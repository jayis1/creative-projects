"""CHIP-8 Emulator — command-line interface and disassembler."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .cpu import CPU, CpuError
from .display import Display
from .keypad import Keypad
from .memory import Memory


def disassemble(data: bytes, start: int = 0x200) -> None:
    """Print a disassembly listing of CHIP-8 ROM *data*."""
    mnemonics = _build_mnemonic_table()
    i = 0
    while i + 1 < len(data):
        opcode = (data[i] << 8) | data[i + 1]
        addr = start + i
        disasm = _disassemble_opcode(opcode, mnemonics)
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
        "Fx33": "LD B, V{x}",
        "Fx55": "LD [I], V{x}",
        "Fx65": "LD V{x}, [I]",
    }


def _disassemble_opcode(opcode: int, table: dict) -> str:
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
        if kk == 0x33:
            return f"LD B, V{x:X}"
        if kk == 0x55:
            return f"LD [I], V{x:X}"
        if kk == 0x65:
            return f"LD V{x:X}, [I]"
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
        description="CHIP-8 emulator and disassembler",
    )
    sub = parser.add_subparsers(dest="command", help="Sub-command")

    # Run
    run_p = sub.add_parser("run", help="Run a CHIP-8 ROM")
    run_p.add_argument("rom", type=Path, help="Path to .ch8 ROM file")
    run_p.add_argument("-c", "--cycles", type=int, default=0,
                       help="Max cycles to run (0=infinite)")
    run_p.add_argument("-s", "--speed", type=int, default=700,
                       help="Instructions per second (default: 700)")
    run_p.add_argument("--dump-display", action="store_true",
                       help="Print the display on halt")

    # Disassemble
    dis_p = sub.add_parser("disasm", help="Disassemble a CHIP-8 ROM")
    dis_p.add_argument("rom", type=Path, help="Path to .ch8 ROM file")

    # Validate
    val_p = sub.add_parser("validate", help="Validate a CHIP-8 ROM")
    val_p.add_argument("rom", type=Path, help="Path to .ch8 ROM file")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "disasm":
        rom_data = args.rom.read_bytes()
        disassemble(rom_data)
        return

    if args.command == "validate":
        rom_data = args.rom.read_bytes()
        print(f"ROM size: {len(rom_data)} bytes")
        if len(rom_data) > 4096 - 0x200:
            print("WARNING: ROM exceeds available memory")
        print(f"Instructions: {len(rom_data) // 2}")
        return

    if args.command == "run":
        cpu = CPU()
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
            print(cpu.display.render())


if __name__ == "__main__":
    main()