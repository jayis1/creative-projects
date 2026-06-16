"""CLI entry point for the RISC-V emulator.

Usage:
  riscv-emu run <binary> [--base-addr ADDR] [--max-instructions N] [--trace] [--profile] [--uart]
  riscv-emu asm <source> [--base-addr ADDR] [-o output]
  riscv-emu debug <binary> [--base-addr ADDR]
  riscv-emu dis <binary> [--base-addr ADDR] [--count N]
"""

from __future__ import annotations
import argparse
import sys

from .cpu import CPU, CPUHalt, Trap
from .memory import Memory, MemoryRegion
from .assembler import Assembler
from .disassembler import disassemble, disassemble_to_string
from .loader import load_binary, load_elf, load_file
from .debugger import Debugger
from .profiler import Profiler


def cmd_run(args):
    """Run a binary file."""
    base_addr = getattr(args, 'base_addr', 0x20000000)
    mem, entry = load_file(args.binary, base_addr=base_addr)
    # Add stack region
    stack_base = 0x7F000000
    stack_size = 0x01000000  # 16 MB
    mem.add_region(MemoryRegion(stack_base, stack_size, "rw"))
    # Add UART MMIO region (readable)
    mem.add_region(MemoryRegion(0x10000000, 8, "rw"))
    # Set up CPU
    cpu = CPU(memory=mem, pc=entry)
    cpu.set_reg(2, stack_base + stack_size - 16)  # sp

    profiler = None
    if args.profile:
        profiler = Profiler()
        profiler.start()

    tracer_entries = []
    if args.trace:
        print(f"Tracing enabled. Entry point: 0x{entry:08x}")

    max_insn = getattr(args, 'max_instructions', 100000)
    count = 0
    try:
        while count < max_insn:
            try:
                cpu.step()
                count += 1
            except Trap as t:
                try:
                    cpu._handle_trap(t)
                except CPUHalt:
                    break
            except CPUHalt:
                break
            if args.trace and count <= 1000:
                from .disassembler import disassemble
                insn_word = mem.read_word(cpu.pc)
                tracer_entries.append(
                    f"[{count:6d}] PC=0x{cpu.pc:08x}  {disassemble(insn_word, cpu.pc)}"
                )
    except Exception as e:
        print(f"Error after {count} instructions: {e}", file=sys.stderr)

    print(f"\nExecution completed: {count} instructions")
    print(f"Final PC: 0x{cpu.pc:08x}")
    # Print key registers
    print(f"a0 (x10) = 0x{cpu.get_reg(10):08x}")
    print(f"a1 (x11) = 0x{cpu.get_reg(11):08x}")

    if args.uart and cpu.uart_output:
        print(f"\n=== UART Output ===\n{cpu.uart_output}")

    if args.trace and tracer_entries:
        print("\n=== Trace (first 1000 entries) ===")
        for line in tracer_entries:
            print(line)

    if profiler:
        profiler.stop()
        print(profiler.summary(mem))


def cmd_asm(args):
    """Assemble a source file."""
    with open(args.source, "r") as f:
        source = f.read()

    base_addr = getattr(args, 'base_addr', 0x20000000)
    asm = Assembler(base_addr=base_addr)
    try:
        code, labels = asm.assemble(source, base_addr=base_addr)
    except Exception as e:
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
        print(f"\nLabels:")
        for name, addr in sorted(labels.items(), key=lambda x: x[1]):
            print(f"  {name}: 0x{addr:08x}")


def cmd_debug(args):
    """Run a binary under the debugger."""
    base_addr = getattr(args, 'base_addr', 0x20000000)
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
    base_addr = getattr(args, 'base_addr', 0x20000000)
    mem, entry = load_file(args.binary, base_addr=base_addr)
    count = getattr(args, 'count', 20)
    addr = entry
    for _ in range(count):
        try:
            insn_word = mem.read_word(addr)
        except Exception:
            break
        asm_str = disassemble(insn_word, addr)
        print(f"  0x{addr:08x}:  0x{insn_word:08x}  {asm_str}")
        addr += 4


def main():
    parser = argparse.ArgumentParser(
        prog="riscv-emu",
        description="RISC-V RV32I + RV32M Emulator and Assembler"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # run
    run_parser = subparsers.add_parser("run", help="Run a RISC-V binary")
    run_parser.add_argument("binary", help="Binary or ELF file to run")
    run_parser.add_argument("--base-addr", type=lambda x: int(x, 0), default=0x20000000,
                           help="Base load address for raw binaries (default: 0x20000000)")
    run_parser.add_argument("--max-instructions", type=int, default=100000,
                           help="Maximum instructions to execute")
    run_parser.add_argument("--trace", action="store_true", help="Enable instruction tracing")
    run_parser.add_argument("--profile", action="store_true", help="Enable profiling")
    run_parser.add_argument("--uart", action="store_true", help="Print UART MMIO output")

    # asm
    asm_parser = subparsers.add_parser("asm", help="Assemble RISC-V source code")
    asm_parser.add_argument("source", help="Assembly source file")
    asm_parser.add_argument("--base-addr", type=lambda x: int(x, 0), default=0x20000000,
                           help="Base address (default: 0x20000000)")
    asm_parser.add_argument("-o", "--output", help="Output binary file")
    asm_parser.add_argument("--disassemble", action="store_true",
                           help="Show disassembly of assembled output")

    # debug
    debug_parser = subparsers.add_parser("debug", help="Debug a RISC-V binary")
    debug_parser.add_argument("binary", help="Binary or ELF file to debug")
    debug_parser.add_argument("--base-addr", type=lambda x: int(x, 0), default=0x20000000,
                             help="Base load address for raw binaries")

    # dis
    dis_parser = subparsers.add_parser("dis", help="Disassemble a RISC-V binary")
    dis_parser.add_argument("binary", help="Binary or ELF file to disassemble")
    dis_parser.add_argument("--base-addr", type=lambda x: int(x, 0), default=0x20000000,
                           help="Base load address for raw binaries")
    dis_parser.add_argument("--count", type=int, default=20, help="Number of instructions to disassemble")

    args = parser.parse_args()
    if args.command == "run":
        cmd_run(args)
    elif args.command == "asm":
        cmd_asm(args)
    elif args.command == "debug":
        cmd_debug(args)
    elif args.command == "dis":
        cmd_dis(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()