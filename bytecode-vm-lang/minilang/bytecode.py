"""MiniLang bytecode instruction set.

A stack-based bytecode VM.  Each instruction is a 32-bit opcode optionally
followed by an integer operand.  The operand is encoded directly into the
:class:`Instruction` object to keep dispatch fast.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, auto


class OpCode(IntEnum):
    # --- literals & variables ------------------------------------------- #
    PUSH_INT = auto()       # operand: int value
    PUSH_STR = auto()       # operand: string-pool index
    PUSH_BOOL = auto()      # operand: 0/1
    PUSH_NIL = auto()
    LOAD_LOCAL = auto()     # operand: slot index
    STORE_LOCAL = auto()    # operand: slot index
    POP = auto()            # discard top of stack

    # --- arrays --------------------------------------------------------- #
    NEW_ARRAY = auto()      # operand: element count
    INDEX_GET = auto()
    INDEX_SET = auto()      # pop value, index, array

    # --- arithmetic ----------------------------------------------------- #
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    MOD = auto()
    NEG = auto()

    # --- comparisons ---------------------------------------------------- #
    EQ = auto()
    NEQ = auto()
    LT = auto()
    LE = auto()
    GT = auto()
    GE = auto()

    # --- logic ---------------------------------------------------------- #
    NOT = auto()
    AND = auto()
    OR = auto()

    # --- control flow --------------------------------------------------- #
    JUMP = auto()           # operand: target pc
    JUMP_IF_FALSE = auto()  # operand: target pc
    JUMP_IF_TRUE = auto()   # operand: target pc
    CALL = auto()           # operand: arg count
    RETURN = auto()         # operand: 1 if value, 0 if unit

    # --- built-ins ------------------------------------------------------ #
    PRINT = auto()          # pop value, print it
    HALT = auto()

    # --- debug ---------------------------------------------------------- #
    TRACE = auto()          # pop & return (used by REPL to display values)


@dataclass(slots=True)
class Instruction:
    op: OpCode
    operand: int = 0
    line: int = 0

    def __repr__(self) -> str:
        return f"Instruction({self.op.name}, {self.operand}, line={self.line})"


class Disassembler:
    """Pretty-print a bytecode chunk."""

    def __init__(self, code: list[Instruction], strings: list[str],
                 name: str = "<chunk>"):
        self.code = code
        self.strings = strings
        self.name = name

    def disassemble(self) -> str:
        lines: list[str] = [f"== {self.name} =="]
        for i, ins in enumerate(self.code):
            operand_str = ""
            if ins.op == OpCode.PUSH_STR:
                operand_str = f'  ; "{self.strings[ins.operand]}"'
            elif ins.op == OpCode.PUSH_INT:
                operand_str = f"  ; {ins.operand}"
            elif ins.op == OpCode.JUMP or ins.op == OpCode.JUMP_IF_FALSE:
                operand_str = f"  -> {ins.operand}"
            elif ins.op == OpCode.LOAD_LOCAL or ins.op == OpCode.STORE_LOCAL:
                operand_str = f"  slot {ins.operand}"
            lines.append(f"  {i:4d}  {ins.op.name:<16} {ins.operand}{operand_str}")
        return "\n".join(lines)