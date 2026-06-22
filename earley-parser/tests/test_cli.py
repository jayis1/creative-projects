"""Tests for the CLI interface."""
import pytest
import subprocess
import sys
import os
from earley_parser.cli import main


@pytest.fixture
def expr_bnf(tmp_path):
    p = tmp_path / "expr.bnf"
    p.write_text("""# Expression grammar
start ::= <E>

<E> ::= <E> "+" <E>
      | <E> "*" <E>
      | "(" <E> ")"
      | "id"
""")
    return str(p)


@pytest.fixture
def balance_bnf(tmp_path):
    p = tmp_path / "balance.bnf"
    p.write_text("""start ::= <S>

<S> ::= "(" <S> ")"
      | <S> <S>
      |
""")
    return str(p)


class TestCLI:
    def test_demo(self, capsys):
        ret = main(["demo"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "Recognition Demo" in out
        assert "Parse Tree" in out

    def test_recognize_accept(self, capsys, expr_bnf):
        ret = main(["recognize", "--grammar", expr_bnf, "id", "+", "id"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "✓" in out or "Accepted" in out

    def test_recognize_reject(self, capsys, expr_bnf):
        ret = main(["recognize", "--grammar", expr_bnf, "id", "+"])
        assert ret == 1
        out = capsys.readouterr().out
        assert "✗" in out or "error" in out.lower()

    def test_recognize_no_input(self, capsys, expr_bnf):
        ret = main(["recognize", "--grammar", expr_bnf])
        assert ret == 1

    def test_tree(self, capsys, expr_bnf):
        ret = main(["tree", "--grammar", expr_bnf, "--max", "3",
                     "id", "+", "id", "*", "id"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "Tree" in out
        assert "E" in out

    def test_forest_json(self, capsys, expr_bnf):
        ret = main(["forest", "--grammar", expr_bnf, "--format", "json",
                     "id"])
        assert ret == 0
        out = capsys.readouterr().out
        assert '"symbol"' in out

    def test_forest_dot(self, capsys, expr_bnf):
        ret = main(["forest", "--grammar", expr_bnf, "--format", "dot",
                     "id"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "digraph" in out

    def test_forest_lisp(self, capsys, expr_bnf):
        ret = main(["forest", "--grammar", expr_bnf, "--format", "lisp",
                     "id"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "(E" in out

    def test_check_valid(self, capsys, expr_bnf):
        ret = main(["check", expr_bnf])
        assert ret == 0
        out = capsys.readouterr().out
        assert "valid" in out.lower()

    def test_check_invalid(self, capsys, tmp_path):
        p = tmp_path / "bad.bnf"
        p.write_text('start ::= <S>\n<S> ::= <A>\n<A> ::= <B>\n<B> ::= <A>\n')
        ret = main(["check", str(p)])
        assert ret == 1

    def test_analyze(self, capsys, expr_bnf):
        ret = main(["analyze", expr_bnf])
        assert ret == 0
        out = capsys.readouterr().out
        assert "Grammar:" in out
        assert "LL(1):" in out

    def test_analyze_ambiguity(self, capsys, expr_bnf):
        ret = main(["analyze", "--ambiguity", "--max-length", "3", expr_bnf])
        assert ret == 0
        out = capsys.readouterr().out
        assert "Ambiguity" in out

    def test_ll1(self, capsys, expr_bnf):
        ret = main(["ll1", expr_bnf])
        # Ambiguous grammar => not LL(1) => ret 1
        assert ret == 1
        out = capsys.readouterr().out
        assert "LL(1):" in out

    def test_chart(self, capsys, expr_bnf):
        ret = main(["chart", "--grammar", expr_bnf, "id", "+", "id"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "Chart[0]" in out

    def test_cyk(self, capsys, tmp_path):
        p = tmp_path / "cnf.bnf"
        p.write_text("""start ::= <S>
<S> ::= <S> <A>
<S> ::= "a"
<A> ::= "b"
""")
        ret = main(["cyk", str(p), "a", "b"])
        assert ret == 0

    def test_config(self, capsys, tmp_path, expr_bnf):
        import json
        cfg = {"grammar_file": expr_bnf}
        p = tmp_path / "cfg.json"
        p.write_text(json.dumps(cfg))
        ret = main(["config", str(p), "id", "+", "id"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "Tree" in out