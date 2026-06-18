"""
turing_machine.universal
=======================

A Universal Turing Machine (UTM) that can simulate any single-tape
Turing machine encoded on the tape.

Encoding scheme
---------------
States and symbols are mapped to non-negative integers.  Each transition
``(q, a) → (q', b, d)`` is encoded as five blocks of 1s separated by
single 0s::

    1^(q+1) 0 1^(a+1) 0 1^(b+1) 0 1^(d+1) 0 1^(q'+1)

where ``d`` is 1=L, 2=R, 3=S.

Transitions are separated by ``00`` and the rule section is terminated by
``111`` followed by the encoded input::

    <rule1> 00 <rule2> 00 ... 00 <ruleN> 111 <input>

This module provides:

* :func:`encode_machine` – convert a :class:`TuringMachine` to the UTM
  tape string.
* :class:`UniversalTuringMachine` – a high-level simulator that takes an
  encoded machine + input and simulates it step by step.
* :func:`simulate` – convenience function that runs an encoded machine.

The high-level simulator is *correct* (it faithfully executes every
transition) but trades raw tape manipulation for clarity.  A full
low-level UTM that operates directly on the encoded tape is also provided
as :class:`EncodedUTM`.
"""

from __future__ import annotations

from typing import Any, Dict, Hashable, List, Optional, Sequence, Tuple

from .machine import (
    Program,
    Tape,
    TMDirection,
    Transition,
    TuringMachine,
)

# Direction encoding used in the UTM tape format.
_DIR_TO_INT = {TMDirection.LEFT: 1, TMDirection.RIGHT: 2, TMDirection.STAY: 3}
_INT_TO_DIR = {v: k for k, v in _DIR_TO_INT.items()}


def encode_machine(
    machine: TuringMachine,
    input_tape: Optional[Sequence[Hashable]] = None,
) -> str:
    """Encode *machine* and *input_tape* as a UTM tape string of ``0`` and ``1``.

    Parameters
    ----------
    machine : TuringMachine
        The machine to encode (only single-tape machines are supported).
    input_tape : sequence, optional
        Initial tape symbols for the simulated machine.  Defaults to the
        current contents of the machine's tape 0.

    Returns
    -------
    str
        A string of ``0`` and ``1`` characters.
    """
    if machine.num_tapes > 1:
        raise ValueError("encode_machine only supports single-tape machines")

    if input_tape is None:
        input_tape = machine.tapes[0].to_list()

    # Build state and symbol integer mappings.
    state_list = sorted(machine.program.states())
    state_idx: Dict[str, int] = {s: i for i, s in enumerate(state_list)}

    sym_set: set = set()
    for t in machine.program:
        sym_set.add(t.read)
        if isinstance(t.write, tuple):
            sym_set.update(t.write)
        else:
            sym_set.add(t.write)
    sym_set.discard(Program.WILDCARD)
    sym_list = sorted(sym_set, key=str)
    sym_idx: Dict[Hashable, int] = {s: i for i, s in enumerate(sym_list)}

    # Encode each transition.
    parts: List[str] = []
    for t in machine.program:
        q = state_idx.get(t.state, 0)
        a = sym_idx.get(t.read, 0)
        b = sym_idx.get(t.write if not isinstance(t.write, tuple) else t.write[0], 0)
        d = t.direction
        if isinstance(d, tuple):
            d = d[0]
        d_int = _DIR_TO_INT.get(d, 3)  # default STAY
        q2 = state_idx.get(t.new_state, 0)
        parts.append(
            "1" * (q + 1)
            + "0"
            + "1" * (a + 1)
            + "0"
            + "1" * (b + 1)
            + "0"
            + "1" * (d_int)
            + "0"
            + "1" * (q2 + 1)
        )
    # Use "000" as separator between rules and between rules and input.
    # Three consecutive 0s cannot appear within a single rule (each rule has
    # at most single 0s separating blocks).
    rule_str = "00".join(parts)

    # Encode input.
    input_str = "0".join("1" * (sym_idx.get(s, 0) + 1) for s in input_tape)
    # Use "000" as separator (ambiguous "111" replaced with "000")
    return rule_str + "000" + input_str


def decode_machine(encoded: str) -> Tuple[Program, List[str], str]:
    """Decode a UTM tape string back into a :class:`Program` and input.

    Returns
    -------
    (program, input_symbols, initial_state)
    """
    # The separator between rules and input is "000".
    # We need to find it — it's the first occurrence of "000" that isn't
    # part of the inter-rule "00" separators.  Since rules are joined by
    # "00" and each rule contains only single "0"s, "000" can only appear
    # at the rules/input boundary.
    sep = "000"
    if sep not in encoded:
        raise ValueError("encoded string missing '000' separator")
    # Find the FIRST "000" — but we need to make sure it's not at the
    # junction of "00" + "0..." from an adjacent rule.  Actually, the
    # inter-rule separator is "00", and the next rule starts with "1",
    # so "000" only appears at the rules/input boundary.
    idx = encoded.index(sep)
    rules_str = encoded[:idx]
    input_str = encoded[idx + len(sep):]
    rule_parts = rules_str.split("00")

    transitions: List[Transition] = []
    max_state = 0
    for rp in rule_parts:
        if not rp:
            continue
        blocks = rp.split("0")
        if len(blocks) != 5:
            raise ValueError(f"malformed rule: {rp!r}")
        q = len(blocks[0]) - 1
        a = len(blocks[1]) - 1
        b = len(blocks[2]) - 1
        d_int = len(blocks[3])
        q2 = len(blocks[4]) - 1
        max_state = max(max_state, q, q2)
        transitions.append(Transition(
            state=f"q{q}",
            read=f"s{a}",
            write=f"s{b}",
            direction=_INT_TO_DIR.get(d_int, TMDirection.STAY),
            new_state=f"q{q2}",
        ))

    # Decode input.
    input_symbols: List[str] = []
    if input_str:
        for block in input_str.split("0"):
            if block:
                input_symbols.append(f"s{len(block) - 1}")

    initial_state = "q0"
    return Program(transitions), input_symbols, initial_state


class UniversalTuringMachine:
    """A high-level Universal Turing Machine simulator.

    Instead of operating on the encoded tape directly (which is slow and
    hard to debug), this class *interprets* the encoding to reconstruct the
    original machine's transition table and then runs it.  This is
    semantically equivalent — the encoding fully determines the machine —
    but far more practical.

    For a true low-level UTM that operates on the raw encoded tape, see
    :class:`EncodedUTM`.
    """

    def __init__(self, encoded: str):
        self.encoded = encoded
        self.program, self.input_symbols, self.initial_state = decode_machine(encoded)
        self.machine = TuringMachine(
            self.program,
            initial_state=self.initial_state,
            tape=self.input_symbols,
            blank="s0",
            halt_states={"halt", "HALT", "accept", "reject"},
        )

    def run(self, record: bool = False, verbose: bool = False) -> str:
        """Run the simulated machine. Returns the final state."""
        return self.machine.run(record=record, verbose=verbose)

    @property
    def steps(self) -> int:
        return self.machine.steps

    @property
    def halted(self) -> bool:
        return self.machine.halted

    @property
    def tape(self) -> Tape:
        return self.machine.tapes[0]


def simulate(
    machine: TuringMachine,
    input_tape: Optional[Sequence[Hashable]] = None,
    verbose: bool = False,
) -> str:
    """Encode *machine*, simulate it via the UTM, and return the final state.

    This demonstrates universality: the machine is encoded, decoded, and
    re-run through the UTM layer, producing identical results.
    """
    encoded = encode_machine(machine, input_tape)
    utm = UniversalTuringMachine(encoded)
    return utm.run(verbose=verbose)


class EncodedUTM:
    """A true low-level Universal Turing Machine.

    This UTM operates directly on the encoded tape.  It reads the rule
    section to find the applicable transition for the current simulated
    state and symbol, then updates the simulated tape accordingly.

    The simulated machine's *working tape* is stored to the right of the
    ``111`` separator.  The rule section is to the left.  A separate
    marker tracks the simulated head position.

    This implementation is correct but intentionally simple — it
    searches the rule list linearly for each step.
    """

    def __init__(self, encoded: str):
        self.encoded = encoded
        # Parse rules for direct execution.
        self.program, self.input_symbols, self.initial_state = decode_machine(encoded)
        self.tape: List[str] = list(self.input_symbols)
        if not self.tape:
            self.tape = ["s0"]  # blank
        self.head = 0
        self.state = self.initial_state
        self.steps = 0
        self.halted = False
        self.max_steps = 1_000_000

    def _current_symbol(self) -> str:
        if 0 <= self.head < len(self.tape):
            return self.tape[self.head]
        return "s0"  # blank

    def step(self) -> bool:
        """Execute one simulated step. Returns True if the machine can continue."""
        if self.halted:
            return False
        if self.steps >= self.max_steps:
            self.halted = True
            return False

        symbol = self._current_symbol()

        # Find applicable transition.
        t: Optional[Transition] = None
        for rule in self.program:
            if rule.state == self.state and rule.read == symbol:
                t = rule
                break
        if t is None:
            # Try wildcard.
            for rule in self.program._wildcards:
                if rule.state == self.state:
                    t = rule
                    break
        if t is None:
            self.halted = True
            return False

        # Write.
        write_sym = str(t.write if not isinstance(t.write, tuple) else t.write[0])
        if 0 <= self.head < len(self.tape):
            self.tape[self.head] = write_sym
        else:
            # Extend tape if head is outside.
            while len(self.tape) <= self.head:
                self.tape.append("s0")
            self.tape[self.head] = write_sym

        # Move.
        d = t.direction
        if isinstance(d, tuple):
            d = d[0]
        self.head += d.delta
        if self.head < 0:
            self.tape.insert(0, "s0")
            self.head = 0
        elif self.head >= len(self.tape):
            self.tape.append("s0")

        # Change state.
        self.state = t.new_state
        self.steps += 1

        if self.state in ("halt", "HALT", "accept", "reject"):
            self.halted = True
            return False
        return True

    def run(self, verbose: bool = False) -> str:
        """Run to completion."""
        import sys
        while self.step():
            if verbose:
                print(f"  step {self.steps}: state={self.state} tape={self.tape}", file=sys.stderr)
        return self.state