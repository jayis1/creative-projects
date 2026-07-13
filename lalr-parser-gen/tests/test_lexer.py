"""Tests for the configurable Lexer framework."""
import pytest
from lalr.lexer import Lexer, TokenSpec, LexError, LexerBuilder


class TestLexer:
    def test_basic_lexing(self):
        lexer = Lexer()
        lexer.add_spec(TokenSpec("NUMBER", r"\d+", action=int))
        lexer.add_spec(TokenSpec("PLUS", r"\+"))
        lexer.set_skip(r"\s+")
        tokens = lexer.lex("42 + 7")
        assert len(tokens) == 3
        assert tokens[0].type == "NUMBER"
        assert tokens[0].value == 42
        assert tokens[1].type == "PLUS"
        assert tokens[2].value == 7

    def test_longest_match(self):
        """Longer match should win over shorter."""
        lexer = Lexer()
        lexer.add_spec(TokenSpec("IF", r"if", priority=10))
        lexer.add_spec(TokenSpec("ID", r"[A-Za-z_][A-Za-z0-9_]*"))
        lexer.set_skip(r"\s+")
        tokens = lexer.lex("if ifelse")
        assert tokens[0].type == "IF"
        assert tokens[1].type == "ID"
        assert tokens[1].value == "ifelse"

    def test_priority_breaks_ties(self):
        """Same length, higher priority wins."""
        lexer = Lexer()
        lexer.add_spec(TokenSpec("KEYWORD", r"if", priority=10))
        lexer.add_spec(TokenSpec("ID", r"[A-Za-z_]+", priority=0))
        lexer.set_skip(r"\s+")
        tokens = lexer.lex("if")
        assert tokens[0].type == "KEYWORD"

    def test_hidden_tokens(self):
        """Hidden tokens are produced but not returned."""
        lexer = Lexer()
        lexer.add_spec(TokenSpec("WS", r"\s+", hidden=True))
        lexer.add_spec(TokenSpec("NUMBER", r"\d+", action=int))
        tokens = lexer.lex("42  3")
        assert len(tokens) == 2

    def test_lex_error(self):
        lexer = Lexer()
        lexer.add_spec(TokenSpec("NUMBER", r"\d+"))
        with pytest.raises(LexError):
            lexer.lex("abc")

    def test_no_specs_error(self):
        lexer = Lexer()
        with pytest.raises(LexError):
            lexer.lex("test")

    def test_line_column_tracking(self):
        lexer = Lexer()
        lexer.add_spec(TokenSpec("NUMBER", r"\d+"))
        lexer.set_skip(r"\s+")
        tokens = lexer.lex("42\n  7")
        assert hasattr(tokens[1], "line")
        assert tokens[1].line == 2
        assert tokens[1].column == 3

    def test_lex_stream(self):
        lexer = Lexer()
        lexer.add_spec(TokenSpec("NUMBER", r"\d+"))
        lexer.set_skip(r"\s+")
        tokens = list(lexer.lex_stream("1 2 3"))
        assert len(tokens) == 3
        assert [t.value for t in tokens] == ["1", "2", "3"]

    def test_add_keyword(self):
        lexer = Lexer()
        lexer.add_keyword("if", "IF", priority=20)
        lexer.add_spec(TokenSpec("ID", r"[A-Za-z_]+"))
        lexer.set_skip(r"\s+")
        tokens = lexer.lex("if foo")
        assert tokens[0].type == "IF"
        assert tokens[1].type == "ID"

    def test_add_symbol(self):
        lexer = Lexer()
        lexer.add_symbol("+", "PLUS")
        lexer.add_symbol("->", "ARROW")
        tokens = lexer.lex("->+")
        assert tokens[0].type == "ARROW"
        assert tokens[1].type == "PLUS"

    def test_action_callback(self):
        def my_action(s):
            return s.upper()
        lexer = Lexer()
        lexer.add_spec(TokenSpec("WORD", r"[a-z]+", action=my_action))
        tokens = lexer.lex("hello")
        assert tokens[0].value == "HELLO"

    def test_lex_empty_string(self):
        lexer = Lexer()
        lexer.add_spec(TokenSpec("X", r"x"))
        tokens = lexer.lex("")
        assert tokens == []

    def test_multichar_tokens(self):
        lexer = Lexer()
        lexer.add_spec(TokenSpec("EQ", r"=="))
        lexer.add_spec(TokenSpec("ASSIGN", r"="))
        lexer.add_spec(TokenSpec("ID", r"[A-Za-z_]+"))
        lexer.set_skip(r"\s+")
        tokens = lexer.lex("x == y")
        assert tokens[1].type == "EQ"


class TestLexerBuilder:
    def test_build_from_config(self):
        config = {
            "skip": r"\s+",
            "tokens": [
                {"name": "NUMBER", "pattern": r"\d+", "action": "int"},
                {"name": "PLUS", "pattern": r"\+", "priority": 5},
                {"name": "ID", "pattern": r"[A-Za-z_]+"},
            ],
            "keywords": {
                "if": "IF",
                "else": "ELSE",
            }
        }
        builder = LexerBuilder()
        lexer = builder.build(config)
        tokens = lexer.lex("if 42 + else")
        assert tokens[0].type == "IF"
        assert tokens[1].type == "NUMBER"
        assert tokens[1].value == 42
        assert tokens[3].type == "ELSE"