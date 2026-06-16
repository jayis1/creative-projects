"""CHIP-8 Emulator — a full-featured interpreter for the CHIP-8 virtual machine.

Supports all 35 standard opcodes, SUPER-CHIP extensions (scroll, extended mode,
large fonts, RPL flags), a configurable keypad, 64×32 pixel display, timers,
audio beep, font sprites, debugger, ROM validator, assembler, tracer/profiler,
execution recorder, and multiple ROM loading strategies.
"""

__version__ = "2.0.0"

from .assembler import Assembler, AssemblerError, assemble, AssemblyResult
from .config import EmulatorConfig, load_config, generate_default_config
from .cpu import CPU, CpuError
from .debugger import Debugger
from .display import Display
from .keypad import Keypad
from .memory import Memory, Chip8MemoryError, PROGRAM_START
from .opcodes import OpcodeTable
from .recorder import Recorder, StepRecord
from .sound import SoundTimer
from .timer import DelayTimer
from .tracer import Tracer, ProfileStats
from .validator import validate_rom, validate_rom_bytes, ValidationResult

__all__ = [
    # Core
    "CPU",
    "CpuError",
    "Memory",
    "Chip8MemoryError",
    "PROGRAM_START",
    "Display",
    "Keypad",
    "DelayTimer",
    "SoundTimer",
    "OpcodeTable",
    # Developer tools
    "Debugger",
    "Tracer",
    "ProfileStats",
    "Recorder",
    "StepRecord",
    "Assembler",
    "AssemblerError",
    "AssemblyResult",
    "assemble",
    # Config
    "EmulatorConfig",
    "load_config",
    "generate_default_config",
    # Validation
    "validate_rom",
    "validate_rom_bytes",
    "ValidationResult",
]