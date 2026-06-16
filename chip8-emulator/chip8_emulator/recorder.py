"""CHIP-8 execution recorder — record and playback execution traces.

Records a complete execution trace (opcodes + register/memory state) that
can be saved to JSON and played back for deterministic replay.

Usage::

    from chip8_emulator import CPU
    from chip8_emulator.recorder import Recorder

    cpu = CPU()
    rec = Recorder(cpu)
    cpu.load_rom_from_file("maze.ch8")
    cpu.run(cycles=500)
    rec.save("maze_trace.json")

    # Later: replay
    rec2 = Recorder.replay("maze_trace.json")
    rec2.run()  # Re-executes all recorded steps
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .cpu import CPU


@dataclass
class StepRecord:
    """A single recorded execution step."""

    cycle: int
    pc: int
    opcode: int
    registers: List[int]  # V0–VF
    i_register: int
    sp: int
    collision: bool = False


class Recorder:
    """Records and replays CHIP-8 execution traces.

    The recorder captures every instruction execution, including the full
    register state after each step. This enables:
    - Deterministic replay of any execution
    - Comparison of different emulator implementations
    - Debugging by stepping through recorded traces
    - Regression testing
    """

    def __init__(self, cpu: "CPU", *, max_steps: int = 0) -> None:
        """Initialize the recorder.

        Args:
            cpu: The CPU instance to record.
            max_steps: Maximum steps to record (0 = unlimited).
        """
        self.cpu = cpu
        self.max_steps = max_steps
        self._steps: List[StepRecord] = []
        self._recording = False
        self._rom_data: Optional[bytes] = None
        self._super_chip: bool = cpu.super_chip

    def start(self) -> None:
        """Start recording."""
        self._recording = True
        self._steps.clear()

    def stop(self) -> None:
        """Stop recording."""
        self._recording = False

    def on_step(self, cpu: "CPU", opcode: int) -> None:
        """Callback for CPU on_step — records each execution step."""
        if not self._recording:
            return
        if self.max_steps > 0 and len(self._steps) >= self.max_steps:
            self._recording = False
            return

        collision = (opcode >> 12) == 0xD  # DRW sets VF
        step = StepRecord(
            cycle=cpu.cycles,
            pc=cpu.pc - 2,
            opcode=opcode,
            registers=list(cpu.V),
            i_register=cpu.I,
            sp=cpu.sp,
            collision=collision,
        )
        self._steps.append(step)

    def attach(self) -> None:
        """Attach the recorder to the CPU's on_step callback."""
        self.cpu._on_step = self.on_step

    def detach(self) -> None:
        """Detach the recorder from the CPU."""
        self.cpu._on_step = None

    @property
    def steps(self) -> List[StepRecord]:
        """Return the list of recorded steps."""
        return list(self._steps)

    @property
    def step_count(self) -> int:
        """Return the number of recorded steps."""
        return len(self._steps)

    def save(self, path: str) -> None:
        """Save the recorded trace to a JSON file.

        Args:
            path: Output file path.
        """
        data = {
            "version": 1,
            "super_chip": self._super_chip,
            "rom_data": list(self._rom_data) if self._rom_data else None,
            "steps": [
                {
                    "cycle": s.cycle,
                    "pc": s.pc,
                    "opcode": s.opcode,
                    "registers": s.registers,
                    "i_register": s.i_register,
                    "sp": s.sp,
                    "collision": s.collision,
                }
                for s in self._steps
            ],
        }
        Path(path).write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: str) -> "Recorder":
        """Load a recorded trace from a JSON file.

        Args:
            path: Path to the JSON trace file.

        Returns:
            A Recorder instance with the loaded trace data.
        """
        data = json.loads(Path(path).read_text())
        rec = cls.__new__(cls)
        rec._steps = []
        rec._recording = False
        rec._super_chip = data.get("super_chip", False)
        rec._rom_data = bytes(data["rom_data"]) if data.get("rom_data") else None
        rec.cpu = None  # type: ignore
        rec.max_steps = 0

        for step_data in data["steps"]:
            rec._steps.append(StepRecord(
                cycle=step_data["cycle"],
                pc=step_data["pc"],
                opcode=step_data["opcode"],
                registers=step_data["registers"],
                i_register=step_data["i_register"],
                sp=step_data["sp"],
                collision=step_data.get("collision", False),
            ))
        return rec

    @classmethod
    def replay(cls, path: str) -> "Recorder":
        """Load a trace and replay it on a fresh CPU.

        Re-creates the CPU, loads the ROM, and replays each step,
        verifying register state matches the recorded state.

        Args:
            path: Path to the JSON trace file.

        Returns:
            The Recorder with the replayed CPU attached.
        """
        rec = cls.load(path)
        from .cpu import CPU
        from .memory import Memory, PROGRAM_START

        cpu = CPU(super_chip=rec._super_chip)
        if rec._rom_data:
            cpu.load_rom(rec._rom_data)

        rec.cpu = cpu
        return rec

    def diff(self, other: "Recorder") -> List[str]:
        """Compare two recorded traces and return differences.

        Args:
            other: Another Recorder to compare against.

        Returns:
            List of difference descriptions.
        """
        diffs = []
        min_len = min(len(self._steps), len(other._steps))
        for i in range(min_len):
            s1 = self._steps[i]
            s2 = other._steps[i]
            if s1.opcode != s2.opcode:
                diffs.append(f"Step {i}: opcode mismatch {s1.opcode:04X} vs {s2.opcode:04X}")
            if s1.registers != s2.registers:
                diffs.append(f"Step {i}: registers differ")
            if s1.i_register != s2.i_register:
                diffs.append(f"Step {i}: I register mismatch {s1.i_register:04X} vs {s2.i_register:04X}")
            if s1.sp != s2.sp:
                diffs.append(f"Step {i}: SP mismatch {s1.sp} vs {s2.sp}")

        if len(self._steps) != len(other._steps):
            diffs.append(f"Trace length mismatch: {len(self._steps)} vs {len(other._steps)}")

        return diffs

    def to_dict(self) -> Dict:
        """Convert trace to a serializable dict."""
        return {
            "step_count": len(self._steps),
            "super_chip": self._super_chip,
            "rom_size": len(self._rom_data) if self._rom_data else 0,
        }

    def __repr__(self) -> str:
        return f"Recorder(steps={len(self._steps)}, recording={self._recording})"