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
  - CLINT timer interrupts
  - Configurable memory map and peripheral I/O
  - State serialization (save/load checkpoints)
  - Disassembler
"""

from .cpu import CPU, Trap, CPUHalt
from .memory import Memory, MemoryRegion, MemoryError
from .assembler import Assembler, AssembleError
from .disassembler import disassemble, disassemble_to_string
from .loader import load_elf, load_binary, load_file
from .debugger import Debugger
from .profiler import Profiler
from .tracer import Tracer, TraceEntry
from .csrs import CSRFile, CSRError
from .config import EmulatorConfig, CPUConfig, UARTConfig, MemoryRegionConfig, TraceConfig
from .state import StateSerializer
from .devices import MMIODevice, UARTDevice, CLINTDevice, DeviceBus
from .logging_utils import setup_logging, get_logger

__version__ = "2.0.0"
__all__ = [
    "CPU", "Trap", "CPUHalt", "Memory", "MemoryRegion", "MemoryError",
    "Assembler", "AssembleError", "disassemble", "disassemble_to_string",
    "load_elf", "load_binary", "load_file",
    "Debugger", "Profiler", "Tracer", "TraceEntry", "CSRFile", "CSRError",
    "EmulatorConfig", "CPUConfig", "UARTConfig", "MemoryRegionConfig", "TraceConfig",
    "StateSerializer", "MMIODevice", "UARTDevice", "CLINTDevice", "DeviceBus",
    "setup_logging", "get_logger",
]