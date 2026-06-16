#!/usr/bin/env python3
"""Example: Using the tracer/profiler to analyze ROM execution.

This example shows how to:
- Attach a Tracer to the CPU
- Run a ROM with profiling enabled
- View opcode frequency statistics
- Identify hot addresses
"""

from chip8_emulator import CPU
from chip8_emulator.tracer import Tracer
from chip8_emulator.roms import maze_rom

# Create CPU and tracer
cpu = CPU()
tracer = Tracer(cpu)

# Attach tracer to CPU's on_step callback
tracer.attach()

# Load the maze ROM and run for some cycles
cpu.load_rom(maze_rom())
cpu.run(cycles=500)
tracer.detach()

# Print profiling summary
print(tracer.summary())

# Access raw stats
print(f"\nTotal cycles: {tracer.stats.total_cycles}")
print(f"Draw calls: {tracer.stats.draw_calls}")

# Get top opcodes
print("\nTop 5 opcodes:")
for name, count in tracer.stats.top_opcodes(5):
    print(f"  {name}: {count}")

# Export as JSON
# json_str = tracer.stats.to_json()
# print(f"JSON export: {len(json_str)} bytes")