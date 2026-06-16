"""Tests for the ROM validator."""

import pytest
import tempfile
from pathlib import Path

from chip8_emulator.validator import validate_rom, validate_rom_bytes, ValidationResult


class TestValidateRom:
    """Test ROM validation."""

    def test_valid_rom(self, tmp_path):
        """A well-formed ROM should pass validation."""
        rom = bytes([0x00, 0xE0, 0x12, 0x00])  # CLS; JP 0x200
        path = tmp_path / "valid.ch8"
        path.write_bytes(rom)
        result = validate_rom(str(path))
        assert result.ok
        assert result.size == 4

    def test_empty_rom(self, tmp_path):
        """An empty ROM should fail validation."""
        path = tmp_path / "empty.ch8"
        path.write_bytes(b"")
        result = validate_rom(str(path))
        assert not result.ok
        assert "empty" in " ".join(result.errors).lower()

    def test_nonexistent_file(self):
        """A nonexistent file should fail validation."""
        result = validate_rom("/nonexistent/file.ch8")
        assert not result.ok

    def test_oversized_rom(self, tmp_path):
        """A ROM exceeding 3840 bytes should fail validation."""
        rom = bytes(4000)
        path = tmp_path / "big.ch8"
        path.write_bytes(rom)
        result = validate_rom(str(path))
        assert not result.ok
        assert "too large" in " ".join(result.errors).lower()

    def test_odd_sized_rom(self, tmp_path):
        """A ROM with odd byte count should get a warning."""
        rom = bytes([0x12, 0x00, 0xFF])  # 3 bytes — odd
        path = tmp_path / "odd.ch8"
        path.write_bytes(rom)
        result = validate_rom(str(path))
        assert result.ok
        assert any("odd" in w.lower() for w in result.warnings)

    def test_validate_rom_bytes(self):
        """validate_rom_bytes should work with in-memory data."""
        rom = bytes([0x00, 0xE0])
        result = validate_rom_bytes(rom)
        assert result.ok
        assert result.size == 2

    def test_validation_result_str(self):
        """ValidationResult should have a readable string representation."""
        result = ValidationResult(path="test.ch8", size=100, num_instructions=50)
        assert "test.ch8" in str(result)
        assert "PASS" in str(result)

    def test_rom_starting_with_cls(self, tmp_path):
        """ROM starting with CLS should get info message."""
        rom = bytes([0x00, 0xE0, 0x12, 0x00])
        path = tmp_path / "cls.ch8"
        path.write_bytes(rom)
        result = validate_rom(str(path))
        assert any("CLS" in i for i in result.info)

    def test_rom_starting_with_jp(self, tmp_path):
        """ROM starting with JP should get info message."""
        rom = bytes([0x12, 0x00])
        path = tmp_path / "jp.ch8"
        path.write_bytes(rom)
        result = validate_rom(str(path))
        assert any("JP" in i for i in result.info)

    def test_near_limit_rom_warning(self, tmp_path):
        """A ROM near the size limit should get a warning."""
        # 3500 bytes is ~91% of the 3840 limit
        rom = bytes(3500)
        path = tmp_path / "near_limit.ch8"
        path.write_bytes(rom)
        result = validate_rom(str(path))
        assert result.ok
        assert any("near" in w.lower() for w in result.warnings)