"""CHIP-8 Emulator — a full-featured interpreter for the CHIP-8 virtual machine.

Supports all 35 standard opcodes, SUPER-CHIP extensions (scroll, extended mode,
large fonts, RPL flags), a configurable keypad, 64×32 pixel display, timers,
audio beep, font sprites, debugger, ROM validator, and multiple ROM loading
strategies.
"""

__version__ = "1.1.0"

from .cpu import CPU
from .debugger import Debugger
from .display import Display
from .keypad import Keypad
from .memory import Memory, Chip8MemoryError
from .opcodes import OpcodeTable
from .sound import SoundTimer
from .timer import DelayTimer
from .validator import validate_rom, validate_rom_bytes, ValidationResult

__all__ = [
    "CPU",
    "Debugger",
    "Display",
    "Keypad",
    "Memory",
    "Chip8MemoryError",
    "OpcodeTable",
    "DelayTimer",
    "SoundTimer",
    "validate_rom",
    "validate_rom_bytes",
    "ValidationResult",
]