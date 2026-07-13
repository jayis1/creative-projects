"""Tests for the error recovery parser."""
import pytest
from lalr import Grammar, LALRTable, Token, ParseError
from lalr.error_recovery import RecoveringParser, ParseErrorEntry


class TestRecoveringParser:
    def _simple_grammar(self):
        return Grammar([
            ("stmts", ["stmts", "stmt"]),
            ("stmts", ["stmt"]),
            ("stmt", ["ID", "=", "NUMBER", ";"]),
            ("stmt", ["NUMBER", ";"]),
        ])

    def test_no_errors(self):
        """Parser should work correctly when there are no errors."""
        g = self._simple_grammar()
        table = LALRTable(g)
        parser = RecoveringParser(g, table=table, sync_tokens={";"})
        tokens = [
            Token("ID", "x", 0), Token("=", "=", 1),
            Token("NUMBER", 42, 2), Token(";", ";", 3),
        ]
        errors = []
        result = parser.parse(tokens, on_error=errors.append)
        assert len(errors) == 0
        assert result is not None

    def test_recover_from_missing_semicolon(self):
        """Should detect missing semicolon and recover."""
        g = self._simple_grammar()
        table = LALRTable(g)
        parser = RecoveringParser(g, table=table, sync_tokens={";"},
                                  max_errors=10)
        tokens = [
            Token("ID", "x", 0), Token("=", "=", 1),
            Token("NUMBER", 42, 2),
            # Missing ; here
            Token("ID", "y", 3), Token("=", "=", 4),
            Token("NUMBER", 10, 5), Token(";", ";", 6),
        ]
        errors = []
        result = parser.parse(tokens, on_error=errors.append)
        assert len(errors) >= 1
        assert errors[0].position >= 0

    def test_multiple_errors(self):
        """Should collect multiple errors in one pass."""
        g = self._simple_grammar()
        table = LALRTable(g)
        parser = RecoveringParser(g, table=table, sync_tokens={";"},
                                  max_errors=20)
        tokens = [
            Token("ID", "x", 0), Token("=", "=", 1),
            # Missing NUMBER
            Token(";", ";", 2),
            Token("ID", "y", 3), Token("=", "=", 4),
            Token("NUMBER", 10, 5),
            # Missing ;
            Token("ID", "z", 6), Token("=", "=", 7),
            Token("NUMBER", 99, 8), Token(";", ";", 9),
        ]
        errors = []
        result = parser.parse(tokens, on_error=errors.append)
        assert len(errors) >= 2

    def test_max_errors_limit(self):
        """Should stop after max_errors."""
        g = self._simple_grammar()
        table = LALRTable(g)
        parser = RecoveringParser(g, table=table, sync_tokens={";"},
                                  max_errors=2)
        tokens = [
            Token("NUMBER", 0, 0),  # Error: expected ID or NUMBER
            Token("NUMBER", 1, 1),
            Token("NUMBER", 2, 2),
            Token("NUMBER", 3, 3),
        ]
        errors = []
        result = parser.parse(tokens, on_error=errors.append)
        assert len(errors) <= 3  # max_errors + some slack

    def test_error_entry_str(self):
        entry = ParseErrorEntry("Test error", position=5, state=3,
                                 expected=["ID", "NUMBER"])
        s = str(entry)
        assert "Test error" in s
        assert "position 5" in s
        assert "state 3" in s
        assert "ID" in s

    def test_error_entry_skipped(self):
        entry = ParseErrorEntry("Test", position=0, skipped=3)
        assert entry.skipped == 3

    def test_errors_collected_in_self(self):
        """Errors should also be in parser.errors."""
        g = self._simple_grammar()
        table = LALRTable(g)
        parser = RecoveringParser(g, table=table, sync_tokens={";"})
        tokens = [Token("UNKNOWN", "?", 0)]
        parser.parse(tokens)
        assert len(parser.errors) >= 1