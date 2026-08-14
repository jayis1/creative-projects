"""
Core War — A MARS (Memory Array Redcode Simulator) implementation in Python.

Core War is a programming game where assembly-like programs ("warriors")
battle for control of a virtual computer's memory.
"""

from core_war.mars import MARS, Warrior, BattleResult
from core_war.parser import RedcodeParser, ParseError
from core_war.opcodes import Opcode, Modifier, AddressMode

__version__ = "1.0.0"

__all__ = [
    "MARS",
    "Warrior",
    "BattleResult",
    "RedcodeParser",
    "ParseError",
    "Opcode",
    "Modifier",
    "AddressMode",
]