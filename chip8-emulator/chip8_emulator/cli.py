"""CHIP-8 Emulator — command-line interface, disassembler, debugger, validator, and assembler."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from .assembler import Assembler, AssemblerError, assemble
from .config import EmulatorConfig, generate_default_config, load_config
from .cpu import CPU, CpuError
from .debugger import Debugger
from .display import Display
from .keypad import Keypad
from .memory import Memory
from .recorder import Recorder
from .tracer import Tracer
from .validator import validate_rom

logger = logging.getLogger(__name__)


def disassemble(data: bytes, start: int = 0x200) -> None:
    """Print a disassembly listing of CHIP-8 ROM *data*."""
    i = 0
    while i + 1 < len(data):
        opcode = (data[i] << 8) | data[i + 1]
        addr = start + i
        disasm = _disassemble_opcode(opcode)
        print(f"  {addr:04X}:  {opcode:04X}    {disasm}")
        i += 2


def _build_mnemonic_table() -> dict:
    """Return a mapping from opcode patterns to mnemonic strings."""
    return {
        "00E0": "CLS",
        "00EE": "RET",
        "0NNN": "SYS {addr}",
        "1NNN": "JP {addr}",
        "2NNN": "CALL {addr}",
        "3xkk": "SE V{x}, {kk}",
        "4xkk": "SNE V{x}, {kk}",
        "5xy0": "SE V{x}, V{y}",
        "6xkk": "LD V{x}, {kk}",
        "7xkk": "ADD V{x}, {kk}",
        "8xy0": "LD V{x}, V{y}",
        "8xy1": "OR V{x}, V{y}",
        "8xy2": "AND V{x}, V{y}",
        "8xy3": "XOR V{x}, V{y}",
        "8xy4": "ADD V{x}, V{y}",
        "8xy5": "SUB V{x}, V{y}",
        "8xy6": "SHR V{x}",
        "8xy7": "SUBN V{x}, V{y}",
        "8xyE": "SHL V{x}",
        "9xy0": "SNE V{x}, V{y}",
        "ANNN": "LD I, {addr}",
        "BNNN": "JP V0, {addr}",
        "Cxkk": "RND V{x}, {kk}",
        "Dxyn": "DRW V{x}, V{y}, {n}",
        "Ex9E": "SKP V{x}",
        "ExA1": "SKNP V{x}",
        "Fx07": "LD V{x}, DT",
        "Fx0A": "LD V{x}, K",
        "Fx15": "LD DT, V{x}",
        "Fx18": "LD ST, V{x}",
        "Fx1E": "ADD I, V{x}",
        "Fx29": "LD F, V{x}",
        "Fx30": "LD HF, V{x}",
        "Fx33": "LD B, V{x}",
        "Fx55": "LD [I], V{x}",
        "Fx65": "LD V{x}, [I]",
        "Fx75": "LD R, V{x}",
        "Fx85": "LD V{x}, R",
        "00FD": "EXIT",
        "00FF": "EXMODE",
        "00Cn": "SCROLL DOWN",
        "00FB": "SCROLL LEFT",
        "00FC": "SCROLL RIGHT",
    }


def _disassemble_opcode(opcode: int, table: dict | None = None) -> str:
    """Disassemble a single opcode into a human-readable string."""
    nnn = opcode & 0x0FFF
    kk = opcode & 0xFF
    x = (opcode >> 8) & 0xF
    y = (opcode >> 4) & 0xF
    n = opcode & 0xF
    last = opcode & 0xF

    if opcode == 0x00E0:
        return "CLS"
    if opcode == 0x00EE:
        return "RET"
    if opcode == 0x00FD:
        return "EXIT (SUPER-CHIP)"
    if opcode == 0x00FF:
        return "EXMODE (SUPER-CHIP)"
    if opcode == 0x00FB:
        return "SCROLL LEFT (SUPER-CHIP)"
    if opcode == 0x00FC:
        return "SCROLL RIGHT (SUPER-CHIP)"
    if (opcode & 0xFFF0) == 0x00C0:
        return f"SCROLL DOWN {n} (SUPER-CHIP)"

    prefix = (opcode >> 12) & 0xF

    if prefix == 0x0:
        return f"SYS {nnn:03X}"
    if prefix == 0x1:
        return f"JP {nnn:03X}"
    if prefix == 0x2:
        return f"CALL {nnn:03X}"
    if prefix == 0x3:
        return f"SE V{x:X}, {kk:02X}"
    if prefix == 0x4:
        return f"SNE V{x:X}, {kk:02X}"
    if prefix == 0x5 and last == 0:
        return f"SE V{x:X}, V{y:X}"
    if prefix == 0x6:
        return f"LD V{x:X}, {kk:02X}"
    if prefix == 0x7:
        return f"ADD V{x:X}, {kk:02X}"
    if prefix == 0x8:
        if last == 0:
            return f"LD V{x:X}, V{y:X}"
        if last == 1:
            return f"OR V{x:X}, V{y:X}"
        if last == 2:
            return f"AND V{x:X}, V{y:X}"
        if last == 3:
            return f"XOR V{x:X}, V{y:X}"
        if last == 4:
            return f"ADD V{x:X}, V{y:X}"
        if last == 5:
            return f"SUB V{x:X}, V{y:X}"
        if last == 6:
            return f"SHR V{x:X}"
        if last == 7:
            return f"SUBN V{x:X}, V{y:X}"
        if last == 0xE:
            return f"SHL V{x:X}"
        return f"??? ({opcode:04X})"
    if prefix == 0x9 and last == 0:
        return f"SNE V{x:X}, V{y:X}"
    if prefix == 0xA:
        return f"LD I, {nnn:03X}"
    if prefix == 0xB:
        return f"JP V0, {nnn:03X}"
    if prefix == 0xC:
        return f"RND V{x:X}, {kk:02X}"
    if prefix == 0xD:
        return f"DRW V{x:X}, V{y:X}, {n}"
    if prefix == 0xE:
        if kk == 0x9E:
            return f"SKP V{x:X}"
        if kk == 0xA1:
            return f"SKNP V{x:X}"
        return f"??? ({opcode:04X})"
    if prefix == 0xF:
        if kk == 0x07:
            return f"LD V{x:X}, DT"
        if kk == 0x0A:
            return f"LD V{x:X}, K"
        if kk == 0x15:
            return f"LD DT, V{x:X}"
        if kk == 0x18:
            return f"LD ST, V{x:X}"
        if kk == 0x1E:
            return f"ADD I, V{x:X}"
        if kk == 0x29:
            return f"LD F, V{x:X}"
        if kk == 0x30:
            return f"LD HF, V{x:X} (SUPER-CHIP)"
        if kk == 0x33:
            return f"LD B, V{x:X}"
        if kk == 0x55:
            return f"LD [I], V{x:X}"
        if kk == 0x65:
            return f"LD V{x:X}, [I]"
        if kk == 0x75:
            return f"LD R, V{x:X} (SUPER-CHIP)"
        if kk == 0x85:
            return f"LD V{x:X}, R (SUPER-CHIP)"
        return f"??? ({opcode:04X})"

    return f"??? ({opcode:04X})"


def build_test_rom(instructions: list[int]) -> bytes:
    """Build a ROM image from a list of 16-bit instruction words (big-endian)."""
    rom = bytearray()
    for instr in instructions:
        rom.append((instr >> 8) & 0xFF)
        rom.append(instr & 0xFF)
    return bytes(rom)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="chip8-emulator",
        description="CHIP-8 emulator, disassembler, debugger, validator, and assembler",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="Path to config file (YAML/JSON/TOML)",
    )

    sub = parser.add_subparsers(dest="command", help="Sub-command")

    # Run
    run_p = sub.add_parser("run", help="Run a CHIP-8 ROM")
    run_p.add_argument("rom", type=Path, help="Path to .ch8 ROM file")
    run_p.add_argument("-c", "--cycles", type=int, default=0,
                       help="Max cycles to run (0=infinite)")
    run_p.add_argument("-s", "--speed", type=int, default=700,
                       help="Instructions per second (default: 700)")
    run_p.add_argument("--super-chip", action="store_true",
                       help="Enable SUPER-CHIP extensions")
    run_p.add_argument("--dump-display", action="store_true",
                       help="Print the display on halt")
    run_p.add_argument("--dump-registers", action="store_true",
                       help="Print register state on halt")

    # Disassemble
    dis_p = sub.add_parser("disasm", help="Disassemble a CHIP-8 ROM")
    dis_p.add_argument("rom", type=Path, help="Path to .ch8 ROM file")
    dis_p.add_argument("--offset", type=int, default=0x200,
                       help="Starting address (default: 0x200)")

    # Validate
    val_p = sub.add_parser("validate", help="Validate a CHIP-8 ROM")
    val_p.add_argument("rom", type=Path, help="Path to .ch8 ROM file")

    # Debug
    dbg_p = sub.add_parser("debug", help="Debug a CHIP-8 ROM step-by-step")
    dbg_p.add_argument("rom", type=Path, help="Path to .ch8 ROM file")
    dbg_p.add_argument("--super-chip", action="store_true",
                       help="Enable SUPER-CHIP extensions")
    dbg_p.add_argument("-n", "--steps", type=int, default=10,
                       help="Number of steps to run (default: 10)")
    dbg_p.add_argument("-b", "--breakpoint", type=lambda x: int(x, 0),
                       action="append", default=[],
                       help="Add breakpoint at address (e.g. 0x210)")

    # Profile
    prof_p = sub.add_parser("profile", help="Profile a CHIP-8 ROM execution")
    prof_p.add_argument("rom", type=Path, help="Path to .ch8 ROM file")
    prof_p.add_argument("-c", "--cycles", type=int, default=1000,
                        help="Number of cycles to profile (default: 1000)")
    prof_p.add_argument("--super-chip", action="store_true",
                        help="Enable SUPER-CHIP extensions")
    prof_p.add_argument("--json", action="store_true",
                        help="Output profiling data as JSON")

    # Record
    rec_p = sub.add_parser("record", help="Record a CHIP-8 execution trace")
    rec_p.add_argument("rom", type=Path, help="Path to .ch8 ROM file")
    rec_p.add_argument("-o", "--output", type=str, required=True,
                       help="Output JSON trace file")
    rec_p.add_argument("-c", "--cycles", type=int, default=5000,
                       help="Number of cycles to record (default: 5000)")
    rec_p.add_argument("--super-chip", action="store_true",
                       help="Enable SUPER-CHIP extensions")

    # Assemble
    asm_p = sub.add_parser("asm", help="Assemble CHIP-8 source code into a ROM")
    asm_p.add_argument("source", type=Path, help="Path to .ch8asm source file")
    asm_p.add_argument("-o", "--output", type=str, default=None,
                       help="Output ROM file (default: <source>.ch8)")
    asm_p.add_argument("--origin", type=lambda x: int(x, 0), default=0x200,
                       help="Origin address (default: 0x200)")

    # Config
    cfg_p = sub.add_parser("config", help="Generate or show config")
    cfg_p.add_argument("--generate", type=str, choices=["yaml", "json", "toml"],
                       default=None,
                       help="Generate a default config file")
    cfg_p.add_argument("--show", type=str, default=None,
                       help="Show current config from file")

    args = parser.parse_args(argv)

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format="%(name)s: %(message)s")

    # Load config
    config = EmulatorConfig()
    if args.config:
        try:
            config = load_config(args.config)
            config.apply_logging()
        except (FileNotFoundError, ValueError, ImportError) as e:
            print(f"Warning: Could not load config: {e}", file=sys.stderr)

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "config":
        if args.generate:
            print(generate_default_config(args.generate))
        elif args.show:
            try:
                cfg = load_config(args.show)
                print(json.dumps(cfg.to_dict(), indent=2))  # type: ignore
            except Exception as e:
                print(f"Error loading config: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print("Use --generate or --show with the config command")
            sys.exit(1)
        return

    if args.command == "disasm":
        rom_data = args.rom.read_bytes()
        disassemble(rom_data, start=args.offset)
        return

    if args.command == "validate":
        result = validate_rom(str(args.rom))
        print(result)
        sys.exit(0 if result.ok else 1)

    if args.command == "asm":
        source = args.source.read_text()
        result = assemble(source, origin=args.origin)
        if result.errors:
            for err in result.errors:
                print(f"Error: {err}", file=sys.stderr)
            sys.exit(1)
        if result.warnings:
            for warn in result.warnings:
                print(f"Warning: {warn}", file=sys.stderr)
        output_path = args.output or str(args.source.with_suffix(".ch8"))
        Path(output_path).write_bytes(result.rom)
        print(f"Assembled {len(result.rom)} bytes → {output_path}")
        if result.symbols:
            print("Symbols:")
            for name, addr in sorted(result.symbols.items()):
                print(f"  {name}: 0x{addr:04X}")
        return

    if args.command == "profile":
        cpu = CPU(super_chip=args.super_chip)
        cpu.load_rom_from_file(str(args.rom))
        tracer = Tracer(cpu)
        tracer.attach()
        cpu.run(cycles=args.cycles)
        tracer.detach()
        if args.json:
            print(tracer.stats.to_json())
        else:
            print(tracer.summary())
        return

    if args.command == "record":
        cpu = CPU(super_chip=args.super_chip)
        cpu.load_rom_from_file(str(args.rom))
        recorder = Recorder(cpu)
        recorder._rom_data = bytes(cpu.memory._mem[0x200:0x200 + len(args.rom.read_bytes())])
        recorder.attach()
        recorder.start()
        cpu.run(cycles=args.cycles)
        recorder.stop()
        recorder.detach()
        recorder.save(args.output)
        print(f"Recorded {recorder.step_count} steps → {args.output}")
        return

    if args.command == "debug":
        cpu = CPU(super_chip=args.super_chip)
        cpu.load_rom_from_file(str(args.rom))
        debugger = Debugger(cpu)

        for bp in args.breakpoint:
            debugger.add_breakpoint(bp)

        print(f"Debugging {args.rom} ({args.steps} steps)")
        print(f"Initial state:\n{debugger.dump_registers()}")
        print()

        for i in range(args.steps):
            opcode = debugger.step()
            desc = _disassemble_opcode(opcode)
            print(f"Step {i + 1}: {desc}")
            print(debugger.dump_registers())
            if debugger.should_break():
                print(f"*** Breakpoint hit at {cpu.pc:04X}")
                break
            print()

        print("\nDisplay:")
        print(debugger.dump_display())
        return

    if args.command == "run":
        cpu = CPU(super_chip=getattr(args, 'super_chip', False))
        cpu.load_rom_from_file(str(args.rom))
        cycles = args.cycles if args.cycles > 0 else 0
        interval = 1.0 / args.speed if args.speed > 0 else 0

        print(f"Running {args.rom} ({args.speed} Hz)...")
        try:
            if cycles > 0:
                cpu.run(cycles=cycles)
            else:
                count = 0
                while True:
                    cpu.step()
                    count += 1
                    if interval > 0 and count % args.speed == 0:
                        time.sleep(interval * args.speed)
        except CpuError as e:
            print(f"CPU error: {e}")
        except KeyboardInterrupt:
            print("\nHalted by user")

        if args.dump_display:
            print("\nDisplay:")
            print(cpu.display.render())

        if args.dump_registers:
            dbg = Debugger(cpu)
            print("\nRegisters:")
            print(dbg.dump_registers())

        print(f"\nTotal cycles: {cpu.cycles}")


if __name__ == "__main__":
    main()