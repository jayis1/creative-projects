"""
A single Redcode instruction in core memory.
"""

from dataclasses import dataclass
from core_war.opcodes import Opcode, Modifier, AddressMode, ADDRESS_MODE_SYMBOLS


@dataclass
class Instruction:
    """A single Redcode instruction stored in core memory."""

    opcode: Opcode = Opcode.DAT
    modifier: Modifier = Modifier.F
    a_mode: AddressMode = AddressMode.DIRECT
    a_value: int = 0
    b_mode: AddressMode = AddressMode.DIRECT
    b_value: int = 0

    def copy(self) -> "Instruction":
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