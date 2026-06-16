"""Memory subsystem for the RISC-V emulator.

Provides a sparse, region-based memory model with configurable permissions,
memory-mapped I/O callbacks, and efficient address translation.
"""

from __future__ import annotations
import struct
from typing import Callable, Dict, List, Optional, Tuple


class MemoryError(Exception):
    """Raised on invalid memory access (out of range, wrong permissions)."""
    pass


class MemoryRegion:
    """A contiguous memory region with base address, size, and permissions.

    Attributes:
        base: Start address of the region.
        size: Size in bytes.
        perms: Permission string: combination of 'r', 'w', 'x'.
        data: Backing byte buffer.
        io_read: Optional callback(addr, size) for memory-mapped reads.
        io_write: Optional callback(addr, value, size) for memory-mapped writes.
    """

    def __init__(
        self,
        base: int,
        size: int,
        perms: str = "rwx",
        data: Optional[bytes] = None,
        io_read: Optional[Callable[[int, int], int]] = None,
        io_write: Optional[Callable[[int, int, int], None]] = None,
    ):
        if size <= 0:
            raise ValueError(f"Region size must be positive, got {size}")
        if not all(c in "rwx" for c in perms):
            raise ValueError(f"Invalid permissions '{perms}'; use combination of r/w/x")
        self.base = base
        self.size = size
        self.perms = set(perms)
        self.data = bytearray(data) if data else bytearray(size)
        self.io_read = io_read
        self.io_write = io_write

    def contains(self, addr: int) -> bool:
        return self.base <= addr < self.base + self.size

    def check_perm(self, perm: str, addr: int) -> None:
        if perm not in self.perms:
            raise MemoryError(
                f"Permission '{perm}' denied at 0x{addr:08x} "
                f"(region 0x{self.base:08x}-0x{self.base+self.size-1:08x} has "
                f"perms {''.join(sorted(self.perms))})"
            )


class Memory:
    """Sparse memory system backed by multiple overlapping regions.

    Supports byte, half-word (16-bit), word (32-bit), and double-word (64-bit)
    access with little-endian byte ordering.
    """

    def __init__(self, regions: Optional[List[MemoryRegion]] = None):
        self.regions: List[MemoryRegion] = list(regions) if regions else []
        self._sort()

    def _sort(self) -> None:
        """Sort regions by base address for fast lookup."""
        self.regions.sort(key=lambda r: r.base)

    def add_region(self, region: MemoryRegion) -> None:
        """Add a memory region. Overlapping regions are resolved by later-wins."""
        self.regions.append(region)
        self._sort()

    def _find_region(self, addr: int) -> Optional[MemoryRegion]:
        """Find the region containing `addr`."""
        # Binary search for performance
        lo, hi = 0, len(self.regions) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            r = self.regions[mid]
            if addr < r.base:
                hi = mid - 1
            elif addr >= r.base + r.size:
                lo = mid + 1
            else:
                return r
        return None

    def _resolve(self, addr: int, perm: str) -> MemoryRegion:
        """Resolve address to a region and check permissions."""
        region = self._find_region(addr)
        if region is None:
            raise MemoryError(f"No memory mapped at 0x{addr:08x}")
        region.check_perm(perm, addr)
        return region

    def read_byte(self, addr: int) -> int:
        region = self._resolve(addr, "r")
        if region.io_read:
            return region.io_read(addr, 1)
        return region.data[addr - region.base]

    def read_half(self, addr: int) -> int:
        region = self._resolve(addr, "r")
        if addr & 1:
            raise MemoryError(f"Unaligned half-word read at 0x{addr:08x}")
        if region.io_read:
            return region.io_read(addr, 2)
        off = addr - region.base
        return struct.unpack_from("<H", region.data, off)[0]

    def read_word(self, addr: int) -> int:
        region = self._resolve(addr, "r")
        if addr & 3:
            raise MemoryError(f"Unaligned word read at 0x{addr:08x}")
        if region.io_read:
            return region.io_read(addr, 4)
        off = addr - region.base
        return struct.unpack_from("<I", region.data, off)[0]

    def read_dword(self, addr: int) -> int:
        region = self._resolve(addr, "r")
        if addr & 7:
            raise MemoryError(f"Unaligned double-word read at 0x{addr:08x}")
        if region.io_read:
            return region.io_read(addr, 8)
        off = addr - region.base
        return struct.unpack_from("<Q", region.data, off)[0]

    def write_byte(self, addr: int, value: int) -> None:
        region = self._resolve(addr, "w")
        if region.io_write:
            region.io_write(addr, value & 0xFF, 1)
            return
        region.data[addr - region.base] = value & 0xFF

    def write_half(self, addr: int, value: int) -> None:
        region = self._resolve(addr, "w")
        if addr & 1:
            raise MemoryError(f"Unaligned half-word write at 0x{addr:08x}")
        if region.io_write:
            region.io_write(addr, value & 0xFFFF, 2)
            return
        off = addr - region.base
        struct.pack_into("<H", region.data, off, value & 0xFFFF)

    def write_word(self, addr: int, value: int) -> None:
        region = self._resolve(addr, "w")
        if addr & 3:
            raise MemoryError(f"Unaligned word write at 0x{addr:08x}")
        if region.io_write:
            region.io_write(addr, value & 0xFFFFFFFF, 4)
            return
        off = addr - region.base
        struct.pack_into("<I", region.data, off, value & 0xFFFFFFFF)

    def write_dword(self, addr: int, value: int) -> None:
        region = self._resolve(addr, "w")
        if addr & 7:
            raise MemoryError(f"Unaligned double-word write at 0x{addr:08x}")
        if region.io_write:
            region.io_write(addr, value & 0xFFFFFFFFFFFFFFFF, 8)
            return
        off = addr - region.base
        struct.pack_into("<Q", region.data, off, value & 0xFFFFFFFFFFFFFFFF)

    def read_bytes(self, addr: int, length: int) -> bytes:
        """Read a range of bytes. Does not cross region boundaries."""
        region = self._resolve(addr, "r")
        if region.io_read:
            # Fall back to byte-by-byte for I/O regions
            return bytes(region.io_read(addr + i, 1) for i in range(length))
        off = addr - region.base
        end = off + length
        if end > region.size:
            raise MemoryError(f"Read of {length} bytes at 0x{addr:08x} overflows region")
        return bytes(region.data[off:end])

    def write_bytes(self, addr: int, data: bytes) -> None:
        """Write a range of bytes. Does not cross region boundaries."""
        region = self._resolve(addr, "w")
        if region.io_write:
            for i, b in enumerate(data):
                region.io_write(addr + i, b, 1)
            return
        off = addr - region.base
        end = off + len(data)
        if end > region.size:
            raise MemoryError(f"Write of {len(data)} bytes at 0x{addr:08x} overflows region")
        region.data[off:end] = data

    def dump(self, start: int, length: int) -> str:
        """Hexdump `length` bytes from `start`."""
        lines = []
        for offset in range(0, length, 16):
            addr = start + offset
            try:
                chunk = self.read_bytes(addr, min(16, length - offset))
            except MemoryError:
                break
            hex_part = " ".join(f"{b:02x}" for b in chunk)
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            lines.append(f"0x{addr:08x}  {hex_part:<48s}  {ascii_part}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        parts = []
        for r in self.regions:
            parts.append(f"0x{r.base:08x}-0x{r.base+r.size-1:08x} ({''.join(sorted(r.perms))})")
        return f"Memory([{', '.join(parts)}])"