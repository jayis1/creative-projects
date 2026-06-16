"""Binary and ELF32 loader for the RISC-V emulator.

Supports loading:
  - Raw binary files at a specified address
  - ELF32 little-endian executables (ET_EXEC and ET_DYN)
  - Assembled flat binaries with entry point metadata
"""

from __future__ import annotations
import struct
from typing import Dict, List, Optional, Tuple

from .memory import Memory, MemoryRegion


class LoaderError(Exception):
    """Raised when a file cannot be loaded."""
    pass


# ELF constants
ELF_MAGIC = b"\x7fELF"
ELFCLASS32 = 1
ELFDATA2LSB = 1  # Little-endian
ET_EXEC = 2
ET_DYN = 3
EM_RISCV = 243
R_RISCV_32 = 1
R_RISCV_PCREL_HI20 = 23
R_RISCV_PCREL_LO12_I = 24
R_RISCV_PCREL_LO12_S = 25
R_RISCV_CALL = 28
R_RISCV_CALL_PLT = 29


def load_binary(data: bytes, base_addr: int = 0x20000000, size: int = 0,
                perms: str = "rwx") -> Tuple[Memory, int]:
    """Load a raw binary blob into memory.

    Args:
        data: Raw binary data.
        base_addr: Load address.
        size: Region size (0 = auto-size to data length with 4KB alignment).
        perms: Memory permissions.

    Returns:
        Tuple of (Memory with region loaded, entry point address).
    """
    if size == 0:
        size = max(len(data), 4096)
        # Align to 4KB
        size = (size + 4095) & ~4095

    region = MemoryRegion(base_addr, size, perms, data.ljust(size, b"\x00"))
    mem = Memory([region])
    return mem, base_addr


def load_elf(data: bytes) -> Tuple[Memory, int]:
    """Load an ELF32 little-endian RISC-V executable.

    Parses ELF headers and loads PT_LOAD segments into memory regions.

    Returns:
        Tuple of (Memory with segments loaded, entry point address).
    """
    # Validate ELF magic
    if data[:4] != ELF_MAGIC:
        raise LoaderError("Not a valid ELF file (bad magic)")

    # Validate class and endianness
    ei_class = data[4]
    ei_data = data[5]
    if ei_class != ELFCLASS32:
        raise LoaderError(f"Expected ELF32, got class {ei_class}")
    if ei_data != ELFDATA2LSB:
        raise LoaderError(f"Expected little-endian ELF, got data encoding {ei_data}")

    # Parse ELF header
    (e_type, e_machine, e_version, e_entry, e_phoff,
     e_shoff, e_flags, e_ehsize, e_phentsize, e_phnum,
     e_shentsize, e_shnum, e_shstrndx) = struct.unpack_from(
        "<HHIIIIIHHHHHH", data, 16
    )

    if e_machine != EM_RISCV:
        raise LoaderError(f"Expected RISC-V ELF (machine={EM_RISCV}), got machine={e_machine}")

    if e_type not in (ET_EXEC, ET_DYN):
        raise LoaderError(f"Expected executable ELF (type=2 or 3), got type={e_type}")

    # Parse program headers and load PT_LOAD segments
    regions: List[MemoryRegion] = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        (p_type, p_offset, p_vaddr, p_paddr, p_filesz,
         p_memsz, p_flags, p_align) = struct.unpack_from(
            "<IIIIIIII", data, off
        )

        if p_type != 1:  # PT_LOAD
            continue

        # Determine permissions
        perms = ""
        if p_flags & 4:  # PF_R
            perms += "r"
        if p_flags & 2:  # PF_W
            perms += "w"
        if p_flags & 1:  # PF_X
            perms += "x"
        if not perms:
            perms = "rw"

        # Align base address and size
        base = p_vaddr & ~(p_align - 1) if p_align > 1 else p_vaddr
        size = (p_memsz + (p_vaddr - base) + p_align - 1) & ~(p_align - 1) if p_align > 1 else p_memsz

        # Create region data
        region_data = bytearray(size)
        file_offset = p_offset - (p_vaddr - base)  # Adjust for alignment
        if p_filesz > 0 and file_offset + p_filesz <= len(data):
            region_data[p_vaddr - base:p_vaddr - base + p_filesz] = data[file_offset:file_offset + p_filesz]

        regions.append(MemoryRegion(base, size, perms, bytes(region_data)))

    if not regions:
        raise LoaderError("No loadable segments found in ELF")

    mem = Memory(regions)

    # Add a stack region (1MB at 0x80000000, growing down)
    stack_base = 0x7F000000
    stack_size = 0x01000000  # 16 MB
    stack_region = MemoryRegion(stack_base, stack_size, "rw", b"\x00" * stack_size)
    mem.add_region(stack_region)

    return mem, e_entry


def load_file(path: str, base_addr: int = 0x20000000) -> Tuple[Memory, int]:
    """Load a binary or ELF file by path.

    Automatically detects ELF format vs raw binary.
    """
    with open(path, "rb") as f:
        data = f.read()

    if data[:4] == ELF_MAGIC:
        return load_elf(data)
    else:
        return load_binary(data, base_addr)