"""
A parser for Redcode source files.

Supports ICWS'94 style Redcode with:
  - Labels and EQU constants
  - ORG / END pseudo-ops
  - All standard opcodes, modifiers, and addressing modes
  - Comments (semicolon ;) and whitespace-insensitive formatting
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from core_war.instruction import Instruction
from core_war.opcodes import (
    Opcode,
    Modifier,
    AddressMode,
    OPCODE_NAMES,
    DEFAULT_MODIFIERS,
)


class ParseError(Exception):
    """Raised when Redcode source cannot be parsed."""


@dataclass
class ParsedWarrior:
    """Result of parsing a Redcode source file."""

    name: str
    instructions: List[Instruction]
    start_offset: int  # Entry point relative to instruction 0
    source_lines: List[str] = field(default_factory=list)


# --- Regex patterns for tokenizing ---

# Matches an opcode with optional modifier, e.g. "MOV.I", "DAT", "JMP.B"
_OPCODE_RE = re.compile(
    r"^([A-Z]{3})(?:\.([A-Z]{1,2}))?$",
    re.IGNORECASE,
)

# Matches an operand: optional mode symbol + optional expression
# Mode symbols: # $ @ * { < } >
_OPERAND_RE = re.compile(
    r"^([#$@*{}<>])?\s*(.+)$",
)

# Matches a label: starts with letter, alphanumeric + underscore
_LABEL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class RedcodeParser:
    """
    Parses Redcode source text into a list of Instruction objects.

    Usage:
        parser = RedcodeParser()
        warrior = parser.parse(source_text, name="MyWarrior")
    """

    def __init__(self, max_instructions: int = 200):
        self.max_instructions = max_instructions

    def parse(self, source: str, name: str = "Unnamed") -> ParsedWarrior:
        """Parse Redcode source text into a ParsedWarrior."""
        # --- Phase 1: Preprocessing ---
        # Strip comments and blank lines, collect raw lines
        raw_lines = self._strip_comments(source)
        preprocessed = self._preprocess(raw_lines)

        # --- Phase 2: Resolve EQU constants and labels ---
        # First pass: identify labels and EQU definitions
        labels: Dict[str, int] = {}
        equ_constants: Dict[str, str] = {}
        instructions_raw: List[dict] = []  # List of {opcode, modifier, a_str, b_str, labels}

        self._first_pass(preprocessed, labels, equ_constants, instructions_raw)

        # --- Phase 3: Resolve ORG and END ---
        start_offset = self._resolve_org(preprocessed, labels, equ_constants)

        # --- Phase 4: Convert raw instructions to Instruction objects ---
        instructions: List[Instruction] = []
        for idx, raw in enumerate(instructions_raw):
            instr = self._build_instruction(raw, idx, labels, equ_constants)
            instructions.append(instr)

        if len(instructions) == 0:
            raise ParseError("Warrior has no instructions")

        if len(instructions) > self.max_instructions:
            raise ParseError(
                f"Warrior has {len(instructions)} instructions, "
                f"exceeds max {self.max_instructions}"
            )

        return ParsedWarrior(
            name=name,
            instructions=instructions,
            start_offset=start_offset,
            source_lines=raw_lines,
        )

    def _strip_comments(self, source: str) -> List[str]:
        """Remove comments (everything after ;) and return non-empty lines."""
        lines = []
        for line in source.splitlines():
            # Remove comments
            comment_pos = line.find(";")
            if comment_pos >= 0:
                line = line[:comment_pos]
            line = line.strip()
            if line:
                lines.append(line)
        return lines

    def _preprocess(self, lines: List[str]) -> List[str]:
        """Handle line continuations and normalize whitespace."""
        result = []
        for line in lines:
            # Normalize multiple spaces to single (but preserve operand separators)
            line = re.sub(r"\s+", " ", line)
            result.append(line)
        return result

    def _first_pass(
        self,
        lines: List[str],
        labels: Dict[str, int],
        equ_constants: Dict[str, str],
        instructions_raw: List[dict],
    ) -> None:
        """
        First pass: identify labels, EQU constants, and collect raw instruction data.
        """
        for line in lines:
            tokens = line.split()

            if not tokens:
                continue

            # Check for EQU constant definition: "NAME EQU value"
            # The EQU can appear after a label: "NAME equ value"
            equ_idx = self._find_keyword(tokens, "EQU")
            if equ_idx is not None and equ_idx > 0:
                # Everything before EQU is the constant name (may have a label prefix)
                const_name = tokens[equ_idx - 1]
                const_value = " ".join(tokens[equ_idx + 1:])
                equ_constants[const_name.upper()] = const_value
                continue

            # Check for ORG pseudo-op
            if tokens[0].upper() == "ORG":
                continue  # Handled in _resolve_org

            # Check for END pseudo-op
            if tokens[0].upper() == "END":
                continue  # Handled in _resolve_org

            # Parse labels (may have multiple labels on one line)
            label_tokens = []
            idx = 0
            while idx < len(tokens) and _LABEL_RE.match(tokens[idx]):
                # Check if this token is actually the opcode
                opcode_name = tokens[idx].split(".")[0].upper()
                if opcode_name in OPCODE_NAMES:
                    break
                label_tokens.append(tokens[idx])
                idx += 1

            if idx >= len(tokens):
                raise ParseError(f"Line has labels but no opcode: {line}")

            # Register labels at the current instruction index
            instr_idx = len(instructions_raw)
            for label in label_tokens:
                labels[label.upper()] = instr_idx

            # Now parse the opcode + operands
            opcode_token = tokens[idx]
            idx += 1

            # Parse opcode and modifier
            match = _OPCODE_RE.match(opcode_token)
            if not match:
                raise ParseError(f"Invalid opcode token: {opcode_token!r}")

            opcode_name = match.group(1).upper()
            modifier_str = match.group(2)

            if opcode_name not in OPCODE_NAMES:
                raise ParseError(f"Unknown opcode: {opcode_name!r}")

            opcode = OPCODE_NAMES[opcode_name]

            # Resolve modifier
            if modifier_str:
                modifier = Modifier.from_str(modifier_str)
            else:
                modifier = DEFAULT_MODIFIERS.get(opcode, Modifier.F)

            # Parse operands (everything after opcode)
            operand_str = " ".join(tokens[idx:])
            a_str, b_str = self._split_operands(operand_str)

            instructions_raw.append({
                "opcode": opcode,
                "modifier": modifier,
                "a_str": a_str,
                "b_str": b_str,
                "line": line,
            })

    def _find_keyword(self, tokens: List[str], keyword: str) -> Optional[int]:
        """Find the index of a keyword (case-insensitive) in tokens."""
        for i, t in enumerate(tokens):
            if t.upper() == keyword:
                return i
        return None

    def _split_operands(self, operand_str: str) -> Tuple[Optional[str], Optional[str]]:
        """Split the operand string into A and B operands."""
        operand_str = operand_str.strip()
        if not operand_str:
            return None, None

        # Split on comma, respecting that there may be 0, 1, or 2 operands
        parts = [p.strip() for p in operand_str.split(",")]

        if len(parts) == 1:
            # Single operand — could be A-only or B-only depending on opcode
            return parts[0], None
        elif len(parts) == 2:
            return parts[0], parts[1]
        elif len(parts) > 2:
            raise ParseError(f"Too many operands: {operand_str!r}")
        else:
            return None, None

    def _resolve_org(
        self,
        lines: List[str],
        labels: Dict[str, int],
        equ_constants: Dict[str, str],
    ) -> int:
        """Resolve the ORG / END start offset."""
        for line in lines:
            tokens = line.split()
            if not tokens:
                continue

            if tokens[0].upper() == "ORG":
                if len(tokens) < 2:
                    raise ParseError("ORG without operand")
                expr = " ".join(tokens[1:])
                return self._eval_expr(expr, labels, equ_constants, 0)

            if tokens[0].upper() == "END":
                if len(tokens) >= 2:
                    expr = " ".join(tokens[1:])
                    return self._eval_expr(expr, labels, equ_constants, 0)
                return 0

        return 0  # Default: start at first instruction

    def _build_instruction(
        self,
        raw: dict,
        idx: int,
        labels: Dict[str, int],
        equ_constants: Dict[str, str],
    ) -> Instruction:
        """Build an Instruction from raw parsed data."""
        opcode: Opcode = raw["opcode"]
        modifier: Modifier = raw["modifier"]
        a_str = raw["a_str"]
        b_str = raw["b_str"]

        # Determine which operands to parse based on opcode
        # Most opcodes have two operands; some (JMP, SPL, NOP, DAT) have special rules

        a_mode, a_value = AddressMode.DIRECT, 0
        b_mode, b_value = AddressMode.DIRECT, 0

        if a_str is not None:
            a_mode, a_value = self._parse_operand(a_str, labels, equ_constants, idx)
        if b_str is not None:
            b_mode, b_value = self._parse_operand(b_str, labels, equ_constants, idx)

        # Handle single-operand opcodes
        # JMP, SPL, NOP: single operand goes to A-field
        # DAT with one operand: operand goes to B-field (A defaults to 0)
        if b_str is None and a_str is not None:
            if opcode in (Opcode.JMP, Opcode.SPL, Opcode.NOP):
                # A-field has the operand, B stays default
                pass
            elif opcode == Opcode.DAT:
                # DAT with one operand: move A to B, A becomes 0
                b_mode, b_value = a_mode, a_value
                a_mode, a_value = AddressMode.DIRECT, 0
            else:
                # For other opcodes with one operand, treat as B-field
                b_mode, b_value = a_mode, a_value
                a_mode, a_value = AddressMode.DIRECT, 0

        return Instruction(
            opcode=opcode,
            modifier=modifier,
            a_mode=a_mode,
            a_value=a_value,
            b_mode=b_mode,
            b_value=b_value,
        )

    def _parse_operand(
        self,
        operand: str,
        labels: Dict[str, int],
        equ_constants: Dict[str, str],
        current_idx: int,
    ) -> Tuple[AddressMode, int]:
        """Parse a single operand into (address_mode, value)."""
        operand = operand.strip()
        if not operand:
            return AddressMode.DIRECT, 0

        match = _OPERAND_RE.match(operand)
        if not match:
            raise ParseError(f"Invalid operand: {operand!r}")

        mode_sym = match.group(1)
        expr_str = match.group(2)

        mode = AddressMode.from_str(mode_sym if mode_sym else "")
        value = self._eval_expr(expr_str, labels, equ_constants, current_idx)

        return mode, value

    def _eval_expr(
        self,
        expr: str,
        labels: Dict[str, int],
        equ_constants: Dict[str, str],
        current_idx: int,
    ) -> int:
        """
        Evaluate an expression that may contain:
        - Integer literals
        - Label references (resolved to offset from current instruction)
        - EQU constants
        - Simple arithmetic: +, -, *, /, %, ()
        """
        expr = expr.strip()

        # Substitute EQU constants first (case-insensitive)
        for const_name, const_value in equ_constants.items():
            pattern = r"\b" + re.escape(const_name) + r"\b"
            expr = re.sub(pattern, f"({const_value})", expr, flags=re.IGNORECASE)

        # Substitute labels with their absolute position (case-insensitive)
        # Labels resolve to (label_position - current_idx) for relative addressing
        for label_name, label_pos in labels.items():
            relative = label_pos - current_idx
            pattern = r"\b" + re.escape(label_name) + r"\b"
            expr = re.sub(pattern, str(relative), expr, flags=re.IGNORECASE)

        # Evaluate the arithmetic expression safely
        try:
            result = self._safe_eval(expr)
        except Exception as e:
            raise ParseError(f"Cannot evaluate expression {expr!r}: {e}")

        return result

    def _safe_eval(self, expr: str) -> int:
        """Safely evaluate a simple arithmetic expression."""
        expr = expr.strip()
        if not expr:
            return 0

        # Only allow digits, operators, parentheses, and whitespace
        allowed = set("0123456789+-*/%() \t")
        if not all(c in allowed for c in expr):
            raise ParseError(f"Unsafe expression: {expr!r}")

        # Use Python's eval with restricted globals
        try:
            result = eval(expr, {"__builtins__": {}}, {})
        except Exception as e:
            raise ParseError(f"Eval error for {expr!r}: {e}")

        return int(result)