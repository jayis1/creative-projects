"""Tests for built-in machines."""

import pytest
from turing_machine.machine import TuringMachine, MultiTapeTM, TMDirection
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


class TestBinaryIncrementer:
    def _run(self, tape_str):
        prog = binary_incrementer()
        tm = TuringMachine(prog, initial_state="s0", tape=list(tape_str),
                           blank="_", halt_states={"halt"})
        tm.run()
        return "".join(str(c) for c in tm.tapes[0].to_list())

    def test_increment_1011(self):
        assert self._run("1011") == "1100"  # 11 + 1 = 12

    def test_increment_0(self):
        assert self._run("0") == "1"

    def test_increment_111(self):
        assert self._run("111") == "1000"  # 7 + 1 = 8

    def test_increment_empty(self):
        assert self._run("") == "1"

    def test_increment_all_ones(self):
        assert self._run("1") == "10"


class TestBinaryDecrementer:
    def _run(self, tape_str):
        prog = binary_decrementer()
        tm = TuringMachine(prog, initial_state="s0", tape=list(tape_str),
                           blank="_", halt_states={"halt"})
        tm.run()
        return "".join(str(c) for c in tm.tapes[0].to_list())

    def test_decrement_1100(self):
        assert self._run("1100") == "1011"  # 12 - 1 = 11

    def test_decrement_1(self):
        assert self._run("1") == "0"

    def test_decrement_10(self):
        # 10 (2) - 1 = 1, machine produces "01" (leading zero is expected)
        result = self._run("10")
        # Strip leading zeros for comparison
        stripped = result.lstrip("0") or "0"
        assert stripped == "1"  # 2 - 1 = 1


class TestUnaryAdder:
    def _run(self, tape):
        prog = unary_adder()
        tm = TuringMachine(prog, initial_state="s0", tape=tape,
                           blank="_", halt_states={"halt"})
        tm.run()
        return tm.tapes[0].to_list()

    def test_add_3_plus_2(self):
        result = self._run(["1", "1", "1", "_", "1", "1"])
        ones = sum(1 for c in result if c == "1")
        assert ones == 5

    def test_add_1_plus_1(self):
        result = self._run(["1", "_", "1"])
        ones = sum(1 for c in result if c == "1")
        assert ones == 2


class TestPalindromeChecker:
    def _run(self, tape_str):
        prog = palindrome_checker()
        tm = TuringMachine(prog, initial_state="s0", tape=list(tape_str),
                           blank="_", halt_states={"halt", "accept", "reject"})
        return tm.run()

    def test_palindrome_101(self):
        assert self._run("101") == "accept"

    def test_palindrome_1001(self):
        assert self._run("1001") == "accept"

    def test_not_palindrome_100(self):
        assert self._run("100") == "reject"

    def test_single_char_is_palindrome(self):
        assert self._run("1") == "accept"

    def test_empty_is_palindrome(self):
        assert self._run("") == "accept"

    def test_palindrome_11(self):
        assert self._run("11") == "accept"


class TestCopyMachine:
    def _run(self, tape_str):
        prog = copy_machine()
        tm = TuringMachine(prog, initial_state="s0", tape=list(tape_str),
                           blank="_", halt_states={"halt"})
        tm.run()
        return tm.tapes[0].to_list()

    def test_copy_111(self):
        result = self._run("111")
        ones = sum(1 for c in result if c == "1")
        assert ones == 6  # 3 original + 3 copy

    def test_copy_1(self):
        result = self._run("1")
        ones = sum(1 for c in result if c == "1")
        assert ones == 2


class TestBusyBeaver:
    def test_bb4_halts(self):
        prog = busy_beaver(4)
        tm = TuringMachine(prog, initial_state="A", blank="0",
                           halt_states={"HALT", "halt"})
        tm.run()
        assert tm.halted
        assert tm.steps == 107

    def test_bb4_ones_count(self):
        prog = busy_beaver(4)
        tm = TuringMachine(prog, initial_state="A", blank="0",
                           halt_states={"HALT", "halt"})
        tm.run()
        ones = sum(1 for c in tm.tapes[0].to_list(strip_blanks=False) if c == "1")
        assert ones == 13

    def test_bb2(self):
        prog = busy_beaver(2)
        tm = TuringMachine(prog, initial_state="A", blank="0",
                           halt_states={"HALT", "halt"})
        tm.run()
        assert tm.halted

    def test_bb_invalid(self):
        with pytest.raises(ValueError):
            busy_beaver(5)


class TestTwoTapeAdder:
    def test_add_101_plus_11(self):
        prog = two_tape_adder()
        tm = MultiTapeTM(prog, initial_state="scan",
                         tapes=[["1", "0", "1"], ["1", "1"]],
                         blank="_", halt_states={"halt"}, num_tapes=2)
        tm.run()
        result = "".join(str(c) for c in tm.tapes[0].to_list())
        # 101 (5) + 11 (3) = 8 = 1000
        assert result == "1000"

    def test_add_zeros(self):
        prog = two_tape_adder()
        tm = MultiTapeTM(prog, initial_state="scan",
                         tapes=[["0"], ["0"]],
                         blank="_", halt_states={"halt"}, num_tapes=2)
        tm.run()
        result = "".join(str(c) for c in tm.tapes[0].to_list())
        assert result == "0"


class TestTagSystem:
    def test_basic_tag_system(self):
        ts = TagSystem({"a": "bc", "b": "a", "c": "aaa"}, m=2)
        ts.initialize(["a", "a", "a"])
        ts.run()
        assert ts.halted

    def test_tag_system_history(self):
        ts = TagSystem({"a": "aa", "b": "a"}, m=2)
        ts.initialize(["a", "a", "a", "a"])
        ts.run(record=True)
        # History should have initial + steps
        assert len(ts.history) >= 1

    def test_tag_system_halts_on_short_tape(self):
        ts = TagSystem({"a": "aa"}, m=2)
        ts.initialize(["a"])  # too short
        ts.run()
        assert ts.halted


class TestMachineRegistry:
    def test_list_machines(self):
        names = list_machines()
        assert "binary_incrementer" in names
        assert "palindrome_checker" in names

    def test_get_machine(self):
        prog = get_machine("binary_incrementer")
        assert prog is not None
        assert len(prog) > 0

    def test_get_unknown_machine(self):
        with pytest.raises(KeyError):
            get_machine("nonexistent_machine")