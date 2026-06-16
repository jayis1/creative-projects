"""
RISC-V RV32I Emulator — a full-featured 32-bit RISC-V CPU emulator.

Supports:
  - RV32I base instruction set (40 instructions)
  - RV32M extension (multiply/divide)
  - Zicsr extension (CSR read/write)
  - Assembler with labels, directives, and pseudo-instructions
  - Interactive debugger with breakpoints, watchpoints, and step execution
  - Execution profiler and trace recorder
  - UART MMIO output (QEMU virt compatible)
  - Disassembler
  - Configurable memory map and peripheral I/O
"""

from .cpu import CPU, Trap, CPUHalt
from .memory import Memory, MemoryRegion, MemoryError
from .assembler import Assembler
from .disassembler import disassemble, disassemble_to_string
from .loader import load_elf, load_binary
from .debugger import Debugger
from .profiler import Profiler
from .tracer import Tracer
from .csrs import CSRFile

__version__ = "1.1.0"
__all__ = [
    "CPU", "Trap", "CPUHalt", "Memory", "MemoryRegion", "MemoryError",
    "Assembler", "disassemble", "disassemble_to_string",
    "load_elf", "load_binary", "Debugger", "Profiler", "Tracer", "CSRFile",
]