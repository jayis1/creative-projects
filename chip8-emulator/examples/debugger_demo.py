#!/usr/bin/env python3
"""Example: Using the debugger for step-by-step execution.

This example shows how to:
- Create a Debugger instance
- Set breakpoints
- Step through execution
- Inspect CPU state
"""

from chip8_emulator import CPU, Debugger
from chip8_emulator.roms import draw_test_rom

# Create CPU and debugger
cpu = CPU()
cpu.load_rom(draw_test_rom())
debugger = Debugger(cpu)

# Set a breakpoint at the draw instruction
debugger.add_breakpoint(0x204)  # DRW instruction address

print("=== Step-by-step execution ===")
print(f"Initial state:\n{debugger.dump_registers()}\n")

# Step through a few instructions
for i in range(6):
    opcode = debugger.step()
    print(f"Step {i+1}: opcode={opcode:04X}")

print(f"\nFinal registers:\n{debugger.dump_registers()}")
print(f"\nDisplay:\n{debugger.dump_display()}")

# List breakpoints
print(f"\nBreakpoints: {[f'0x{bp:04X}' for bp in debugger.list_breakpoints()]}")