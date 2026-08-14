"""
Opcodes, modifiers, and addressing modes for the Redcode instruction set.

Based on the ICWS'94 standard used in Core War.
"""

from enum import IntEnum


class Opcode(IntEnum):
    """Redcode opcodes (ICWS'94)."""

    DAT = 0   # Terminate warrior execution (data)
    MOV = 1   # Copy one instruction to another
    ADD = 2   # Add A-field to B-field
    SUB = 3   # Subtract A-field from B-field
    JMP = 4   # Jump to A-field address
    JMZ = 5   # Jump if B-field is zero
    JMN = 6   # Jump if B-field is non-zero
    DJN = 7   # Decrement B-field, jump if non-zero
    SPL = 8   # Split execution into a new process
    CMP = 9   # Skip next if A-field equals B-field (also SEQ)
    SEQ = 9   # Alias for CMP
    SNE = 10  # Skip next if A-field not equal to B-field
    SLT = 11  # Skip if A-field less than B-field
    SLT_old = 12  # (unused, reserved)
    NOP = 13  # No operation
    MOD = 14  # B-field = B-field mod A-field
    MUL = 15  # B-field = A-field * B-field
    DIV = 16  # B-field = B-field / A-field

    @classmethod
    def from_str(cls, name: str) -> "Opcode":
        """Parse an opcode from its string representation."""
        name = name.strip().upper()
        # Handle full names like "DAT", "MOV", etc.
        for op in cls:
            if op.name == name:
                return op
        # Handle legacy aliases
        aliases = {
            "SEQ": cls.SEQ,
            "SNE": cls.SNE,
        }
        if name in aliases:
            return aliases[name]
        raise ValueError(f"Unknown opcode: {name!r}")


# Mapping of opcode string names to Opcode values (for parser convenience)
OPCODE_NAMES: dict[str, Opcode] = {
    "DAT": Opcode.DAT,
    "MOV": Opcode.MOV,
    "ADD": Opcode.ADD,
    "SUB": Opcode.SUB,
    "JMP": Opcode.JMP,
    "JMZ": Opcode.JMZ,
    "JMN": Opcode.JMN,
    "DJN": Opcode.DJN,
    "SPL": Opcode.SPL,
    "CMP": Opcode.CMP,
    "SEQ": Opcode.SEQ,
    "SNE": Opcode.SNE,
    "SLT": Opcode.SLT,
    "NOP": Opcode.NOP,
    "MOD": Opcode.MOD,
    "MUL": Opcode.MUL,
    "DIV": Opcode.DIV,
}


class Modifier(IntEnum):
    """Instruction modifiers specifying which fields an opcode operates on."""

    A = 0    # Operate on A-field only
    B = 1    # Operate on B-field only
    AB = 2   # Source A-field → destination B-field
    BA = 3   # Source B-field → destination A-field
    F = 4    # Both fields (A→A, B→B)
    X = 5    # Cross fields (A→B, B→A)
    I = 6    # Entire instruction (opcode + both fields)

    @classmethod
    def from_str(cls, name: str) -> "Modifier":
        """Parse a modifier from its string representation."""
        name = name.strip().upper()
        for mod in cls:
            if mod.name == name:
                return mod
        raise ValueError(f"Unknown modifier: {name!r}")


# Default modifiers for each opcode (ICWS'94 standard)
DEFAULT_MODIFIERS: dict[Opcode, Modifier] = {
    Opcode.DAT: Modifier.F,
    Opcode.MOV: Modifier.I,
    Opcode.ADD: Modifier.F,
    Opcode.SUB: Modifier.F,
    Opcode.JMP: Modifier.B,
    Opcode.JMZ: Modifier.B,
    Opcode.JMN: Modifier.B,
    Opcode.DJN: Modifier.B,
    Opcode.SPL: Modifier.B,
    Opcode.CMP: Modifier.I,
    Opcode.SEQ: Modifier.I,
    Opcode.SNE: Modifier.I,
    Opcode.SLT: Modifier.B,
    Opcode.NOP: Modifier.F,
    Opcode.MOD: Modifier.B,
    Opcode.MUL: Modifier.B,
    Opcode.DIV: Modifier.B,
}


class AddressMode(IntEnum):
    """Addressing modes for Redcode operands."""

    IMMEDIATE = 0    # # — Use the operand value directly
    DIRECT = 1       # $ — Relative to current instruction (default)
    INDIRECT_B = 2   # @ — Indirect via B-field pointer
    INDIRECT_A = 3   # * — Indirect via A-field pointer
    PREDEC_B = 4     # { — Predecrement B-field pointer, then indirect
    PREDEC_A = 5     # < — Predecrement A-field pointer, then indirect
    POSTINC_B = 6    # } — Post-increment B-field pointer after indirect
    POSTINC_A = 7    # > — Post-increment A-field pointer after indirect

    @classmethod
    def from_str(cls, symbol: str) -> "AddressMode":
        """Parse an addressing mode from its symbol."""
        symbols = {
            "#": cls.IMMEDIATE,
            "$": cls.DIRECT,
            "@": cls.INDIRECT_B,
            "*": cls.INDIRECT_A,
            "{": cls.PREDEC_B,
            "<": cls.PREDEC_A,
            "}": cls.POSTINC_B,
            ">": cls.POSTINC_A,
        }
        symbol = symbol.strip()
        if symbol == "":
            return cls.DIRECT  # Default mode
        if symbol in symbols:
            return symbols[symbol]
        raise ValueError(f"Unknown addressing mode: {symbol!r}")


# Symbol lookup for serialization
ADDRESS_MODE_SYMBOLS: dict[AddressMode, str] = {
    AddressMode.IMMEDIATE: "#",
    AddressMode.DIRECT: "$",
    AddressMode.INDIRECT_B: "@",
    AddressMode.INDIRECT_A: "*",
    AddressMode.PREDEC_B: "{",
    AddressMode.PREDEC_A: "<",
    AddressMode.POSTINC_B: "}",
    AddressMode.POSTINC_A: ">",
}