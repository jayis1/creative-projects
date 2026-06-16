"""CHIP-8 assembler — convert mnemonic source code into ROM bytes.

Supports the full standard CHIP-8 instruction set plus SUPER-CHIP extensions.

Syntax:
    - Instructions are case-insensitive: LD V0, 05  or  ld v0, 05
    - Comments start with ; or //
    - Labels end with :   e.g.  loop:
    - Numbers can be hex (0x200, $200) or decimal (512)
    - Strings for sprite data: .db 0xFF, 0x81  or  .dw 0x3000
    - .org 0x300  sets the output address

Example:
    ; Simple hello program
    .org 0x200
    CLS
    LD V0, 0x0A    ; x position
    LD V1, 0x0A    ; y position
    LD I, sprite
    DRW V0, V1, 5
    JP loop
    sprite:
    .db 0x90, 0x90, 0xF0, 0x90, 0x90
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


class AssemblerError(Exception):
    """Raised on assembly errors."""


@dataclass
class AssemblyResult:
    """Result of assembling CHIP-8 source code."""

    rom: bytes
    symbols: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


# Mnemonic → (prefix_nibble, pattern)
# pattern keys: x, y, kk, nnn, n
MNEMONICS = {
    # 0-prefixed
    "CLS": (0x0, "00E0"),
    "RET": (0x0, "00EE"),
    "EXIT": (0x0, "00FD"),
    "EXMODE": (0x0, "00FF"),
    "SCROLL_DOWN": (0x0, "00Cn"),
    "SCROLL_LEFT": (0x0, "00FB"),
    "SCROLL_RIGHT": (0x0, "00FC"),
    "SYS": (0x0, "0nnn"),
    # 1-prefixed
    "JP": (0x1, "1nnn"),
    # 2-prefixed
    "CALL": (0x2, "2nnn"),
    # 3-prefixed
    "SE": (0x3, None),  # disambiguate: 3xkk or 5xy0
    # 4-prefixed
    "SNE": (0x4, None),  # disambiguate: 4xkk or 9xy0
    # 6-prefixed
    "LD": (0x6, None),  # many forms
    # 7-prefixed
    "ADD": (0x7, None),  # 7xkk or 8xy4
    # 8-prefixed
    "OR": (0x8, "8xy1"),
    "AND": (0x8, "8xy2"),
    "XOR": (0x8, "8xy3"),
    "SUB": (0x8, "8xy5"),
    "SUBN": (0x8, "8xy7"),
    "SHR": (0x8, "8xy6"),
    "SHL": (0x8, "8xyE"),
    # A-prefixed
    # B-prefixed
    "RND": (0xC, "Cxkk"),
    # D-prefixed
    "DRW": (0xD, "Dxyn"),
    # E-prefixed
    "SKP": (0xE, "Ex9E"),
    "SKNP": (0xE, "ExA1"),
}


def _parse_number(s: str) -> int:
    """Parse a number string (hex with 0x/$ prefix, or decimal)."""
    s = s.strip()
    if s.startswith("0x") or s.startswith("0X"):
        return int(s, 16)
    if s.startswith("$"):
        return int(s[1:], 16)
    return int(s)


def _parse_register(s: str) -> int:
    """Parse a register reference like 'V0'..'VF' or 'v0'..'vf'."""
    s = s.strip().upper()
    if not s.startswith("V") or len(s) != 2:
        raise AssemblerError(f"Invalid register: {s!r} (expected V0–VF)")
    digit = s[1]
    if digit in "0123456789ABCDEF":
        return int(digit, 16)
    raise AssemblerError(f"Invalid register: {s!r}")


class Assembler:
    """Two-pass CHIP-8 assembler.

    Pass 1: Collect labels and compute addresses.
    Pass 2: Emit opcodes, resolving label references.
    """

    def __init__(self, origin: int = 0x200) -> None:
        self.origin = origin
        self._symbols: Dict[str, int] = {}
        self._errors: List[str] = []
        self._warnings: List[str] = []

    def assemble(self, source: str) -> AssemblyResult:
        """Assemble *source* code and return an AssemblyResult."""
        lines = source.splitlines()
        instructions, data_bytes = self._pass1(lines)
        rom = self._pass2(instructions, data_bytes)
        return AssemblyResult(
            rom=rom,
            symbols=dict(self._symbols),
            errors=list(self._errors),
            warnings=list(self._warnings),
        )

    # ------------------------------------------------------------------
    # Pass 1 — collect labels, compute addresses, parse instructions
    # ------------------------------------------------------------------

    def _pass1(
        self, lines: List[str]
    ) -> Tuple[List[Tuple[int, str, List[str]]], List[Tuple[int, bytes]]]:
        """Parse lines, collect labels, return (instructions, data_directives)."""
        instructions: List[Tuple[int, str, List[str]]] = []
        data_bytes: List[Tuple[int, bytes]] = []
        pc = self.origin

        for lineno, raw_line in enumerate(lines, 1):
            # Strip comments
            line = raw_line.split(";")[0].split("//")[0].strip()
            if not line:
                continue

            # Handle directives
            if line.upper().startswith(".ORG"):
                arg = line[4:].strip()
                pc = _parse_number(arg)
                continue

            if line.upper().startswith(".DB"):
                # .db 0xFF, 0x81, ...
                arg = line[3:].strip()
                values = [_parse_number(v.strip()) for v in arg.split(",")]
                data_bytes.append((pc, bytes(values)))
                pc += len(values)
                continue

            if line.upper().startswith(".DW"):
                # .dw 0x3000, 0x1234, ... (16-bit big-endian words)
                arg = line[3:].strip()
                values = [_parse_number(v.strip()) for v in arg.split(",")]
                raw = bytearray()
                for v in values:
                    raw.append((v >> 8) & 0xFF)
                    raw.append(v & 0xFF)
                data_bytes.append((pc, bytes(raw)))
                pc += len(values) * 2
                continue

            # Handle labels
            if line.endswith(":"):
                label = line[:-1].strip()
                self._symbols[label] = pc
                continue

            # Parse instruction
            parts = line.replace(",", " ").split()
            mnemonic = parts[0].upper()
            operands = parts[1:]
            instructions.append((pc, mnemonic, operands))
            pc += 2

        return instructions, data_bytes

    # ------------------------------------------------------------------
    # Pass 2 — emit opcodes
    # ------------------------------------------------------------------

    def _pass2(
        self,
        instructions: List[Tuple[int, str, List[str]]],
        data_bytes: List[Tuple[int, bytes]],
    ) -> bytes:
        """Resolve references and emit bytes."""
        # Determine total size
        max_addr = self.origin
        for pc, mnemonic, operands in instructions:
            max_addr = max(max_addr, pc + 2)
        for addr, data in data_bytes:
            max_addr = max(max_addr, addr + len(data))

        rom = bytearray(max_addr - self.origin + 2)

        # Emit data bytes
        for addr, data in data_bytes:
            offset = addr - self.origin
            for i, b in enumerate(data):
                rom[offset + i] = b

        # Emit instructions
        for pc, mnemonic, operands in instructions:
            try:
                opcode = self._encode(pc, mnemonic, operands)
                offset = pc - self.origin
                rom[offset] = (opcode >> 8) & 0xFF
                rom[offset + 1] = opcode & 0xFF
            except AssemblerError as e:
                self._errors.append(f"${pc:04X}: {e}")
            except Exception as e:
                self._errors.append(f"${pc:04X}: Unexpected error: {e}")

        # Trim trailing zeros
        while len(rom) > 0 and rom[-1] == 0 and rom[-2] == 0:
            rom = rom[:-2]

        return bytes(rom)

    def _resolve_label_or_number(self, s: str) -> int:
        """Resolve a label or parse a number."""
        s = s.strip()
        if s in self._symbols:
            return self._symbols[s]
        return _parse_number(s)

    def _encode(self, pc: int, mnemonic: str, operands: List[str]) -> int:
        """Encode a single instruction into a 16-bit opcode."""

        # --- Special mnemonics with multiple forms ---
        if mnemonic == "LD":
            return self._encode_ld(operands)
        if mnemonic == "ADD":
            return self._encode_add(operands)
        if mnemonic == "SE":
            return self._encode_se(operands)
        if mnemonic == "SNE":
            return self._encode_sne(operands)
        if mnemonic == "JP":
            return self._encode_jp(operands)
        if mnemonic == "CALL":
            addr = self._resolve_label_or_number(operands[0])
            return 0x2000 | (addr & 0xFFF)
        if mnemonic == "SYS":
            addr = self._resolve_label_or_number(operands[0])
            return 0x0000 | (addr & 0xFFF)

        # --- Simple mnemonics ---
        if mnemonic == "CLS":
            return 0x00E0
        if mnemonic == "RET":
            return 0x00EE
        if mnemonic == "EXIT":
            return 0x00FD
        if mnemonic == "EXMODE":
            return 0x00FF
        if mnemonic == "SCROLL_LEFT":
            return 0x00FB
        if mnemonic == "SCROLL_RIGHT":
            return 0x00FC
        if mnemonic == "SCROLL_DOWN":
            n = _parse_number(operands[0])
            return 0x00C0 | (n & 0xF)
        if mnemonic == "RND":
            x = _parse_register(operands[0])
            kk = _parse_number(operands[1])
            return 0xC000 | (x << 8) | (kk & 0xFF)
        if mnemonic == "DRW":
            x = _parse_register(operands[0])
            y = _parse_register(operands[1])
            n = _parse_number(operands[2])
            return 0xD000 | (x << 8) | (y << 4) | (n & 0xF)
        if mnemonic == "SKP":
            x = _parse_register(operands[0])
            return 0xE000 | (x << 8) | 0x9E
        if mnemonic == "SKNP":
            x = _parse_register(operands[0])
            return 0xE000 | (x << 8) | 0xA1
        if mnemonic in ("OR", "AND", "XOR", "SUB", "SUBN", "SHR", "SHL"):
            suffix_map = {
                "OR": 1, "AND": 2, "XOR": 3,
                "SUB": 5, "SUBN": 7,
                "SHR": 6, "SHL": 0xE,
            }
            x = _parse_register(operands[0])
            y = _parse_register(operands[1])
            return 0x8000 | (x << 8) | (y << 4) | suffix_map[mnemonic]

        raise AssemblerError(f"Unknown mnemonic: {mnemonic}")

    def _encode_ld(self, operands: List[str]) -> int:
        """Encode LD instruction (many forms)."""
        dest = operands[0].strip().upper()
        src = operands[1].strip() if len(operands) > 1 else ""

        # LD Vx, Vy
        if dest.startswith("V") and src.upper().startswith("V"):
            x = _parse_register(dest)
            y = _parse_register(src)
            return 0x8000 | (x << 8) | (y << 4)

        # LD Vx, special sources (DT, K, [I], R) — must check before LD Vx, kk
        if dest.startswith("V") and src:
            src_upper = src.upper()

            if src_upper == "DT":
                x = _parse_register(dest)
                return 0xF000 | (x << 8) | 0x07
            if src_upper == "K":
                x = _parse_register(dest)
                return 0xF000 | (x << 8) | 0x0A
            if src_upper == "[I]":
                x = _parse_register(dest)
                return 0xF000 | (x << 8) | 0x65
            if src_upper == "R":
                x = _parse_register(dest)
                return 0xF000 | (x << 8) | 0x85

        # LD Vx, kk
        if dest.startswith("V") and src:
            x = _parse_register(dest)
            try:
                kk = _parse_number(src)
            except (ValueError, AssemblerError):
                # It might be a label — but LD Vx, label doesn't make sense
                raise AssemblerError(f"Invalid immediate in LD {dest}, {src}")
            return 0x6000 | (x << 8) | (kk & 0xFF)

        # LD I, addr
        if dest == "I":
            addr = self._resolve_label_or_number(src)
            return 0xA000 | (addr & 0xFFF)

        # LD DT, Vx
        if dest == "DT":
            x = _parse_register(src)
            return 0xF000 | (x << 8) | 0x15

        # LD ST, Vx
        if dest == "ST":
            x = _parse_register(src)
            return 0xF000 | (x << 8) | 0x18

        # LD F, Vx
        if dest == "F":
            x = _parse_register(src)
            return 0xF000 | (x << 8) | 0x29

        # LD HF, Vx
        if dest == "HF":
            x = _parse_register(src)
            return 0xF000 | (x << 8) | 0x30

        # LD B, Vx
        if dest == "B":
            x = _parse_register(src)
            return 0xF000 | (x << 8) | 0x33

        # LD [I], Vx
        if dest == "[I]":
            x = _parse_register(src)
            return 0xF000 | (x << 8) | 0x55

        # LD R, Vx (SUPER-CHIP)
        if dest == "R":
            x = _parse_register(src)
            return 0xF000 | (x << 8) | 0x75

        raise AssemblerError(f"Invalid LD form: LD {dest}, {src}")

    def _encode_add(self, operands: List[str]) -> int:
        """Encode ADD instruction."""
        dest = operands[0].strip()
        src = operands[1].strip()

        # ADD I, Vx
        if dest.upper() == "I":
            x = _parse_register(src)
            return 0xF000 | (x << 8) | 0x1E

        # ADD Vx, kk
        if dest.upper().startswith("V"):
            x = _parse_register(dest)
            try:
                kk = _parse_number(src)
                return 0x7000 | (x << 8) | (kk & 0xFF)
            except (ValueError, AssemblerError):
                pass
            # ADD Vx, Vy
            if src.upper().startswith("V"):
                y = _parse_register(src)
                return 0x8000 | (x << 8) | (y << 4) | 4

        raise AssemblerError(f"Invalid ADD form: ADD {dest}, {src}")

    def _encode_se(self, operands: List[str]) -> int:
        """Encode SE instruction."""
        x_reg = operands[0].strip()
        y_val = operands[1].strip()
        x = _parse_register(x_reg)

        if y_val.upper().startswith("V"):
            y = _parse_register(y_val)
            return 0x5000 | (x << 8) | (y << 4)
        else:
            kk = _parse_number(y_val)
            return 0x3000 | (x << 8) | (kk & 0xFF)

    def _encode_sne(self, operands: List[str]) -> int:
        """Encode SNE instruction."""
        x_reg = operands[0].strip()
        y_val = operands[1].strip()
        x = _parse_register(x_reg)

        if y_val.upper().startswith("V"):
            y = _parse_register(y_val)
            return 0x9000 | (x << 8) | (y << 4)
        else:
            kk = _parse_number(y_val)
            return 0x4000 | (x << 8) | (kk & 0xFF)

    def _encode_jp(self, operands: List[str]) -> int:
        """Encode JP instruction (including JP V0, addr)."""
        parts = operands[0].strip()
        if "," in parts:
            # JP V0, addr
            halves = parts.split(",")
            reg = halves[0].strip().upper()
            addr = self._resolve_label_or_number(halves[1].strip())
            if reg == "V0":
                return 0xB000 | (addr & 0xFFF)
            # SUPER-CHIP: JP Vx, addr
            x = _parse_register(reg)
            return 0xB000 | (addr & 0xFFF)
        else:
            addr = self._resolve_label_or_number(parts)
            return 0x1000 | (addr & 0xFFF)


def assemble(source: str, origin: int = 0x200) -> AssemblyResult:
    """Assemble CHIP-8 source code into a ROM bytes object.

    This is the main entry point for the assembler.

    Args:
        source: CHIP-8 assembly source code.
        origin: Starting address (default 0x200).

    Returns:
        AssemblyResult with the assembled ROM and any errors/warnings.
    """
    asm = Assembler(origin=origin)
    return asm.assemble(source)