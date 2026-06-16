"""CHIP-8 ROM validator — detects common issues with ROM files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class ValidationResult:
    """Result of ROM validation."""

    path: str
    size: int = 0
    num_instructions: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True if no errors were found."""
        return len(self.errors) == 0

    def __str__(self) -> str:
        lines = [f"ROM Validation: {self.path}"]
        lines.append(f"  Size: {self.size} bytes ({self.num_instructions} instructions)")
        for msg in self.info:
            lines.append(f"  INFO: {msg}")
        for msg in self.warnings:
            lines.append(f"  WARN: {msg}")
        for msg in self.errors:
            lines.append(f"  ERROR: {msg}")
        if self.ok:
            lines.append("  PASS ✓")
        else:
            lines.append("  FAIL ✗")
        return "\n".join(lines)


# Common CHIP-8 program signatures
CHIP8_SIGNATURES = {
    b"\x00\xE0": "CLS (clear screen)",
    b"\x00\xEE": "RET (return from subroutine)",
    b"\x12": "JP (jump to address)",
    b"\x22": "CALL (call subroutine)",
}

# Maximum ROM size (4 KiB - 0x200 for font/reserved)
MAX_ROM_SIZE = 4096 - 0x200

# Suspicious byte patterns that might indicate a corrupt ROM
SUSPICIOUS_PATTERNS = [
    (b"\xFF\xFF", "Consecutive 0xFF bytes (might be padding)"),
    (b"\x00\x00", "Consecutive 0x00 bytes (might be padding)"),
]


def validate_rom(path: str) -> ValidationResult:
    """Validate a CHIP-8 ROM file at *path*.

    Checks for:
    - File existence and readability
    - ROM size constraints
    - Common header patterns
    - Suspicious byte sequences
    - Unusual starting addresses
    - Opcode validity (basic scan)
    """
    result = ValidationResult(path=path)

    # Check file exists
    p = Path(path)
    if not p.exists():
        result.errors.append(f"File not found: {path}")
        return result

    if not p.is_file():
        result.errors.append(f"Not a file: {path}")
        return result

    # Read ROM data
    try:
        data = p.read_bytes()
    except OSError as e:
        result.errors.append(f"Cannot read file: {e}")
        return result

    result.size = len(data)

    # Size checks
    if result.size == 0:
        result.errors.append("ROM is empty")
        return result

    if result.size % 2 != 0:
        result.warnings.append(
            f"ROM size ({result.size}) is odd — instructions are 2 bytes"
        )

    result.num_instructions = result.size // 2

    if result.size > MAX_ROM_SIZE:
        result.errors.append(
            f"ROM too large: {result.size} bytes (max {MAX_ROM_SIZE})"
        )
    elif result.size > MAX_ROM_SIZE * 0.9:
        result.warnings.append(
            f"ROM is {result.size} bytes — near the {MAX_ROM_SIZE}-byte limit"
        )

    # Check for common starting patterns
    first_word = (data[0] << 8) | data[1] if len(data) >= 2 else 0
    if first_word == 0x00E0:
        result.info.append("Starts with CLS — common pattern")
    elif (first_word >> 12) == 0x1:
        result.info.append(f"Starts with JP {first_word & 0x0FFF:03X}")
    elif (first_word >> 12) == 0x2:
        result.info.append(f"Starts with CALL {first_word & 0x0FFF:03X}")
    elif (first_word >> 12) == 0x6:
        result.info.append(f"Starts with LD V{(first_word >> 8) & 0xF:X}, {first_word & 0xFF:02X}")
    else:
        result.warnings.append(f"Unusual first opcode: {first_word:04X}")

    # Scan for suspicious patterns
    for pattern, description in SUSPICIOUS_PATTERNS:
        count = data.count(pattern)
        if count > result.num_instructions // 2:
            result.warnings.append(f"High frequency of {description} ({count} occurrences)")

    # Basic opcode validity scan
    invalid_count = 0
    for i in range(0, min(len(data), 512), 2):
        if i + 1 >= len(data):
            break
        opcode = (data[i] << 8) | data[i + 1]
        prefix = (opcode >> 12) & 0xF
        # Check for clearly invalid prefixes
        if prefix == 0 and opcode not in (0x00E0, 0x00EE) and (opcode & 0x0FFF) != 0:
            # 0NNN (machine code call) — acceptable but unusual
            pass
        elif prefix == 5 and (opcode & 0xF) != 0:
            invalid_count += 1
        elif prefix == 8:
            last = opcode & 0xF
            if last not in (0, 1, 2, 3, 4, 5, 6, 7, 0xE):
                invalid_count += 1
        elif prefix == 9 and (opcode & 0xF) != 0:
            invalid_count += 1
        elif prefix == 0xE:
            kk = opcode & 0xFF
            if kk not in (0x9E, 0xA1):
                invalid_count += 1
        elif prefix == 0xF:
            kk = opcode & 0xFF
            if kk not in (0x07, 0x0A, 0x15, 0x18, 0x1E, 0x29, 0x33, 0x55, 0x65):
                invalid_count += 1

    if invalid_count > 0 and invalid_count > result.num_instructions // 4:
        result.warnings.append(
            f"{invalid_count} potentially invalid opcodes detected in first 256 instructions"
        )

    # Check if ROM looks like it has sprite data at the end
    if len(data) > 32:
        # Look for common font-sprite-like patterns in the last 80 bytes
        tail = data[-80:]
        high_byte_count = sum(1 for b in tail if b > 0x7F)
        if high_byte_count > len(tail) // 2:
            result.info.append("ROM ends with high-byte data (possible sprite data)")

    return result


def validate_rom_bytes(data: bytes, name: str = "<bytes>") -> ValidationResult:
    """Validate CHIP-8 ROM data from a bytes object."""
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ch8") as f:
        f.write(data)
        path = f.name
    try:
        return validate_rom(path)
    finally:
        Path(path).unlink(missing_ok=True)