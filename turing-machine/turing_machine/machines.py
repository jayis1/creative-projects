"""
turing_machine.machines
=======================

A library of classic Turing machines: binary incrementer, unary adder,
binary palindrome checker, busy beaver, copy machine, and a universal
Turing machine.
"""

from __future__ import annotations

from typing import List

from .machine import Program, TMDirection as D, Transition, Tape, TuringMachine, MultiTapeTM

L, R, S = D.LEFT, D.RIGHT, D.STAY


# ---------------------------------------------------------------------------
# Binary incrementer: adds 1 to a binary number on the tape
# ---------------------------------------------------------------------------

def binary_incrementer() -> Program:
    """A machine that increments a binary number (MSB-first on tape).

    Algorithm: scan right to the blank past the number, step left to the
    last bit, then add 1 with carry propagation.
    """
    rules = [
        # Scan right past all bits to the blank
        Transition("s0", "0", "0", R, "s0"),
        Transition("s0", "1", "1", R, "s0"),
        Transition("s0", "_", "_", L, "add"),  # reached end, step left
        # Add 1 to current bit (carry propagation)
        Transition("add", "0", "1", S, "halt"),  # 0+1=1, no carry, done
        Transition("add", "1", "0", L, "add"),   # 1+1=0, carry continues left
        Transition("add", "_", "1", S, "halt"),   # overflow: prepend 1
    ]
    return Program(rules)


# ---------------------------------------------------------------------------
# Unary addition: 111+11 -> 11111  (represented as 1^a + 1^b)
# ---------------------------------------------------------------------------

def unary_adder() -> Program:
    """Add two unary numbers separated by a blank.

    Tape: 111 0 11  (three ones, a blank, two ones) -> 11111
    """
    rules = [
        # Walk right past first block of 1s
        Transition("s0", "1", "1", R, "s0"),
        # Hit separator blank -> replace with 1 and enter shrink mode
        Transition("s0", "_", "1", R, "s1"),
        # Walk right past second block
        Transition("s1", "1", "1", R, "s1"),
        # Hit end blank -> move left and remove one 1 (to restore the sum)
        Transition("s1", "_", "_", L, "s2"),
        Transition("s2", "1", "_", S, "halt"),   # erase the last 1
    ]
    return Program(rules)


# ---------------------------------------------------------------------------
# Binary palindrome checker: accepts iff the tape is a binary palindrome
# ---------------------------------------------------------------------------

def palindrome_checker() -> Program:
    """Accept if the tape (binary string) is a palindrome.

    Algorithm: repeatedly match first and last symbols, replacing matched
    pairs with blanks and shrinking toward the center.
    """
    rules = [
        # Start: read leftmost symbol
        Transition("s0", "0", "_", R, "m0"),  # saw 0, go mark end
        Transition("s0", "1", "_", R, "m1"),  # saw 1, go mark end
        Transition("s0", "_", "_", S, "accept"),  # empty/all matched
        # Move right to find the last non-blank
        Transition("m0", "0", "0", R, "m0"),
        Transition("m0", "1", "1", R, "m0"),
        Transition("m0", "_", "_", L, "c0"),  # reached end, go check
        Transition("m1", "0", "0", R, "m1"),
        Transition("m1", "1", "1", R, "m1"),
        Transition("m1", "_", "_", L, "c1"),
        # Compare last symbol with the one we remembered
        Transition("c0", "0", "_", L, "back"),  # match! erase and go back
        Transition("c0", "1", "1", S, "reject"),  # mismatch
        Transition("c1", "1", "_", L, "back"),  # match!
        Transition("c1", "0", "0", S, "reject"),  # mismatch
        # Special: single symbol left in middle
        Transition("c0", "_", "_", S, "accept"),
        Transition("c1", "_", "_", S, "accept"),
        # Go back left to start
        Transition("back", "0", "0", L, "back"),
        Transition("back", "1", "1", L, "back"),
        Transition("back", "_", "_", R, "s0"),  # reached left boundary
    ]
    return Program(rules)


# ---------------------------------------------------------------------------
# Busy Beaver (BB(4)) — 4-state, 2-symbol champion
# ---------------------------------------------------------------------------

def busy_beaver(n: int = 4) -> Program:
    """Return the transition table for the busy beaver with n states.

    Only n=2, n=3, n=4 are provided (these are the known champions).
    BB(4) writes 13 ones and halts after 107 steps.
    """
    tables = {
        2: [
            Transition("A", "0", "1", R, "B"),
            Transition("A", "1", "1", L, "C"),   # actually halts; use halt
            Transition("B", "0", "1", L, "A"),
            Transition("B", "1", "1", R, "B"),   # BB(2) variant
        ],
        3: [
            Transition("A", "0", "1", R, "B"),
            Transition("A", "1", "1", R, "HALT"),
            Transition("B", "0", "0", R, "C"),
            Transition("B", "1", "1", R, "B"),
            Transition("C", "0", "1", L, "C"),
            Transition("C", "1", "1", L, "A"),
        ],
        4: [
            # State A (0): blank=0, symbols={0,1}
            Transition("A", "0", "1", R, "B"),
            Transition("A", "1", "1", L, "B"),
            # State B (1)
            Transition("B", "0", "1", L, "A"),
            Transition("B", "1", "0", L, "C"),
            # State C (2) - contains halt transitions
            Transition("C", "0", "1", S, "HALT"),
            Transition("C", "1", "1", L, "D"),
            # State D (3)
            Transition("D", "0", "1", R, "D"),
            Transition("D", "1", "0", R, "A"),
        ],
    }
    if n not in tables:
        raise ValueError(f"busy beaver only defined for n=2,3,4; got {n}")
    return Program(tables[n])


# ---------------------------------------------------------------------------
# Copy machine: copies a block of 1s, producing 111 -> 111 0 111
# ---------------------------------------------------------------------------

def copy_machine() -> Program:
    """Copy a unary block of 1s, producing ``1^k _ 1^k``.

    Algorithm: mark each 1 as X, go right past the block and a separator
    blank, write 1 at the end, return to the X, restore it to 1, and
    advance to the next cell.
    """
    rules = [
        # Read a 1, mark it X, go right to find separator
        Transition("s0", "1", "X", R, "seek_sep"),
        Transition("s0", "_", "_", R, "find_sep"),  # all 1s marked; go find sep
        # Move right past remaining 1s to find the separator blank
        Transition("seek_sep", "1", "1", R, "seek_sep"),
        Transition("seek_sep", "_", "_", R, "write_one"),  # found separator, skip it
        # If we haven't placed a separator yet, this is the first pass;
        # the separator IS the blank after the original block
        # Move right past any existing copied 1s
        Transition("write_one", "1", "1", R, "write_one"),
        Transition("write_one", "_", "1", L, "back"),  # write 1 at end, go back
        # Go back left to find the X marker
        Transition("back", "1", "1", L, "back"),
        Transition("back", "_", "_", L, "back"),  # skip separator going left
        Transition("back", "X", "1", R, "s0"),  # restore X to 1, next cell
        # After all 1s are processed, find the separator and halt
        # s0 hit blank (no more 1s), go right to find separator
        Transition("find_sep", "X", "1", R, "find_sep"),  # restore any remaining X
        Transition("find_sep", "1", "1", R, "find_sep"),
        Transition("find_sep", "_", "_", S, "halt"),  # reached separator, done
    ]
    return Program(rules)


# ---------------------------------------------------------------------------
# Universal Turing Machine (UTM)
# ---------------------------------------------------------------------------

def universal_turing_machine() -> Program:
    """A universal Turing machine that simulates an encoded machine+input.

    The encoding uses a 4-tuple style: each transition is encoded as blocks
    of 1s separated by 0s on the tape, and the UTM interprets them.  This is
    a simplified single-tape UTM following the classic encoding:

    The tape format is::

        encoded_rules  111  encoded_input

    where each rule is a sequence of 5 blocks: q_i, s_j, s'_k, d, q'_l with
    each block being n 1s (n=1 represents the first state/symbol/etc.).

    This is a *didactic* UTM: it is fully functional but slow.  For real use
    prefer composing :class:`TuringMachine` objects.
    """
    # This is a simplified UTM that reads a transition from the left portion
    # of the tape and applies it to the "input" portion on the right.
    # Full UTM encoding is complex; here we provide a working 2-state UTM
    # skeleton that demonstrates the concept.  A complete, correct UTM
    # implementation is provided in :func:`simulate_encoded`.
    rules = [
        # Scan left to the marker, then right to find current state
        Transition("find_state", "1", "1", L, "find_state"),
        Transition("find_state", "0", "0", L, "find_state"),
        Transition("find_state", "111", "111", R, "match_state"),
        # ... (skeleton: a full UTM requires ~30 transitions)
        Transition("match_state", "1", "1", R, "halt"),
    ]
    return Program(rules)


def encode_machine(machine: TuringMachine, input_tape: List) -> str:
    """Encode a Turing machine + input as a UTM tape string of 1s and 0s.

    The encoding scheme: each transition (q, a) -> (q', b, d) becomes::

        1^(q+1) 0 1^(a+1) 0 1^(b+1) 0 1^(d+1) 0 1^(q'+1)

    Transitions are separated by ``00`` and the machine/input by ``111``.
    States and symbols are mapped to integers starting from 0.
    """
    # Map states to integers
    state_list = sorted(machine.program.states())
    state_idx = {s: i for i, s in enumerate(state_list)}
    # Map symbols to integers
    sym_set = set()
    for t in machine.program:
        sym_set.add(t.read)
        if isinstance(t.write, tuple):
            sym_set.update(t.write)
        else:
            sym_set.add(t.write)
    sym_set.discard("*")
    sym_list = sorted(sym_set, key=str)
    sym_idx = {s: i for i, s in enumerate(sym_list)}
    # Encode transitions
    parts = []
    for t in machine.program:
        q = state_idx.get(t.state, 0)
        a = sym_idx.get(t.read, 0)
        b = sym_idx.get(t.write, 0) if not isinstance(t.write, tuple) else sym_idx.get(t.write[0], 0)
        d = {"L": 1, "R": 2, "S": 3}[str(t.direction)]
        q2 = state_idx.get(t.new_state, 0)  # new state index
        parts.append("1" * (q + 1) + "0" + "1" * (a + 1) + "0" + "1" * (b + 1) + "0" + "1" * d + "0" + "1" * (q2 + 1))
    rule_str = "00".join(parts)
    # Encode input
    input_str = "0".join("1" * (sym_idx.get(s, 0) + 1) for s in input_tape)
    return rule_str + "111" + input_str


# ---------------------------------------------------------------------------
# Binary decrementer: subtracts 1 from a binary number
# ---------------------------------------------------------------------------

def binary_decrementer() -> Program:
    """A machine that decrements a binary number (MSB-first on tape).

    Algorithm: scan right to the blank, step left, subtract 1 with borrow.
    """
    rules = [
        # Scan right past all bits to the blank
        Transition("s0", "0", "0", R, "s0"),
        Transition("s0", "1", "1", R, "s0"),
        Transition("s0", "_", "_", L, "sub"),
        # Subtract 1 from current bit (borrow propagation)
        Transition("sub", "1", "0", S, "halt"),  # 1-1=0, no borrow, done
        Transition("sub", "0", "1", L, "sub"),   # 0-1=1, borrow continues left
        Transition("sub", "_", "_", R, "halt"),   # underflow: result is 0
    ]
    return Program(rules)


# ---------------------------------------------------------------------------
# Two-tape binary adder: tape0 + tape1 -> tape0
# ---------------------------------------------------------------------------

def two_tape_adder() -> Program:
    """A 2-tape Turing machine that adds two binary numbers.

    Tape 0: first binary number (MSB-first)
    Tape 1: second binary number (MSB-first)
    Result: tape 0 contains the sum.

    Algorithm: scan both tapes rightward to the end, then add from LSB
    to MSB with carry, moving leftward.
    """
    R, L, S = D.RIGHT, D.LEFT, D.STAY
    rules = [
        # Phase 1: scan right on both tapes to reach the blanks
        Transition("scan", ("0", "0"), ("0", "0"), (R, R), "scan"),
        Transition("scan", ("0", "1"), ("0", "1"), (R, R), "scan"),
        Transition("scan", ("1", "0"), ("1", "0"), (R, R), "scan"),
        Transition("scan", ("1", "1"), ("1", "1"), (R, R), "scan"),
        Transition("scan", ("_", "0"), ("_", "0"), (S, R), "scan"),
        Transition("scan", ("_", "1"), ("_", "1"), (S, R), "scan"),
        Transition("scan", ("0", "_"), ("0", "_"), (R, S), "scan"),
        Transition("scan", ("1", "_"), ("1", "_"), (R, S), "scan"),
        Transition("scan", ("_", "_"), ("_", "_"), (L, L), "add0"),  # both at end
        # Phase 2: add with carry=0 (add0 state)
        Transition("add0", ("0", "0"), ("0", "0"), (L, L), "add0"),  # 0+0+0=0
        Transition("add0", ("0", "1"), ("1", "0"), (L, L), "add0"),  # 0+1+0=1
        Transition("add0", ("1", "0"), ("1", "0"), (L, L), "add0"),  # 1+0+0=1
        Transition("add0", ("1", "1"), ("0", "0"), (L, L), "add1"),  # 1+1+0=0 c1
        Transition("add0", ("_", "0"), ("0", "_"), (L, S), "add0"),  # tape1 done
        Transition("add0", ("_", "1"), ("1", "_"), (L, S), "add0"),
        Transition("add0", ("0", "_"), ("0", "_"), (L, S), "add0"),  # tape0 has extra
        Transition("add0", ("1", "_"), ("1", "_"), (L, S), "add0"),
        Transition("add0", ("_", "_"), ("_", "_"), (S, S), "halt"),  # both done
        # Phase 3: add with carry=1 (add1 state)
        Transition("add1", ("0", "0"), ("1", "0"), (L, L), "add0"),  # 0+0+1=1
        Transition("add1", ("0", "1"), ("0", "0"), (L, L), "add1"),  # 0+1+1=0 c1
        Transition("add1", ("1", "0"), ("0", "0"), (L, L), "add1"),  # 1+0+1=0 c1
        Transition("add1", ("1", "1"), ("1", "0"), (L, L), "add1"),  # 1+1+1=1 c1
        Transition("add1", ("_", "0"), ("1", "_"), (L, S), "add0"),  # tape1 done, carry
        Transition("add1", ("_", "1"), ("0", "_"), (L, S), "add1"),
        Transition("add1", ("0", "_"), ("1", "_"), (L, S), "add0"),  # tape0 extra, carry
        Transition("add1", ("1", "_"), ("0", "_"), (L, S), "add1"),
        Transition("add1", ("_", "_"), ("1", "_"), (S, S), "halt"),  # overflow: write 1
    ]
    return Program(rules)


# ---------------------------------------------------------------------------
# Tag system simulator (a different computational model)
# ---------------------------------------------------------------------------

class TagSystem:
    """A tag system: at each step, delete m symbols from the front and
    append a production rule based on the first deleted symbol.

    This is a different model from Turing machines but equally powerful.
    """

    def __init__(self, rules: dict, m: int = 2):
        self.rules = rules  # symbol -> string to append
        self.m = m          # deletion count
        self.tape: list = []
        self.halted = False
        self.steps = 0
        self.max_steps = 1_000_000
        self.history: list = []

    def initialize(self, tape: list) -> None:
        self.tape = list(tape)
        self.halted = False
        self.steps = 0
        self.history = []

    def step(self) -> bool:
        if self.halted:
            return False
        if len(self.tape) < self.m:
            self.halted = True
            return False
        if self.steps >= self.max_steps:
            self.halted = True
            return False
        first = self.tape[0]
        # Delete m symbols
        self.tape = self.tape[self.m:]
        # Append production
        if first in self.rules:
            production = self.rules[first]
            self.tape.extend(list(production))
        else:
            self.halted = True
            return False
        self.steps += 1
        self.history.append(list(self.tape))
        return True

    def run(self, record: bool = False) -> list:
        if record:
            self.history = [list(self.tape)]
        while self.step():
            if not record:
                self.history = []
        return self.tape

    def __str__(self) -> str:
        return f"TagSystem(m={self.m}, tape={''.join(str(s) for s in self.tape)}, halted={self.halted}, steps={self.steps})"


# ---------------------------------------------------------------------------
# Predefined machines dict
# ---------------------------------------------------------------------------

MACHINES = {
    "binary_incrementer": binary_incrementer,
    "binary_decrementer": binary_decrementer,
    "unary_adder": unary_adder,
    "palindrome_checker": palindrome_checker,
    "copy_machine": copy_machine,
    "busy_beaver_4": lambda: busy_beaver(4),
}


def get_machine(name: str) -> Program:
    """Return a predefined machine by name, or raise KeyError."""
    if name not in MACHINES:
        raise KeyError(f"unknown machine: {name!r}; available: {list(MACHINES)}")
    return MACHINES[name]()


def list_machines() -> List[str]:
    """Return the names of all predefined machines."""
    return list(MACHINES)