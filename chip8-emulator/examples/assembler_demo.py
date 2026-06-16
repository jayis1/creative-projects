#!/usr/bin/env python3
"""Example: Using the assembler to write CHIP-8 programs in mnemonics.

This example shows how to:
- Write CHIP-8 programs using assembly mnemonics
- Assemble them into ROM bytes
- Run the assembled ROM
"""

from chip8_emulator import CPU
from chip8_emulator.assembler import assemble

# Write a CHIP-8 program in assembly
source = """
; Simple counter: count V0 from 0 to 9
; and display each digit using font sprites

    CLS             ; Clear screen
    LD V0, 0       ; counter = 0
    LD V1, 0       ; x = 0
    LD V2, 0       ; y = 0

loop:
    LD F, V0       ; load font sprite for V0
    DRW V1, V2, 5  ; draw sprite at (V1, V2)
    ADD V0, 1      ; counter++
    SE V0, 10      ; if V0 == 10, we wrapped around
    JP loop        ; keep counting
halt:
    JP halt         ; infinite loop (halt)
"""

# Assemble the source code
result = assemble(source, origin=0x200)

if result.errors:
    print("Assembly errors:")
    for err in result.errors:
        print(f"  {err}")
else:
    print(f"Assembled {len(result.rom)} bytes")
    print(f"Symbols: {result.symbols}")

    # Load and run the assembled ROM
    cpu = CPU()
    cpu.load_rom(result.rom)
    cpu.run(cycles=50)

    print(f"\nV0 = {cpu.V[0]:02X}")
    print(f"Cycles: {cpu.cycles}")
    print("\nDisplay:")
    print(cpu.display.render(on="█", off="·"))