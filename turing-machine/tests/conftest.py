"""
Test suite for the Turing machine simulator.

Run with: pytest tests/ -v
"""

from turing_machine.machine import (
    Tape,
    Transition,
    TMDirection,
    Program,
    TuringMachine,
    MultiTapeTM,
)
from turing_machine.machines import (
    binary_incrementer,
    binary_decrementer,
    unary_adder,
    palindrome_checker,
    copy_machine,
    busy_beaver,
    two_tape_adder,
    TagSystem,
    get_machine,
    list_machines,
)
from turing_machine.def_parser import parse, parse_file, Parser, ParseError
from turing_machine.debugger import Debugger, Breakpoint
from turing_machine.serialization import (
    serialize_machine,
    deserialize_machine,
    save_machine,
    load_machine,
    serialize_program,
    deserialize_program,
)
from turing_machine.analysis import (
    reachable_states,
    dead_states,
    unused_states,
    analyze_machine,
    tape_statistics,
)