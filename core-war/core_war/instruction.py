"""
A single Redcode instruction in core memory.

Represents one cell of the MARS circular memory array, containing
an opcode, modifier, two operands (each with an addressing mode and value).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core_war.opcodes import Opcode, Modifier, AddressMode, ADDRESS_MODE_SYMBOLS


@dataclass
class Instruction:
    """
    A single Redcode instruction stored in core memory.

    Attributes:
        opcode: The operation to perform (DAT, MOV, ADD, etc.).
        modifier: Which fields the opcode operates on (.A, .B, .AB, etc.).
        a_mode: Addressing mode for the A operand.
        a_value: Numeric value of the A operand.
        b_mode: Addressing mode for the B operand.
        b_value: Numeric value of the B operand.
    """

    opcode: Opcode = Opcode.DAT
    modifier: Modifier = Modifier.F
    a_mode: AddressMode = AddressMode.DIRECT
    a_value: int = 0
    b_mode: AddressMode = AddressMode.DIRECT
    b_value: int = 0

    def copy(self) -> Instruction:
        """Return a deep copy of this instruction."""
        return Instruction(
            opcode=self.opcode,
            modifier=self.modifier,
            a_mode=self.a_mode,
            a_value=self.a_value,
            b_mode=self.b_mode,
            b_value=self.b_value,
        )

    def __str__(self) -> str:
        """Render this instruction in standard Redcode notation."""
        a_sym = ADDRESS_MODE_SYMBOLS.get(self.a_mode, "$")
        b_sym = ADDRESS_MODE_SYMBOLS.get(self.b_mode, "$")
        return (
            f"{self.opcode.name}.{self.modifier.name} "
            f"{a_sym}{self.a_value}, {b_sym}{self.b_value}"
        )

    def __repr__(self) -> str:
        return (
            f"Instruction({self.opcode.name}, {self.modifier.name}, "
            f"{self.a_mode.name}, {self.a_value}, {self.b_mode.name}, {self.b_value})"
        )

    def is_dat_zero(self) -> bool:
        """Check if this instruction is a default empty cell (DAT 0, 0)."""
        return (
            self.opcode == Opcode.DAT
            and self.a_value == 0
            and self.b_value == 0
        )

    def pack(self) -> tuple[int, int, int, int, int, int]:
        """Pack instruction into a tuple of ints for hashing/comparison."""
        return (
            int(self.opcode), int(self.modifier),
            int(self.a_mode), self.a_value,
            int(self.b_mode), self.b_value,
        )