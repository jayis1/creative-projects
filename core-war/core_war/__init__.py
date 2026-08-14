"""
Core War — A MARS (Memory Array Redcode Simulator) implementation in Python.

Core War is a programming game where assembly-like programs ("warriors")
battle for control of a virtual computer's memory.

This package provides:
  - Full ICWS'94 Redcode instruction set (16 opcodes, 7 modifiers, 8 modes)
  - Redcode parser (labels, EQU constants, ORG/END, expressions)
  - MARS virtual machine with step-through execution
  - Battle scheduler and tournament system
  - Disassembler and core memory visualizer
  - Strategy analyzer for warrior classification
  - Battle recording and replay system
  - Genetic algorithm for evolving warriors
  - Configuration management (YAML/JSON)
  - Structured logging
  - CLI interface with 9 subcommands
"""

from core_war.mars import MARS, WarriorState, BattleResult, Warrior
from core_war.parser import RedcodeParser, ParseError, ParsedWarrior
from core_war.opcodes import Opcode, Modifier, AddressMode
from core_war.instruction import Instruction
from core_war.loader import load_warrior, load_warriors_from_dir, load_warrior_from_string
from core_war.disassembler import disassemble, disassemble_core, disassemble_around
from core_war.visualizer import core_heatmap, core_summary, format_core_summary, battle_log
from core_war.scheduler import BattleScheduler, BattleStats, TournamentResult
from core_war.config import BattleConfig, load_config
from core_war.logging_config import setup_logging, get_logger
from core_war.strategy_analyzer import StrategyAnalyzer, AnalysisResult, StrategyType, Vulnerability
from core_war.replay import BattleRecorder, BattleReplay, BattleRecording, CycleSnapshot
from core_war.mutator import GeneticEvolver, WarriorMutator, Individual, PopulationStats

__version__ = "3.0.0"

__all__ = [
    # Core engine
    "MARS",
    "WarriorState",
    "BattleResult",
    "Warrior",
    # Parser
    "RedcodeParser",
    "ParseError",
    "ParsedWarrior",
    # Opcodes and instructions
    "Opcode",
    "Modifier",
    "AddressMode",
    "Instruction",
    # Loader
    "load_warrior",
    "load_warriors_from_dir",
    "load_warrior_from_string",
    # Disassembler
    "disassemble",
    "disassemble_core",
    "disassemble_around",
    # Visualizer
    "core_heatmap",
    "core_summary",
    "format_core_summary",
    "battle_log",
    # Scheduler
    "BattleScheduler",
    "BattleStats",
    "TournamentResult",
    # Configuration
    "BattleConfig",
    "load_config",
    # Logging
    "setup_logging",
    "get_logger",
    # Strategy analyzer
    "StrategyAnalyzer",
    "AnalysisResult",
    "StrategyType",
    "Vulnerability",
    # Replay
    "BattleRecorder",
    "BattleReplay",
    "BattleRecording",
    "CycleSnapshot",
    # Genetic evolution
    "GeneticEvolver",
    "WarriorMutator",
    "Individual",
    "PopulationStats",
]