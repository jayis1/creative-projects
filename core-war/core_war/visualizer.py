"""
Core memory visualization tools for the MARS.

Provides hex-dump style views of core memory, execution heatmaps,
and ASCII art visualizations of the battlefield.
"""

from typing import List, Optional, Dict

from core_war.instruction import Instruction
from core_war.opcodes import Opcode


# Short opcode symbols for compact display (2 chars each)
OPCODE_SHORT: Dict[Opcode, str] = {
    Opcode.DAT: "DA",
    Opcode.MOV: "MV",
    Opcode.ADD: "AD",
    Opcode.SUB: "SU",
    Opcode.JMP: "JM",
    Opcode.JMZ: "JZ",
    Opcode.JMN: "JN",
    Opcode.DJN: "DJ",
    Opcode.SPL: "SP",
    Opcode.CMP: "CP",
    Opcode.SEQ: "SQ",
    Opcode.SNE: "SN",
    Opcode.SLT: "SL",
    Opcode.NOP: "NO",
    Opcode.MOD: "MO",
    Opcode.MUL: "MU",
    Opcode.DIV: "DV",
}


def core_heatmap(
    core: List[Instruction],
    access_counts: Optional[Dict[int, int]] = None,
    width: int = 80,
    max_count: int = 1,
) -> str:
    """
    Generate a heatmap of core memory showing instruction opcodes.

    Args:
        core: The core memory array.
        access_counts: Optional dict mapping address → execution count.
        width: Number of cells per row.
        max_count: Maximum access count for heat scaling.

    Returns:
        ASCII art heatmap string.
    """
    if access_counts is None:
        access_counts = {}

    if max_count == 0:
        max_count = 1

    lines = []
    for row_start in range(0, len(core), width):
        row = []
        for i in range(width):
            addr = row_start + i
            if addr >= len(core):
                row.append("  ")
                continue

            instr = core[addr]
            short = OPCODE_SHORT.get(instr.opcode, "??")

            # Heat coloring via intensity
            count = access_counts.get(addr, 0)
            if count == 0:
                row.append(short)
            else:
                intensity = min(count / max_count, 1.0)
                if intensity > 0.75:
                    row.append(short)  # Hot — will be colored in terminal
                elif intensity > 0.5:
                    row.append(short)
                elif intensity > 0.25:
                    row.append(short.lower())
                else:
                    row.append(short.lower())
        lines.append(" ".join(row))
    return "\n".join(lines)


def core_summary(core: List[Instruction]) -> Dict[str, int]:
    """
    Summarize core memory contents by opcode frequency.

    Returns a dict mapping opcode name → count.
    """
    counts: Dict[str, int] = {}
    for instr in core:
        name = instr.opcode.name
        counts[name] = counts.get(name, 0) + 1
    return counts


def format_core_summary(summary: Dict[str, int], total: int) -> str:
    """Format a core summary dict as a readable text table."""
    lines = []
    lines.append(f"Core memory summary ({total} cells):")
    lines.append(f"{'Opcode':<10} {'Count':>8} {'%':>8}")
    lines.append("-" * 28)
    for name, count in sorted(summary.items(), key=lambda x: -x[1]):
        pct = 100.0 * count / total if total > 0 else 0
        lines.append(f"{name:<10} {count:>8} {pct:>7.1f}%")
    lines.append("-" * 28)
    lines.append(f"{'Total':<10} {total:>8}")
    return "\n".join(lines)


def battle_log(
    core: List[Instruction],
    warriors: List,  # List[WarriorState]
    alive_only: bool = False,
) -> str:
    """
    Generate a text summary of warrior states in a battle.

    Args:
        core: Core memory (unused but kept for API consistency).
        warriors: List of WarriorState objects.
        alive_only: If True, only show alive warriors.
    """
    lines = []
    lines.append(f"{'Warrior':<20} {'Status':<8} {'Procs':>6} {'Exec':>8} {'Load':>6}")
    lines.append("-" * 52)
    for w in warriors:
        if alive_only and not w.alive:
            continue
        status = "ALIVE" if w.alive else "DEAD"
        lines.append(f"{w.name:<20} {status:<8} {len(w.processes):>6} "
                     f"{w.instructions_executed:>8} {w.load_address:>6}")
    return "\n".join(lines)