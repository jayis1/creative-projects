"""CHIP-8 opcode dispatch table — maps opcode patterns to handler methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Dict

if TYPE_CHECKING:
    from .cpu import CPU


class OpcodeTable:
    """Maps opcode patterns to handler functions on the CPU.

    The CHIP-8 has 35 standard opcodes.  Many are uniquely identified by
    their top nibble, but the 8-prefixed, E-prefixed, and F-prefixed
    groups require deeper inspection of specific bits.
    """

    def __init__(self, cpu: "CPU") -> None:
        self._table: Dict[int, Callable[[], None]] = {}
        self._build(cpu)

    # ------------------------------------------------------------------
    # Table construction
    # ------------------------------------------------------------------

    def _build(self, cpu: "CPU") -> None:
        """Populate the dispatch table with all standard CHIP-8 opcodes."""
        # Top-nibble-only opcodes
        self._table[0x1] = cpu.op_1xxx     # 1NNN — JP addr
        self._table[0x2] = cpu.op_2xxx     # 2NNN — CALL addr
        self._table[0x3] = cpu.op_3xxx     # 3xkk — SE Vx, byte
        self._table[0x4] = cpu.op_4xxx     # 4xkk — SNE Vx, byte
        self._table[0x5] = cpu.op_5xxx     # 5xy0 — SE Vx, Vy
        self._table[0x6] = cpu.op_6xxx     # 6xkk — LD Vx, byte
        self._table[0x7] = cpu.op_7xxx     # 7xkk — ADD Vx, byte
        self._table[0x9] = cpu.op_9xxx     # 9xy0 — SNE Vx, Vy
        self._table[0xA] = cpu.op_Axxx     # ANNN — LD I, addr
        self._table[0xB] = cpu.op_Bxxx     # BNNN — JP V0, addr
        self._table[0xC] = cpu.op_Cxxx     # Cxkk — RND Vx, byte
        self._table[0xD] = cpu.op_Dxxx     # Dxyn — DRW Vx, Vy, nibble

        # 8-prefixed sub-opcodes (determined by last nibble)
        self._table[0x8000] = cpu.op_8xy0   # LD Vx, Vy
        self._table[0x8001] = cpu.op_8xy1   # OR Vx, Vy
        self._table[0x8002] = cpu.op_8xy2   # AND Vx, Vy
        self._table[0x8003] = cpu.op_8xy3   # XOR Vx, Vy
        self._table[0x8004] = cpu.op_8xy4   # ADD Vx, Vy
        self._table[0x8005] = cpu.op_8xy5   # SUB Vx, Vy
        self._table[0x8006] = cpu.op_8xy6   # SHR Vx {, Vy}
        self._table[0x8007] = cpu.op_8xy7   # SUBN Vx, Vy
        self._table[0x800E] = cpu.op_8xyE   # SHL Vx {, Vy}

        # E-prefixed sub-opcodes
        self._table[0xE09E] = cpu.op_Ex9E  # SKP Vx
        self._table[0xE0A1] = cpu.op_ExA1  # SKNP Vx

        # F-prefixed sub-opcodes
        self._table[0xF007] = cpu.op_Fx07   # LD Vx, DT
        self._table[0xF00A] = cpu.op_Fx0A   # LD Vx, K
        self._table[0xF015] = cpu.op_Fx15   # LD DT, Vx
        self._table[0xF018] = cpu.op_Fx18   # LD ST, Vx
        self._table[0xF01E] = cpu.op_Fx1E   # ADD I, Vx
        self._table[0xF029] = cpu.op_Fx29   # LD F, Vx
        self._table[0xF030] = cpu.op_Fx30   # LD HF, Vx (SUPER-CHIP)
        self._table[0xF033] = cpu.op_Fx33   # LD B, Vx
        self._table[0xF055] = cpu.op_Fx55   # LD [I], Vx
        self._table[0xF065] = cpu.op_Fx65   # LD Vx, [I]
        self._table[0xF075] = cpu.op_Fx75   # LD R, Vx (SUPER-CHIP)
        self._table[0xF085] = cpu.op_Fx85   # LD Vx, R (SUPER-CHIP)

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"OpcodeTable(entries={len(self._table)})"

    def __len__(self) -> int:
        return len(self._table)