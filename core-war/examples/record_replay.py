"""
Example: Record a battle and replay it step by step.

This demonstrates the battle recording and replay system.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core_war import load_warrior, BattleRecorder, BattleReplay
from core_war.mars import MARS

WARRIORS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "warriors")


def main():
    # Load warriors
    imp = load_warrior(os.path.join(WARRIORS_DIR, "imp.red"))
    dwarf = load_warrior(os.path.join(WARRIORS_DIR, "dwarf.red"))

    # Record a battle
    print("Recording battle: imp vs dwarf...")
    mars = MARS(core_size=1000, max_cycles=500, seed=42)
    recorder = BattleRecorder(max_snapshots=500)
    recording = recorder.record(mars, [imp, dwarf])

    print(f"\nRecording complete: {len(recording.snapshots)} snapshots")
    print(f"Result: {recording.result}")

    # Save recording
    output_path = "/tmp/core_war_battle.json"
    recording.save(output_path)
    print(f"Saved to: {output_path}")

    # Replay
    print("\n" + "=" * 60)
    print("Replaying battle")
    print("=" * 60)

    replay = BattleReplay(recording)

    # Show first 20 cycles
    for i, snapshot in enumerate(replay.play()):
        if i >= 20:
            print(f"  ... ({replay.total_cycles() - 20} more cycles)")
            break
        alive = ", ".join(snapshot.alive_warriors)
        changes = len(snapshot.changed_cells)
        print(f"  Cycle {snapshot.cycle:>4}: alive=[{alive}] "
              f"changed_cells={changes} "
              f"procs={sum(s['process_count'] for s in snapshot.warrior_states.values())}")

    # Reconstruct core at specific cycle
    print(f"\nCore state at cycle 50:")
    core_at_50 = replay.get_core_at(50)

    # Count non-empty cells
    from core_war.opcodes import Opcode
    non_empty = sum(1 for instr in core_at_50
                    if not (instr.opcode == Opcode.DAT and instr.a_value == 0 and instr.b_value == 0))
    print(f"  Non-empty cells: {non_empty}/{len(core_at_50)}")


if __name__ == "__main__":
    main()