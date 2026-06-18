"""Tests for the definition language parser."""

import pytest
from turing_machine.machine import TMDirection
from turing_machine.def_parser import parse, parse_file, Parser, ParseError, MachineDef


class TestParser:
    def test_parse_directives(self):
        text = """
        blank: _
        start: s0
        halt: halt accept reject
        """
        md = parse(text)
        assert md.blank == "_"
        assert md.start_state == "s0"
        assert "halt" in md.halt_states
        assert "accept" in md.halt_states
        assert "reject" in md.halt_states

    def test_parse_transition(self):
        text = """
        start: s0
        halt: halt
        s0 1 -> 0 R s1
        """
        md = parse(text)
        assert len(md.transitions) == 1
        t = md.transitions[0]
        assert t.state == "s0"
        assert t.read == "1"
        assert t.write == "0"
        assert t.direction == TMDirection.RIGHT
        assert t.new_state == "s1"

    def test_parse_comments(self):
        text = """
        # This is a comment
        start: s0
        halt: halt
        # Another comment
        s0 1 -> 0 R s1  # inline comment
        """
        md = parse(text)
        assert len(md.transitions) == 1

    def test_parse_inline_comment(self):
        text = "s0 1 -> 0 R s1  # do something"
        md = parse(text)
        assert len(md.transitions) == 1
        assert md.transitions[0].new_state == "s1"

    def test_parse_multi_tape_directive(self):
        text = """
        tapes: 2
        start: q0
        halt: halt
        q0 (0 _) -> (1 0) (R S) q1
        """
        md = parse(text)
        assert md.num_tapes == 2
        assert len(md.transitions) == 1
        t = md.transitions[0]
        assert isinstance(t.read, tuple)
        assert t.read == ("0", "_")
        assert isinstance(t.write, tuple)
        assert isinstance(t.direction, tuple)

    def test_parse_error_missing_arrow(self):
        with pytest.raises(ParseError):
            parse("s0 1 0 R s1")

    def test_parse_error_bad_directive(self):
        # Not a directive, not a transition
        with pytest.raises(ParseError):
            parse("garbage line here")

    def test_parse_quoted_symbol(self):
        text = """
        start: s0
        halt: halt
        s0 'a' -> 'b' R s1
        """
        md = parse(text)
        assert md.transitions[0].read == "a"
        assert md.transitions[0].write == "b"

    def test_machine_def_to_program(self):
        md = MachineDef()
        md.transitions.append(
            __import__('turing_machine').machine.Transition("s0", "1", "0", "R", "s1")
        )
        prog = md.to_program()
        assert len(prog) == 1

    def test_machine_def_to_machine(self):
        text = """
        start: s0
        halt: halt
        blank: _
        s0 1 -> 0 R halt
        """
        md = parse(text)
        tm = md.to_machine(tape=["1"])
        tm.run()
        assert tm.state == "halt"

    def test_parse_file(self, tmp_path):
        text = """
        start: s0
        halt: halt
        s0 1 -> 0 R halt
        """
        f = tmp_path / "test.tm"
        f.write_text(text)
        md = parse_file(str(f))
        assert md.start_state == "s0"
        assert len(md.transitions) == 1

    def test_parse_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_file("nonexistent.tm")

    def test_comma_separated_halt(self):
        text = """
        halt: halt, accept, reject
        """
        md = parse(text)
        assert "halt" in md.halt_states
        assert "accept" in md.halt_states
        assert "reject" in md.halt_states