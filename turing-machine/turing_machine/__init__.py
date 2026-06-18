"""
turing_machine
==============

A Turing machine simulator supporting single-tape and multi-tape machines,
a universal Turing machine, halting analysis, tape visualization,
debugging, serialization, and a small definition language for declaring machines.

Public API
----------
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
- ``Debugger``       -- step-through debugger with breakpoints.
- ``TagSystem``      -- tag system simulator (another computational model).
- ``run``            -- convenience runner returning the final tape(s).

Analysis functions:
- ``reachable_states``   -- states reachable from the initial state
- ``dead_states``        -- reachable states that can never reach a halt
- ``unused_states``      -- states defined but never reachable
- ``analyze_machine``    -- comprehensive machine analysis
- ``tape_statistics``    -- statistics about tape contents
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
from .debugger import Debugger, Breakpoint
from .serialization import (
    serialize_machine, deserialize_machine,
    save_machine, load_machine,
    serialize_program, deserialize_program,
    serialize_tape, deserialize_tape,
)
from .analysis import (
    reachable_states,
    dead_states,
    unused_states,
    state_transition_count,
    tape_statistics,
    estimate_steps,
    analyze_machine,
)
from .machines import TagSystem
from .universal import (
    UniversalTuringMachine,
    EncodedUTM,
    encode_machine,
    decode_machine,
    simulate,
)
from .visualizer import (
    text_trace,
    html_animation,
    svg_diagram,
    csv_trace,
)
from .composition import (
    Pipeline,
    Conditional,
    Loop,
    compose,
)
from .config import (
    ConfigError,
    load_config,
    config_to_machine,
    save_config,
)

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
    "Debugger",
    "Breakpoint",
    "TagSystem",
    "UniversalTuringMachine",
    "EncodedUTM",
    "encode_machine",
    "decode_machine",
    "simulate",
    "text_trace",
    "html_animation",
    "svg_diagram",
    "csv_trace",
    "Pipeline",
    "Conditional",
    "Loop",
    "compose",
    "ConfigError",
    "load_config",
    "config_to_machine",
    "save_config",
    "serialize_machine",
    "deserialize_machine",
    "save_machine",
    "load_machine",
    "serialize_program",
    "deserialize_program",
    "serialize_tape",
    "deserialize_tape",
    "reachable_states",
    "dead_states",
    "unused_states",
    "state_transition_count",
    "tape_statistics",
    "estimate_steps",
    "analyze_machine",
]

__version__ = "3.0.0"