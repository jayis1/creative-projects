#!/usr/bin/env python3
"""Example: Validating and disassembling ROM files.

This example shows how to:
- Validate a ROM file
- Disassemble ROM bytes to mnemonics
- Use the ROM validator programmatically
"""

from chip8_emulator import CPU, validate_rom_bytes
from chip8_emulator.roms import maze_rom, ibm_logo_rom, counter_rom

# Validate built-in ROMs
for name, rom_func in [("maze", maze_rom), ("ibm_logo", ibm_logo_rom), ("counter", counter_rom)]:
    result = validate_rom_bytes(rom_func(), name=name)
    print(f"=== {name} ===")
    print(result)
    print()

# Disassemble using the CPU's built-in ROM
from chip8_emulator.cli import disassemble

rom_data = maze_rom()
print("=== Maze ROM Disassembly (first 20 instructions) ===")
disassemble(rom_data[:40])  # First 20 instructions