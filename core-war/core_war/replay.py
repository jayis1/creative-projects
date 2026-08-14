"""
Battle replay system for Core War.

Records battle executions as serialized snapshots, allowing replay,
playback, and analysis of battles after they complete.

Recordings can be saved to/loaded from JSON files.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from core_war.instruction import Instruction
from core_war.opcodes import Opcode, Modifier, AddressMode, ADDRESS_MODE_SYMBOLS
from core_war.mars import MARS, BattleResult, WarriorState
from core_war.parser import ParsedWarrior

logger = logging.getLogger("core_war.replay")


@dataclass
class CycleSnapshot:
    """
    A snapshot of the MARS state at a single cycle.

    Only stores the addresses that changed (delta) for efficiency.
    """

    cycle: int
    alive_warriors: List[str]
    warrior_states: Dict[str, Dict[str, Any]]  # name → {processes, alive, instructions_executed}
    changed_cells: Dict[int, List[Any]]  # addr → [opcode, modifier, a_mode, a_value, b_mode, b_value]


@dataclass
class BattleRecording:
    """
    A complete recording of a battle, suitable for replay.

    Contains the initial state, all cycle snapshots, and the final result.
    """

    core_size: int
    max_cycles: int
    initial_core: Dict[int, List[int]]  # addr → packed instruction data
    warrior_loads: Dict[str, Dict[str, Any]]  # name → {load_address, start_offset, instructions}
    snapshots: List[CycleSnapshot] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize recording to a dictionary."""
        return {
            "core_size": self.core_size,
            "max_cycles": self.max_cycles,
            "initial_core": {str(k): v for k, v in self.initial_core.items()},
            "warrior_loads": self.warrior_loads,
            "snapshots": [
                {
                    "cycle": s.cycle,
                    "alive_warriors": s.alive_warriors,
                    "warrior_states": s.warrior_states,
                    "changed_cells": {str(k): v for k, v in s.changed_cells.items()},
                }
                for s in self.snapshots
            ],
            "result": self.result,
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 0) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, path: Union[str, Path]) -> None:
        """Save recording to a JSON file."""
        path = Path(path)
        path.write_text(self.to_json())
        logger.info("Saved battle recording to %s (%d snapshots)", path, len(self.snapshots))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BattleRecording":
        """Deserialize from a dictionary."""
        initial_core = {int(k): v for k, v in data.get("initial_core", {}).items()}
        snapshots = [
            CycleSnapshot(
                cycle=s["cycle"],
                alive_warriors=s["alive_warriors"],
                warrior_states=s["warrior_states"],
                changed_cells={int(k): v for k, v in s.get("changed_cells", {}).items()},
            )
            for s in data.get("snapshots", [])
        ]
        return cls(
            core_size=data["core_size"],
            max_cycles=data["max_cycles"],
            initial_core=initial_core,
            warrior_loads=data.get("warrior_loads", {}),
            snapshots=snapshots,
            result=data.get("result"),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "BattleRecording":
        """Load a recording from a JSON file."""
        path = Path(path)
        data = json.loads(path.read_text())
        logger.info("Loaded battle recording from %s (%d snapshots)", path, len(data.get("snapshots", [])))
        return cls.from_dict(data)


def _pack_instruction(instr: Instruction) -> List[int]:
    """Pack an instruction into a list of ints for serialization."""
    return [instr.opcode, instr.modifier, instr.a_mode, instr.a_value, instr.b_mode, instr.b_value]


def _unpack_instruction(data: List[int]) -> Instruction:
    """Unpack a serialized instruction."""
    return Instruction(
        opcode=Opcode(data[0]),
        modifier=Modifier(data[1]),
        a_mode=AddressMode(data[2]),
        a_value=data[3],
        b_mode=AddressMode(data[4]),
        b_value=data[5],
    )


class BattleRecorder:
    """
    Records a battle by taking snapshots of the MARS state at each cycle.

    Usage::

        recorder = BattleRecorder()
        recording = recorder.record(mars, warriors)
        recording.save("battle.json")
    """

    def __init__(self, max_snapshots: int = 10000):
        """
        Args:
            max_snapshots: Maximum number of cycle snapshots to keep.
                Set to 0 for unlimited.
        """
        self.max_snapshots = max_snapshots

    def record(
        self,
        mars: MARS,
        warriors: List[ParsedWarrior],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BattleRecording:
        """
        Record a battle by running it with snapshot capture.

        Args:
            mars: A MARS instance (will be reset and run).
            warriors: List of warriors to load.
            metadata: Optional metadata to include in the recording.

        Returns:
            A BattleRecording containing all snapshots.
        """
        mars.reset()
        for w in warriors:
            mars.load_warrior(w)

        # Record initial core state (only non-empty cells)
        initial_core: Dict[int, List[int]] = {}
        for addr in range(len(mars.core)):
            instr = mars.core[addr]
            if instr.opcode != Opcode.DAT or instr.a_value != 0 or instr.b_value != 0:
                initial_core[addr] = _pack_instruction(instr)

        # Record warrior load info
        warrior_loads: Dict[str, Dict[str, Any]] = {}
        for w_state in mars.warriors:
            warrior_loads[w_state.name] = {
                "load_address": w_state.load_address,
                "start_offset": w_state.start_offset,
                "instructions": [_pack_instruction(i) for i in w_state.instructions],
            }

        snapshots: List[CycleSnapshot] = []
        prev_core: Dict[int, Instruction] = {}

        # Enable on_execute callback to capture state changes
        running = True
        while running:
            # Take snapshot before execution
            changed: Dict[int, List[int]] = {}
            for w in mars.warriors:
                if not w.alive:
                    continue
                if not w.processes:
                    continue
                pc = w.processes[0] if w.processes else None
                if pc is not None:
                    # Record the instruction that will be executed
                    if pc not in prev_core or prev_core[pc] != mars.core[pc]:
                        changed[pc] = _pack_instruction(mars.core[pc])
                        prev_core[pc] = mars.core[pc].copy()

            running = mars.step()

            # Create snapshot
            alive_names = [w.name for w in mars.warriors if w.alive]
            warrior_states = {}
            for w in mars.warriors:
                warrior_states[w.name] = {
                    "alive": w.alive,
                    "process_count": len(w.processes),
                    "instructions_executed": w.instructions_executed,
                    "next_pc": w.processes[0] if w.processes else None,
                }

            # Capture all changed cells (not just the executed one)
            all_changed: Dict[int, List[int]] = {}
            for addr in range(len(mars.core)):
                instr = mars.core[addr]
                packed = _pack_instruction(instr)
                if addr not in initial_core:
                    # Was empty (DAT 0, 0), check if it changed
                    if instr.opcode != Opcode.DAT or instr.a_value != 0 or instr.b_value != 0:
                        all_changed[addr] = packed
                else:
                    # Was non-empty, check if it changed from initial
                    if initial_core[addr] != packed:
                        all_changed[addr] = packed

            snapshot = CycleSnapshot(
                cycle=mars.cycle,
                alive_warriors=alive_names,
                warrior_states=warrior_states,
                changed_cells=all_changed,
            )
            snapshots.append(snapshot)

            if self.max_snapshots > 0 and len(snapshots) >= self.max_snapshots:
                logger.warning("Reached max_snapshots limit (%d), stopping", self.max_snapshots)
                break

        result = mars._make_result()
        result_dict = {
            "winner": result.winner,
            "survivors": result.survivors,
            "cycles": result.cycles,
            "reason": result.reason,
            "warrior_results": result.warrior_results,
        }

        recording = BattleRecording(
            core_size=mars.core_size,
            max_cycles=mars.max_cycles,
            initial_core=initial_core,
            warrior_loads=warrior_loads,
            snapshots=snapshots,
            result=result_dict,
            metadata=metadata or {},
        )
        logger.info("Recorded battle: %d snapshots, result=%s", len(snapshots), result.winner)
        return recording


class BattleReplay:
    """
    Replays a recorded battle, reconstructing core state at each cycle.

    Usage::

        replay = BattleReplay(recording)
        for state in replay.play():
            print(f"Cycle {state.cycle}: {state.alive_warriors}")
    """

    def __init__(self, recording: BattleRecording):
        self.recording = recording
        self._core: List[Instruction] = []
        self._current_snapshot = 0
        self._reset_core()

    def _reset_core(self) -> None:
        """Initialize core to the recording's initial state."""
        self._core = [Instruction(Opcode.DAT, Modifier.F, AddressMode.DIRECT, 0,
                                   AddressMode.DIRECT, 0)
                       for _ in range(self.recording.core_size)]
        for addr, packed in self.recording.initial_core.items():
            self._core[addr] = _unpack_instruction(packed)

    @property
    def core(self) -> List[Instruction]:
        """Current core state."""
        return self._core

    def play(self, start_cycle: int = 0, end_cycle: Optional[int] = None):
        """
        Generator that yields CycleSnapshots, applying changes.

        Args:
            start_cycle: Cycle to start replay from.
            end_cycle: Cycle to stop at (None = play to end).

        Yields:
            CycleSnapshot for each cycle.
        """
        self._reset_core()
        end = end_cycle or len(self.recording.snapshots)

        for i, snapshot in enumerate(self.recording.snapshots):
            if i < start_cycle:
                continue
            if i >= end:
                break

            # Apply changed cells
            for addr, packed in snapshot.changed_cells.items():
                self._core[addr] = _unpack_instruction(packed)

            self._current_snapshot = i
            yield snapshot

    def get_snapshot(self, index: int) -> Optional[CycleSnapshot]:
        """Get a specific snapshot by index."""
        if 0 <= index < len(self.recording.snapshots):
            return self.recording.snapshots[index]
        return None

    def get_core_at(self, cycle: int) -> List[Instruction]:
        """
        Reconstruct the core state at a specific cycle.

        Args:
            cycle: The cycle number to get core state for.

        Returns:
            A copy of the core at that cycle.
        """
        self._reset_core()
        for i in range(min(cycle + 1, len(self.recording.snapshots))):
            snapshot = self.recording.snapshots[i]
            for addr, packed in snapshot.changed_cells.items():
                self._core[addr] = _unpack_instruction(packed)
        return [instr.copy() for instr in self._core]

    def total_cycles(self) -> int:
        """Get the total number of recorded cycles."""
        return len(self.recording.snapshots)

    def summary(self) -> str:
        """Generate a text summary of the recording."""
        r = self.recording
        lines = []
        lines.append(f"Battle Recording Summary")
        lines.append(f"{'=' * 50}")
        lines.append(f"  Core size: {r.core_size}")
        lines.append(f"  Max cycles: {r.max_cycles}")
        lines.append(f"  Recorded cycles: {len(r.snapshots)}")
        lines.append(f"  Warriors: {list(r.warrior_loads.keys())}")
        if r.result:
            lines.append(f"  Winner: {r.result.get('winner', 'None')}")
            lines.append(f"  Reason: {r.result.get('reason', 'Unknown')}")
            lines.append(f"  Cycles: {r.result.get('cycles', 0)}")
        lines.append(f"{'=' * 50}")
        return "\n".join(lines)