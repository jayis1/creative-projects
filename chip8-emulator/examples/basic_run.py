#!/usr/bin/env python3
"""Example: Basic ROM loading and execution.

This example shows how to:
- Create a CPU instance
- Load a ROM from bytes
- Run a fixed number of cycles
- Read register state
- Display the screen output
"""

from chip8_emulator import CPU

# Build a simple ROM: LD V0, 5 / ADD V0, 3 / ADD V0, V0 / JP (halt)
# This computes V0 = 5 + 3 + 8 = 16 (wait, let's trace it properly)
# LD V0, 5   → V0 = 5
# LD V1, 3   → V1 = 3
# ADD V0, V1 → V0 = 5 + 3 = 8, VF = 0
# LD V3, 0   → V3 = 0
# ADD V3, V0 → V3 = 8
# JP 0x210   → halt loop

rom = bytes([
    0x60, 0x05,  # LD V0, 5
    0x61, 0x03,  # LD V1, 3
    0x80, 0x14,  # ADD V0, V1
    0x63, 0x00,  # LD V3, 0
    0x83, 0x04,  # ADD V3, V0
    0x12, 0x0A,  # JP 0x20A (halt)
    0x12, 0x0A,  # halt loop
])

cpu = CPU()
cpu.load_rom(rom)

# Run for enough cycles to complete
cpu.run(cycles=20)

# Read results
print(f"V0 = {cpu.V[0]:02X} (expected: 08)")
print(f"V1 = {cpu.V[1]:02X} (expected: 03)")
print(f"V3 = {cpu.V[3]:02X} (expected: 08)")
print(f"VF = {cpu.V[0xF]:02X} (carry flag, expected: 00)")
print(f"Cycles executed: {cpu.cycles}")
print(f"PC: {cpu.pc:04X}")