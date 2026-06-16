"""CHIP-8 Emulator — a full-featured interpreter for the CHIP-8 virtual machine.

Supports all 35 standard opcodes, a configurable keypad, 64×32 pixel display,
timers, audio beep, font sprites, and multiple ROM loading strategies.
"""

__version__ = "1.0.0"

from .cpu import CPU
from .display import Display
from .keypad import Keypad
from .memory import Memory
from .opcodes import OpcodeTable
from .sound import SoundTimer
from .timer import DelayTimer

__all__ = [
    "CPU",
    "Display",
    "Keypad",
    "Memory",
    "OpcodeTable",
    "DelayTimer",
    "SoundTimer",
]