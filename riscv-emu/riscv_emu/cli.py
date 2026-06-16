"""CLI entry point for the RISC-V emulator.

Usage:
  riscv-emu run <binary> [options]       — Run a RISC-V binary
  riscv-emu asm <source> [options]       — Assemble RISC-V source
  riscv-emu debug <binary> [options]     — Interactive debugger
  riscv-emu dis <binary> [options]        — Disassemble a binary
  riscv-emu test [options]                — Run self-tests
  riscv-emu config [options]              — Manage configuration
  riscv-emu info                          — Show emulator info
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from typing import Optional

from .cpu import CPU, CPUHalt, Trap
from .memory import Memory, MemoryRegion, MemoryError
from .assembler import Assembler, AssembleError
from .disassembler import disassemble, disassemble_to_string
from .loader import load_binary, load_elf, load_file
from .debugger import Debugger
from .profiler import Profiler
from .tracer import Tracer
from .config import EmulatorConfig, CPUConfig, UARTConfig, MemoryRegionConfig, TraceConfig
from .state import StateSerializer
from .devices import UARTDevice, CLINTDevice, DeviceBus
from .logging_utils import setup_logging, get_logger

logger = get_logger("cli")


def _build_mem_from_config(config: EmulatorConfig) -> Memory:
    """Build memory regions from configuration."""
    regions = []
    for rc in config.memory_regions:
        regions.append(MemoryRegion(rc.base, rc.size, rc.permissions))

    if config.uart.enabled:
        regions.append(MemoryRegion(config.uart.base_addr, config.uart.size, "rw"))

    return Memory(regions)


def cmd_run(args):
    """Run a binary file."""
    config = _load_config(args)

    setup_logging(config.log_level, log_file=getattr(args, 'log_file', None))

    base_addr = getattr(args, 'base_addr', None) or config.cpu.pc
    mem, entry = load_file(args.binary, base_addr=base_addr)

    # Add stack if not already present
    stack_base = 0x7F000000
    stack_size = 0x01000000
    try:
        mem._resolve(stack_base + stack_size - 4, "w")
    except MemoryError:
        mem.add_region(MemoryRegion(stack_base, stack_size, "rw"))

    # Add UART region if not present
    if config.uart.enabled:
        try:
            mem._resolve(config.uart.base_addr, "w")
        except MemoryError:
            mem.add_region(MemoryRegion(config.uart.base_addr, config.uart.size, "rw"))

    # Set up CPU
    cpu = CPU(
        memory=mem,
        pc=entry,
        hart_id=config.cpu.hart_id,
        enable_m_ext=config.cpu.enable_m_ext,
    )
    cpu.set_reg(2, stack_base + stack_size - 16)  # sp

    # Set up device bus
    device_bus = DeviceBus()
    uart_dev = None
    if config.uart.enabled:
        uart_dev = UARTDevice(config.uart.base_addr, config.uart.size)
        device_bus.add_device(uart_dev)

    max_insn = getattr(args, 'max_instructions', None) or config.cpu.max_instructions

    # Set up profiler
    profiler = None
    if args.profile:
        profiler = Profiler()
        profiler.start()

    # Set up tracer
    tracer = None
    if args.trace:
        tracer = Tracer(max_entries=10000)
        tracer.start()

    # Set up CLINT timer if requested
    clint = None
    if getattr(args, 'timer', False):
        clint = CLINTDevice()
        device_bus.add_device(clint)

    count = 0
    start_time = time.time()
    try:
        while count < max_insn:
            try:
                cpu.step()
                count += 1

                # Tick devices
                if device_bus.devices:
                    device_bus.tick_all(cpu)

            except Trap as t:
                try:
                    cpu._handle_trap(t)
                except CPUHalt:
                    break
            except CPUHalt:
                break
    except KeyboardInterrupt:
        print(f"\nInterrupted after {count} instructions", file=sys.stderr)
    except Exception as e:
        logger.error(f"Error after {count} instructions: {e}")
        print(f"Error after {count} instructions: {e}", file=sys.stderr)

    elapsed = time.time() - start_time

    # Print results
    print(f"\n{'='*50}")
    print(f"Execution completed: {count} instructions")
    print(f"Time: {elapsed:.4f}s")
    if elapsed > 0:
        print(f"Performance: {count/elapsed:.0f} instructions/sec")
    print(f"Final PC: 0x{cpu.pc:08x}")
    print(f"  a0 (x10) = 0x{cpu.get_reg(10):08x}")
    print(f"  a1 (x11) = 0x{cpu.get_reg(11):08x}")

    if args.uart and uart_dev:
        print(f"\n=== UART Output ===\n{uart_dev.output}")
    elif args.uart and cpu.uart_output:
        print(f"\n=== UART Output ===\n{cpu.uart_output}")

    if args.trace and tracer:
        print(f"\n=== Trace ({len(tracer.entries)} entries) ===")
        for entry in tracer.entries[-50:]:
            print(f"  {entry}")
        if config.trace.output_file:
            tracer.to_csv(config.trace.output_file)
            print(f"Trace exported to {config.trace.output_file}")

    if profiler:
        profiler.stop()
        print(profiler.summary(mem))

    # Save state if requested
    if getattr(args, 'save_state', None):
        StateSerializer.save_state(cpu, args.save_state)
        print(f"State saved to {args.save_state}")

    # Export trace to JSON if requested
    if getattr(args, 'trace_json', None) and tracer:
        entries = []
        for e in tracer.entries:
            entries.append({
                "pc": e.pc,
                "insn": e.insn,
                "insn_name": e.insn_name,
                "changed_regs": e.changed_regs(),
                "regs_after": {f"x{i}": e.regs_after[i] for i in e.changed_regs()},
            })
        with open(args.trace_json, "w") as f:
            json.dump(entries, f, indent=2)
        print(f"Trace exported to {args.trace_json}")


def cmd_asm(args):
    """Assemble a source file."""
    with open(args.source, "r") as f:
        source = f.read()

    base_addr = getattr(args, 'base_addr', None) or 0x20000000
    asm = Assembler(base_addr=base_addr)
    try:
        code, labels = asm.assemble(source, base_addr=base_addr)
    except AssembleError as e:
        print(f"Assembly error: {e}", file=sys.stderr)
        sys.exit(1)

    output = getattr(args, 'output', None)
    if output:
        with open(output, "wb") as f:
            f.write(code)
        print(f"Assembled {len(code)} bytes to {output}")
    else:
        print(f"Assembled {len(code)} bytes")
        if args.disassemble:
            print(disassemble_to_string(code, base_addr))
        else:
            # Print hex dump
            for i in range(0, len(code), 16):
                chunk = code[i:i+16]
                hex_str = " ".join(f"{b:02x}" for b in chunk)
                print(f"  0x{base_addr + i:08x}: {hex_str}")

    if labels:
        print(f"\nSymbols ({len(labels)}):")
        for name, addr in sorted(labels.items(), key=lambda x: x[1]):
            print(f"  {name}: 0x{addr:08x}")


def cmd_debug(args):
    """Run a binary under the debugger."""
    config = _load_config(args)
    base_addr = getattr(args, 'base_addr', None) or config.cpu.pc
    mem, entry = load_file(args.binary, base_addr=base_addr)

    stack_base = 0x7F000000
    stack_size = 0x01000000
    mem.add_region(MemoryRegion(stack_base, stack_size, "rw"))
    mem.add_region(MemoryRegion(0x10000000, 8, "rw"))

    cpu = CPU(memory=mem, pc=entry)
    cpu.set_reg(2, stack_base + stack_size - 16)

    dbg = Debugger(cpu, mem)
    dbg.interactive()


def cmd_dis(args):
    """Disassemble a binary file."""
    base_addr = getattr(args, 'base_addr', None) or 0x20000000
    mem, entry = load_file(args.binary, base_addr=base_addr)
    count = getattr(args, 'count', 20)

    # Try to disassemble the entire loaded region
    if getattr(args, 'all', False):
        # Find the memory region containing the entry point
        region = mem._find_region(entry)
        if region:
            count = (region.base + region.size - entry) // 4
        else:
            count = 100

    addr = entry
    results = []
    for _ in range(count):
        try:
            insn_word = mem.read_word(addr)
        except MemoryError:
            break
        asm_str = disassemble(insn_word, addr)
        results.append(f"  0x{addr:08x}:  0x{insn_word:08x}  {asm_str}")
        addr += 4

    print(f"\nDisassembly of {args.binary} ({len(results)} instructions):")
    print("\n".join(results))


def cmd_test(args):
    """Run self-tests."""
    import subprocess
    test_path = args.test_dir if hasattr(args, 'test_dir') and args.test_dir else None

    print("Running RISC-V emulator self-tests...")
    print("=" * 50)

    cmd = [sys.executable, "-m", "pytest", "-v"]
    if test_path:
        cmd.append(test_path)
    else:
        # Find tests directory relative to package
        import os
        pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        test_dir = os.path.join(pkg_dir, "tests")
        if os.path.isdir(test_dir):
            cmd.append(test_dir)
        else:
            cmd.append("tests/")

    result = subprocess.run(cmd, capture_output=False)
    if result.returncode == 0:
        print("\n✓ All tests passed!")
    else:
        print(f"\n✗ Tests failed with return code {result.returncode}")
    return result.returncode


def cmd_config(args):
    """Manage configuration."""
    if args.config_action == "show":
        config = _load_config(args)
        print(config.to_json())

    elif args.config_action == "init":
        config = EmulatorConfig.default()
        output = args.output or "riscv-emu-config.json"
        config.save(output)
        print(f"Default configuration written to {output}")

    elif args.config_action == "validate":
        if not args.config_file:
            print("Error: --config-file required for validate", file=sys.stderr)
            sys.exit(1)
        try:
            config = EmulatorConfig.from_file(args.config_file)
            print("Configuration is valid:")
            print(f"  CPU PC: 0x{config.cpu.pc:08x}")
            print(f"  Memory regions: {len(config.memory_regions)}")
            print(f"  UART: {'enabled' if config.uart.enabled else 'disabled'}")
            print(f"  Log level: {config.log_level}")
        except Exception as e:
            print(f"Configuration error: {e}", file=sys.stderr)
            sys.exit(1)

    else:
        print("Unknown config action. Use: show, init, validate")


def cmd_info(args):
    """Show emulator version and capabilities."""
    from . import __version__
    print(f"RISC-V RV32I Emulator v{__version__}")
    print()
    print("Supported extensions:")
    print("  RV32I  — Base Integer Instruction Set (40 instructions)")
    print("  RV32M  — Multiply/Divide Extension (8 instructions)")
    print("  Zicsr  — Control and Status Registers (6 instructions)")
    print()
    print("Features:")
    print("  Two-pass assembler with pseudo-instructions")
    print("  ELF32 and raw binary loader")
    print("  Interactive GDB-like debugger")
    print("  Execution profiler and tracer")
    print("  UART MMIO output")
    print("  CLINT timer interrupts")
    print("  State serialization (save/load)")
    print("  Configurable memory map")
    print()
    print("Python: " + sys.version.split()[0])
    print("Platform: " + sys.platform)


def _load_config(args) -> EmulatorConfig:
    """Load configuration from args."""
    config_file = getattr(args, 'config_file', None)
    if config_file:
        try:
            return EmulatorConfig.from_file(config_file)
        except Exception as e:
            print(f"Warning: Failed to load config from {config_file}: {e}", file=sys.stderr)
    return EmulatorConfig.default()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="riscv-emu",
        description="RISC-V RV32I + RV32M Emulator with Assembler, Debugger, and Profiler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  riscv-emu run program.bin                    Run a binary
  riscv-emu run program.bin --trace --profile   Run with tracing and profiling
  riscv-emu run program.bin --uart              Show UART output
  riscv-emu run program.bin --save-state out.json   Save state at exit
  riscv-emu asm program.asm -o program.bin     Assemble source
  riscv-emu asm program.asm --disassemble      Assemble and show disassembly
  riscv-emu debug program.bin                  Interactive debugger
  riscv-emu dis program.bin --count 50         Disassemble binary
  riscv-emu test                               Run self-tests
  riscv-emu config init                         Create default config file
  riscv-emu info                                Show version info
        """,
    )

    # Global options
    parser.add_argument("--config-file", "-C", help="Path to config file (JSON/TOML)")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       default="WARNING", help="Set log level")
    parser.add_argument("--log-file", help="Log to file")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- run ---
    run_parser = subparsers.add_parser("run", help="Run a RISC-V binary")
    run_parser.add_argument("binary", help="Binary or ELF file to run")
    run_parser.add_argument("--base-addr", type=lambda x: int(x, 0), default=None,
                           help="Base load address for raw binaries (default: from config)")
    run_parser.add_argument("--max-instructions", type=int, default=None,
                           help="Maximum instructions to execute")
    run_parser.add_argument("--trace", action="store_true", help="Enable instruction tracing")
    run_parser.add_argument("--profile", action="store_true", help="Enable profiling")
    run_parser.add_argument("--uart", action="store_true", help="Print UART MMIO output")
    run_parser.add_argument("--timer", action="store_true", help="Enable CLINT timer interrupts")
    run_parser.add_argument("--save-state", help="Save CPU state to JSON file at exit")
    run_parser.add_argument("--trace-json", help="Export trace to JSON file")

    # --- asm ---
    asm_parser = subparsers.add_parser("asm", help="Assemble RISC-V source code")
    asm_parser.add_argument("source", help="Assembly source file")
    asm_parser.add_argument("--base-addr", type=lambda x: int(x, 0), default=0x20000000,
                           help="Base address (default: 0x20000000)")
    asm_parser.add_argument("-o", "--output", help="Output binary file")
    asm_parser.add_argument("--disassemble", action="store_true",
                           help="Show disassembly of assembled output")

    # --- debug ---
    debug_parser = subparsers.add_parser("debug", help="Debug a RISC-V binary")
    debug_parser.add_argument("binary", help="Binary or ELF file to debug")
    debug_parser.add_argument("--base-addr", type=lambda x: int(x, 0), default=None,
                             help="Base load address for raw binaries")

    # --- dis ---
    dis_parser = subparsers.add_parser("dis", help="Disassemble a RISC-V binary")
    dis_parser.add_argument("binary", help="Binary or ELF file to disassemble")
    dis_parser.add_argument("--base-addr", type=lambda x: int(x, 0), default=None,
                           help="Base load address for raw binaries")
    dis_parser.add_argument("--count", type=int, default=20, help="Number of instructions")
    dis_parser.add_argument("--all", action="store_true", help="Disassemble entire region")

    # --- test ---
    test_parser = subparsers.add_parser("test", help="Run self-tests")
    test_parser.add_argument("--test-dir", help="Path to test directory")

    # --- config ---
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_parser.add_argument("config_action", choices=["show", "init", "validate"],
                               help="Config action")
    config_parser.add_argument("--output", "-o", help="Output file for 'init'")
    config_parser.add_argument("--config-file", "-C", help="Config file (for validate)")

    # --- info ---
    subparsers.add_parser("info", help="Show emulator info and version")

    args = parser.parse_args()

    # Set up logging
    setup_logging(args.log_level, log_file=args.log_file)

    if args.command == "run":
        cmd_run(args)
    elif args.command == "asm":
        cmd_asm(args)
    elif args.command == "debug":
        cmd_debug(args)
    elif args.command == "dis":
        cmd_dis(args)
    elif args.command == "test":
        sys.exit(cmd_test(args))
    elif args.command == "config":
        cmd_config(args)
    elif args.command == "info":
        cmd_info(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()