"""CHIP-8 memory subsystem — 4 KiB address space, font sprites, ROM loading."""

from __future__ import annotations

from typing import List, Optional

# Standard CHIP-8 font sprites (0–F), each 5 bytes.
FONT_SPRITES: List[int] = [
    0xF0, 0x90, 0x90, 0x90, 0xF0,  # 0
    0x20, 0x60, 0x20, 0x20, 0x70,  # 1
    0xF0, 0x10, 0xF0, 0x80, 0xF0,  # 2
    0xF0, 0x10, 0xF0, 0x10, 0xF0,  # 3
    0x90, 0x90, 0xF0, 0x10, 0x10,  # 4
    0xF0, 0x80, 0xF0, 0x10, 0xF0,  # 5
    0xF0, 0x80, 0xF0, 0x90, 0xF0,  # 6
    0xF0, 0x10, 0x20, 0x40, 0x40,  # 7
    0xF0, 0x90, 0xF0, 0x90, 0xF0,  # 8
    0xF0, 0x90, 0xF0, 0x10, 0xF0,  # 9
    0xF0, 0x90, 0xF0, 0x90, 0x90,  # A
    0xE0, 0x90, 0xE0, 0x90, 0xE0,  # B
    0xF0, 0x80, 0x80, 0x80, 0xF0,  # C
    0xE0, 0x90, 0x90, 0x90, 0xE0,  # D
    0xF0, 0x80, 0xF0, 0x80, 0xF0,  # E
    0xF0, 0x80, 0xF0, 0x80, 0x80,  # F
]

FONT_START = 0x050  # Where font sprites live in memory
PROGRAM_START = 0x200  # Where ROMs are loaded
MEMORY_SIZE = 4096  # 4 KiB


class Chip8MemoryError(Exception):
    """Raised on invalid memory access in the CHIP-8 emulator."""


class Memory:
    """CHIP-8 4 KiB address space with font sprites and ROM loading."""

    def __init__(self, size: int = MEMORY_SIZE) -> None:
        self._mem: bytearray = bytearray(size)
        self._load_font()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_font(self) -> None:
        """Copy the standard 5-byte font sprites into low memory."""
        for i, byte in enumerate(FONT_SPRITES):
            self._mem[FONT_START + i] = byte

    # ------------------------------------------------------------------
    # Public API — byte-level
    # ------------------------------------------------------------------

    def read(self, addr: int) -> int:
        """Read a single byte from *addr*."""
        self._check_addr(addr)
        return self._mem[addr]

    def write(self, addr: int, value: int) -> None:
        """Write a single byte to *addr*."""
        self._check_addr(addr)
        if not 0 <= value <= 0xFF:
            raise Chip8MemoryError(f"Value {value:#04x} out of byte range")
        self._mem[addr] = value

    def read_word(self, addr: int) -> int:
        """Read a big-endian 16-bit word starting at *addr*."""
        self._check_addr(addr)
        self._check_addr(addr + 1)
        return (self._mem[addr] << 8) | self._mem[addr + 1]

    # ------------------------------------------------------------------
    # Public API — bulk
    # ------------------------------------------------------------------

    def load_rom(self, data: bytes, offset: int = PROGRAM_START) -> None:
        """Load a ROM image into memory starting at *offset*.

        Raises ``Chip8MemoryError`` if the ROM would overflow the address space
        or the offset is invalid.
        """
        if offset < 0 or offset >= len(self._mem):
            raise Chip8MemoryError(f"Invalid ROM load offset: {offset:#06x}")
        if offset + len(data) > len(self._mem):
            raise Chip8MemoryError(
                f"ROM ({len(data)} bytes) overflows memory at offset {offset:#06x}"
            )
        for i, b in enumerate(data):
            self._mem[offset + i] = b

    def load_rom_from_file(self, path: str, offset: int = PROGRAM_START) -> None:
        """Load a ROM from a file path."""
        with open(path, "rb") as fh:
            data = fh.read()
        self.load_rom(data, offset)

    # ------------------------------------------------------------------
    # Font helpers
    # ------------------------------------------------------------------

    def font_sprite_addr(self, digit: int) -> int:
        """Return the address of the font sprite for hex *digit* (0–F)."""
        if not 0 <= digit <= 0xF:
            raise Chip8MemoryError(f"Invalid font digit: {digit:#x}")
        return FONT_START + digit * 5

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _check_addr(self, addr: int) -> None:
        if not 0 <= addr < len(self._mem):
            raise Chip8MemoryError(f"Address {addr:#06x} out of range [0, {len(self._mem) - 1:#06x})")

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._mem)

    def __repr__(self) -> str:
        return f"Memory(size={len(self._mem)})"