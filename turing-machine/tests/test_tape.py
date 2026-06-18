"""Tests for the core Tape class."""

import pytest
from turing_machine.machine import Tape, TMDirection


class TestTapeBasics:
    def test_empty_tape_has_one_cell(self):
        t = Tape("_")
        assert len(t) == 1
        assert t.read() == "_"

    def test_tape_with_initial_content(self):
        t = Tape("_", ["1", "0", "1"])
        assert len(t) == 3
        assert t.read() == "1"

    def test_write_and_read(self):
        t = Tape("_", ["0"])
        t.write("1")
        assert t.read() == "1"

    def test_move_right(self):
        t = Tape("_", ["1", "0", "1"])
        t.move(TMDirection.RIGHT)
        assert t.read() == "0"

    def test_move_left(self):
        t = Tape("_", ["1", "0", "1"])
        t.move(TMDirection.RIGHT)
        t.move(TMDirection.LEFT)
        assert t.read() == "1"

    def test_move_stay(self):
        t = Tape("_", ["1", "0"])
        t.move(TMDirection.STAY)
        assert t.read() == "1"

    def test_move_past_right_end_grows(self):
        t = Tape("_", ["1"])
        t.move(TMDirection.RIGHT)
        assert t.read() == "_"
        assert len(t) == 2

    def test_move_past_left_end_grows(self):
        t = Tape("_", ["1"])
        t.move(TMDirection.LEFT)
        assert t.read() == "_"
        assert len(t) == 2

    def test_to_list_strips_blanks(self):
        t = Tape("_", ["1", "0", "_", "_"])
        result = t.to_list()
        assert result == ["1", "0"]

    def test_to_list_no_strip(self):
        t = Tape("_", ["1", "0", "_"])
        result = t.to_list(strip_blanks=False)
        assert result == ["1", "0", "_"]

    def test_to_list_empty_returns_blank(self):
        t = Tape("_")
        result = t.to_list()
        assert result == ["_"]

    def test_copy(self):
        t = Tape("_", ["1", "0", "1"])
        t.move(TMDirection.RIGHT)
        c = t.copy()
        assert c.read() == "0"
        c.write("X")
        assert t.read() == "0"  # original unchanged

    def test_render(self):
        t = Tape("_", ["1", "0", "1"])
        s = t.render()
        assert "1" in s
        assert "^" in s

    def test_head_property(self):
        t = Tape("_", ["1", "0", "1"])
        assert t.head == 0
        t.move(TMDirection.RIGHT)
        assert t.head == 1

    def test_head_setter(self):
        t = Tape("_", ["1", "0", "1"])
        t.head = 2
        assert t.read() == "1"

    def test_getitem(self):
        t = Tape("_", ["1", "0", "1"])
        assert t[0] == "1"
        assert t[1] == "0"
        assert t[10] == "_"  # out of bounds returns blank

    def test_setitem(self):
        t = Tape("_", ["1", "0", "1"])
        t[1] = "X"
        assert t[1] == "X"

    def test_iter(self):
        t = Tape("_", ["1", "0", "1"])
        assert list(t) == ["1", "0", "1"]


class TestTMDirection:
    def test_parse_string(self):
        assert TMDirection.parse("L") == TMDirection.LEFT
        assert TMDirection.parse("R") == TMDirection.RIGHT
        assert TMDirection.parse("S") == TMDirection.STAY

    def test_parse_case_insensitive(self):
        assert TMDirection.parse("l") == TMDirection.LEFT
        assert TMDirection.parse("right") == TMDirection.RIGHT

    def test_parse_int(self):
        assert TMDirection.parse(-1) == TMDirection.LEFT
        assert TMDirection.parse(1) == TMDirection.RIGHT
        assert TMDirection.parse(0) == TMDirection.STAY

    def test_parse_invalid(self):
        with pytest.raises(ValueError):
            TMDirection.parse("invalid")

    def test_delta(self):
        assert TMDirection.LEFT.delta == -1
        assert TMDirection.RIGHT.delta == 1
        assert TMDirection.STAY.delta == 0