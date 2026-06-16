"""CLI entry point for the RISC-V emulator.

Usage:
  riscv-emu run <binary> [--base-addr ADDR] [--max-instructions N] [--trace] [--profile]
  riscv-emu asm <source> [--base-addr ADDR] [-o output]
  riscv-emu debug <binary> [--base-addr ADDR]
  riscv-emu dis <binary> [--base-addr ADDR] [--count N]
"""

from __future__ import annotations
import argparse
import sys

from .cpu import CPU, CPUHalt
from .memory import Memory, MemoryRegion
from .assembler import Assembler
from .loader import load_binary, load_elf, load_file
from .debugger import Debugger
from .profiler import Profiler


def cmd_run(args):
    """Run a binary file."""
    mem, entry = load_file(args.binary, base_addr=getattr(args, 'base_addr', 0x20000000))
    # Add stack
    stack_base = 0x7F000000
    stack_size = 0x01000000  # 16 MB
    mem.add_region(MemoryRegion(stack_base, stack_size, "rw"))
    # Set up stack pointer
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
            old_pc = cpu.pc
            try:
                cpu.step()
            except CPUHalt:
                break
            count += 1
            if args.trace and count <= 1000:
                tracer_entries.append(f"[{count:6d}] {cpu.state_dump()}")
    except Exception as e:
        print(f"Error after {count} instructions: {e}", file=sys.stderr)

    print(f"\nExecution completed: {count} instructions")
    print(f"Final PC: 0x{cpu.pc:08x}")
    # Print key registers
    print(f"a0 (x10) = 0x{cpu.get_reg(10):08x}")
    print(f"a1 (x11) = 0x{cpu.get_reg(11):08x}")

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
    mem, entry = load_file(args.binary, base_addr=getattr(args, 'base_addr', 0x20000000))
    stack_base = 0x7F000000
    stack_size = 0x01000000
    mem.add_region(MemoryRegion(stack_base, stack_size, "rw"))
    cpu = CPU(memory=mem, pc=entry)
    cpu.set_reg(2, stack_base + stack_size - 16)

    dbg = Debugger(cpu, mem)
    dbg.interactive()


def cmd_dis(args):
    """Disassemble a binary file."""
    mem, entry = load_file(args.binary, base_addr=getattr(args, 'base_addr', 0x20000000))
    cpu = CPU(memory=mem, pc=entry)
    dbg = Debugger(cpu, mem)
    count = getattr(args, 'count', 20)
    addr = entry
    for i in range(count):
        print(dbg.disassemble_one(addr))
        addr += 4


def main():
    parser = argparse.ArgumentParser(
        prog="riscv-emu",
        description="RISC-V RV32I Emulator and Assembler"
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

    # asm
    asm_parser = subparsers.add_parser("asm", help="Assemble RISC-V source code")
    asm_parser.add_argument("source", help="Assembly source file")
    asm_parser.add_argument("--base-addr", type=lambda x: int(x, 0), default=0x20000000,
                           help="Base address (default: 0x20000000)")
    asm_parser.add_argument("-o", "--output", help="Output binary file")

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