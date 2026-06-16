#!/usr/bin/env python3
"""Example: Recording and replaying execution traces.

This example shows how to:
- Record an execution trace
- Save it to a JSON file
- Load and compare traces for regression testing
"""

import tempfile
from pathlib import Path

from chip8_emulator import CPU
from chip8_emulator.recorder import Recorder
from chip8_emulator.roms import add_test_rom

# Create CPU and recorder
cpu = CPU()
recorder = Recorder(cpu)
recorder._rom_data = add_test_rom()
recorder.attach()
recorder.start()

# Load and run the add test ROM
cpu.load_rom(recorder._rom_data)
cpu.run(cycles=20)
recorder.stop()
recorder.detach()

print(f"Recorded {recorder.step_count} steps")

# Save trace to file
with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
    trace_path = f.name
recorder.save(trace_path)
print(f"Saved trace to {trace_path}")

# Load trace back
loaded = Recorder.load(trace_path)
print(f"Loaded {loaded.step_count} steps from trace file")

# Show first few steps
for step in loaded.steps[:5]:
    print(f"  Cycle {step.cycle}: PC={step.pc:04X} Opcode={step.opcode:04X} V0={step.registers[0]:02X}")

# Verify register state
print(f"\nFinal V0: {loaded.steps[-1].registers[0]:02X}")
print(f"Final V1: {loaded.steps[-1].registers[1]:02X}")

# Clean up
Path(trace_path).unlink(missing_ok=True)