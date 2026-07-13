"""Tests for the visualization module."""
import pytest
from lalr import Grammar, LALRTable
from lalr.visualize import automaton_to_dot, table_to_html, conflict_report


class TestAutomatonToDot:
    def test_basic_dot_output(self):
        g = Grammar([("S", ["a"])])
        table = LALRTable(g)
        dot = automaton_to_dot(table)
        assert "digraph" in dot
        assert "S0" in dot

    def test_with_title(self):
        g = Grammar([("S", ["a"])])
        table = LALRTable(g)
        dot = automaton_to_dot(table, title="Test Grammar")
        assert "Test Grammar" in dot

    def test_horizontal_layout(self):
        g = Grammar([("S", ["a", "b"])])
        table = LALRTable(g)
        dot = automaton_to_dot(table, horizontal=True)
        assert "rankdir=LR" in dot

    def test_show_lookaheads(self):
        g = Grammar([
            ("expr", ["expr", "+", "term"]),
            ("expr", ["term"]),
            ("term", ["NUMBER"]),
        ])
        table = LALRTable(g)
        dot = automaton_to_dot(table, show_lookaheads=True)
        assert "digraph" in dot

    def test_transitions_in_output(self):
        g = Grammar([("S", ["a", "S"]), ("S", ["a"])])
        table = LALRTable(g)
        dot = automaton_to_dot(table)
        assert "->" in dot

    def test_accept_state_styled(self):
        g = Grammar([("S", ["a"])])
        table = LALRTable(g)
        dot = automaton_to_dot(table)
        assert "doubleoctagon" in dot


class TestTableToHTML:
    def test_basic_html(self):
        g = Grammar([("S", ["a"])])
        table = LALRTable(g)
        html = table_to_html(table)
        assert "<table" in html
        assert "</table>" in html

    def test_html_contains_terminals(self):
        g = Grammar([("S", ["a", "b"])])
        table = LALRTable(g)
        html = table_to_html(table)
        assert "a" in html
        assert "b" in html

    def test_html_contains_state_numbers(self):
        g = Grammar([("S", ["a"])])
        table = LALRTable(g)
        html = table_to_html(table)
        assert "0" in html


class TestConflictReport:
    def test_no_conflicts(self):
        g = Grammar([("S", ["a"])])
        table = LALRTable(g)
        report = conflict_report(table)
        assert "No conflicts" in report

    def test_with_conflicts(self):
        g = Grammar([
            ("S", ["S", "S"]),
            ("S", ["a"]),
        ])
        table = LALRTable(g)
        report = conflict_report(table)
        assert "Unresolved" in report

    def test_resolved_conflicts(self):
        from lalr import load_bnf_full
        text = """
        %start expr
        %left '+'
        %left '*'
        expr : expr '+' expr
             | expr '*' expr
             | NUMBER
             ;
        """
        g, prec = load_bnf_full(text)
        table = LALRTable(g, precedence=prec)
        report = conflict_report(table)
        assert "Resolved" in report