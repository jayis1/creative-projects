"""
Disassembler for Redcode instructions in core memory.

Converts Instruction objects back into human-readable Redcode source,
useful for debugging and core memory inspection.
"""

from typing import List, Optional

from core_war.instruction import Instruction
from core_war.opcodes import ADDRESS_MODE_SYMBOLS


def disassemble(instr: Instruction) -> str:
    """Disassemble a single instruction to Redcode text."""
    a_sym = ADDRESS_MODE_SYMBOLS.get(instr.a_mode, "$")
    b_sym = ADDRESS_MODE_SYMBOLS.get(instr.b_mode, "$")
    return (
        f"{instr.opcode.name}.{instr.modifier.name} "
        f"{a_sym}{instr.a_value}, {b_sym}{instr.b_value}"
    )


def disassemble_core(
    core: List[Instruction],
    start: int = 0,
    count: Optional[int] = None,
    highlight_addrs: Optional[set] = None,
) -> str:
    """
    Disassemble a range of core memory to a text listing.

    Args:
        core: The core memory array.
        start: Starting address.
        count: Number of instructions to disassemble (None = all from start).
        highlight_addrs: Set of addresses to highlight with '>>'.

    Returns:
        A multi-line string with address + disassembly.
    """
    if count is None:
        count = len(core) - start

    lines = []
    highlight_addrs = highlight_addrs or set()

    for i in range(start, min(start + count, len(core))):
        marker = ">>" if i in highlight_addrs else "  "
        instr = core[i]
        lines.append(f"{marker} {i:5d}: {disassemble(instr)}")

    return "\n".join(lines)


def disassemble_around(
    core: List[Instruction],
    center: int,
    radius: int = 5,
) -> str:
    """Disassemble core memory around a given address, showing context."""
    start = max(0, center - radius)
    end = min(len(core), center + radius + 1)
    lines = []
    for i in range(start, end):
        marker = ">>" if i == center else "  "
        lines.append(f"{marker} {i:5d}: {disassemble(core[i])}")
    return "\n".join(lines)