"""
turing_machine
==============

A Turing machine simulator supporting single-tape and multi-tape machines,
a universal Turing machine, halting-state analysis, tape visualization,
and a small definition language for declaring machines.

Public API
---------
- ``Tape``           -- a single infinite tape (bounded by a ring buffer).
- ``Transition``     -- one (state, symbol) -> (state, symbol, move) rule.
- ``TMRule``         -- alias for ``Transition``.
- ``TMDirection``    -- enum: LEFT, RIGHT, STAY.
- ``TuringMachine``  -- single-tape machine.
- ``MultiTapeTM``    -- multi-tape machine.
- ``Machine``        -- backward-compatible alias for ``TuringMachine``.
- ``Program``        -- collection of transitions keyed by (state, symbol).
- ``MachineDef``     -- high-level machine definition used by the parser.
- ``Parser``         -- parse the definition language.
- ``run``            -- convenience runner returning the final tape(s).
"""

from .machine import (
    Tape,
    Transition,
    TMRule,
    TMDirection,
    TuringMachine,
    MultiTapeTM,
    Machine,
    Program,
)
from .def_parser import MachineDef, Parser, ParseError

__all__ = [
    "Tape",
    "Transition",
    "TMRule",
    "TMDirection",
    "TuringMachine",
    "MultiTapeTM",
    "Machine",
    "Program",
    "MachineDef",
    "Parser",
    "ParseError",
]

__version__ = "1.0.0"