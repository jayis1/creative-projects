"""Tests for Transition and Program classes."""

import pytest
from turing_machine.machine import Transition, TMDirection, Program


class TestTransition:
    def test_basic_transition(self):
        t = Transition("s0", "1", "0", "R", "s1")
        assert t.state == "s0"
        assert t.read == "1"
        assert t.write == "0"
        assert t.direction == TMDirection.RIGHT
        assert t.new_state == "s1"

    def test_default_new_state(self):
        t = Transition("s0", "1", "0", "R")
        assert t.new_state == "s0"  # defaults to current state

    def test_direction_normalization(self):
        t = Transition("s0", "1", "0", "L", "s1")
        assert t.direction == TMDirection.LEFT

    def test_tuple_direction(self):
        t = Transition("s0", ("1", "0"), ("0", "1"), ("L", "R"), "s1")
        assert isinstance(t.direction, tuple)
        assert t.direction[0] == TMDirection.LEFT
        assert t.direction[1] == TMDirection.RIGHT

    def test_applies_to(self):
        t = Transition("s0", "1", "0", "R", "s1")
        assert t.applies_to("s0", "1")
        assert not t.applies_to("s0", "0")
        assert not t.applies_to("s1", "1")


class TestProgram:
    def test_add_and_lookup(self):
        prog = Program()
        prog.add(Transition("s0", "1", "0", "R", "s1"))
        t = prog.lookup("s0", "1")
        assert t is not None
        assert t.new_state == "s1"

    def test_lookup_missing(self):
        prog = Program()
        prog.add(Transition("s0", "1", "0", "R", "s1"))
        assert prog.lookup("s0", "0") is None
        assert prog.lookup("s1", "1") is None

    def test_wildcard(self):
        prog = Program()
        prog.add(Transition("s0", "*", "X", "R", "s1"))
        t = prog.lookup("s0", "0")
        assert t is not None
        assert t.write == "X"
        t2 = prog.lookup("s0", "1")
        assert t2 is not None

    def test_wildcard_does_not_override_specific(self):
        prog = Program()
        prog.add(Transition("s0", "1", "A", "R", "s1"))
        prog.add(Transition("s0", "*", "X", "R", "s1"))
        t = prog.lookup("s0", "1")
        assert t.write == "A"
        t2 = prog.lookup("s0", "0")
        assert t2.write == "X"

    def test_len(self):
        prog = Program([
            Transition("s0", "0", "0", "R", "s0"),
            Transition("s0", "1", "1", "R", "s0"),
        ])
        assert len(prog) == 2

    def test_states(self):
        prog = Program([
            Transition("s0", "0", "0", "R", "s1"),
            Transition("s1", "1", "1", "L", "halt"),
        ])
        states = prog.states()
        assert "s0" in states
        assert "s1" in states
        assert "halt" in states

    def test_symbols(self):
        prog = Program([
            Transition("s0", "0", "1", "R", "s1"),
            Transition("s1", "1", "0", "L", "halt"),
        ])
        syms = prog.symbols()
        assert "0" in syms
        assert "1" in syms

    def test_contains(self):
        prog = Program([Transition("s0", "1", "0", "R", "s1")])
        assert ("s0", "1") in prog
        assert ("s0", "0") not in prog

    def test_copy(self):
        prog = Program([Transition("s0", "1", "0", "R", "s1")])
        prog2 = prog.copy()
        assert len(prog2) == 1
        prog2.add(Transition("s1", "0", "1", "L", "s0"))
        assert len(prog2) == 2
        assert len(prog) == 1  # original unchanged