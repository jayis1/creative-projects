"""
Core War — A MARS (Memory Array Redcode Simulator) implementation in Python.

Core War is a programming game where assembly-like programs ("warriors")
battle for control of a virtual computer's memory.
"""

from core_war.mars import MARS, WarriorState, BattleResult, Warrior
from core_war.parser import RedcodeParser, ParseError, ParsedWarrior
from core_war.opcodes import Opcode, Modifier, AddressMode
from core_war.instruction import Instruction
from core_war.loader import load_warrior, load_warriors_from_dir, load_warrior_from_string
from core_war.disassembler import disassemble, disassemble_core, disassemble_around
from core_war.visualizer import core_heatmap, core_summary, format_core_summary, battle_log
from core_war.scheduler import BattleScheduler, BattleStats, TournamentResult

__version__ = "2.0.0"

__all__ = [
    "MARS",
    "WarriorState",
    "BattleResult",
    "Warrior",
    "RedcodeParser",
    "ParseError",
    "ParsedWarrior",
    "Opcode",
    "Modifier",
    "AddressMode",
    "Instruction",
    "load_warrior",
    "load_warriors_from_dir",
    "load_warrior_from_string",
    "disassemble",
    "disassemble_core",
    "disassemble_around",
    "core_heatmap",
    "core_summary",
    "format_core_summary",
    "battle_log",
    "BattleScheduler",
    "BattleStats",
    "TournamentResult",
]