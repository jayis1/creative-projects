"""
RISC-V RV32I Emulator — a full-featured 32-bit RISC-V CPU emulator.

Supports:
  - RV32I base instruction set (40 instructions)
  - Zicsr extension (CSR read/write)
  - Assembler with labels, directives, and pseudo-instructions
  - ELF32 loader
  - Interactive debugger with breakpoints, watchpoints, and step execution
  - Execution profiler and trace recorder
  - Configurable memory map and peripheral I/O
"""

from .cpu import CPU
from .memory import Memory, MemoryRegion
from .assembler import Assembler
from .loader import load_elf, load_binary
from .debugger import Debugger
from .profiler import Profiler
from .tracer import Tracer
from .csrs import CSRFile

__version__ = "1.0.0"
__all__ = [
    "CPU", "Memory", "MemoryRegion", "Assembler",
    "load_elf", "load_binary", "Debugger", "Profiler", "Tracer", "CSRFile",
]