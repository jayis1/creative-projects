"""Tests for the Tokenizer and Token classes."""
import pytest
from earley_parser import Tokenizer, TokenSpec, Token, TokenizerError


class TestTokenizer:
    def test_basic_tokenize(self):
        tok = Tokenizer([
            TokenSpec("NUM", r"[0-9]+"),
            TokenSpec("PLUS", r"\+"),
            TokenSpec("WS", r"\s+", skip=True),
        ])
        assert tok.tokenize("12 + 34") == ["NUM", "PLUS", "NUM"]

    def test_tokenize_with_text(self):
        tok = Tokenizer([
            TokenSpec("NUM", r"[0-9]+"),
            TokenSpec("PLUS", r"\+"),
            TokenSpec("WS", r"\s+", skip=True),
        ])
        result = tok.tokenize_with_text("12 + 34")
        assert result == [("NUM", "12"), ("PLUS", "+"), ("NUM", "34")]

    def test_tokenize_full(self):
        tok = Tokenizer([
            TokenSpec("NUM", r"[0-9]+"),
            TokenSpec("WS", r"\s+", skip=True),
        ])
        tokens = tok.tokenize_full("42 99")
        assert len(tokens) == 2
        assert isinstance(tokens[0], Token)
        assert tokens[0].name == "NUM"
        assert tokens[0].value == "42"
        assert tokens[0].position == 0
        assert tokens[1].position == 3

    def test_tokenizer_error(self):
        tok = Tokenizer([TokenSpec("NUM", r"[0-9]+")])
        with pytest.raises(TokenizerError):
            tok.tokenize("12abc")

    def test_zero_length_match_no_hang(self):
        """Regex like [0-9]* should not cause an infinite loop."""
        tok = Tokenizer([
            TokenSpec("NUM", r"[0-9]*"),
            TokenSpec("PLUS", r"\+"),
        ])
        try:
            tok.tokenize("a+")
        except TokenizerError:
            pass  # Acceptable: raises error on unmatched input

    def test_numbers_work(self):
        tok = Tokenizer([
            TokenSpec("NUM", r"[0-9]+"),
            TokenSpec("PLUS", r"\+"),
        ])
        assert tok.tokenize("12+34") == ["NUM", "PLUS", "NUM"]

    def test_skip_whitespace(self):
        tok = Tokenizer([
            TokenSpec("NUM", r"[0-9]+"),
            TokenSpec("WS", r"\s+", skip=True),
        ])
        assert tok.tokenize("  42  ") == ["NUM"]

    def test_unmatched_fallback_whitespace(self):
        """If no spec matches, fall back to skipping whitespace."""
        tok = Tokenizer([TokenSpec("NUM", r"[0-9]+")])
        # Whitespace between numbers should be skipped as fallback
        assert tok.tokenize("12 34") == ["NUM", "NUM"]

    def test_order_priority(self):
        """First matching spec wins."""
        tok = Tokenizer([
            TokenSpec("IF", r"if"),
            TokenSpec("ID", r"[a-z]+"),
        ])
        tokens = tok.tokenize("if id")
        assert tokens == ["IF", "ID"]

    def test_empty_input(self):
        tok = Tokenizer([TokenSpec("NUM", r"[0-9]+")])
        assert tok.tokenize("") == []

    def test_from_spec_pairs(self):
        tok = Tokenizer.from_spec_pairs(
            [("NUM", r"[0-9]+"), ("WS", r"\s+")],
            skip_names={"WS"},
        )
        assert tok.tokenize("12 34") == ["NUM", "NUM"]

    def test_empty_specs_raises(self):
        with pytest.raises(ValueError):
            Tokenizer([])

    def test_token_repr(self):
        t = Token("NUM", "42", 0)
        assert "NUM" in repr(t)
        assert "42" in repr(t)

    def test_token_str(self):
        t = Token("NUM", "42", 0)
        assert "NUM" in str(t)
        assert "42" in str(t)

    def test_complex_expression(self):
        tok = Tokenizer([
            TokenSpec("NUM", r"[0-9]+"),
            TokenSpec("PLUS", r"\+"),
            TokenSpec("STAR", r"\*"),
            TokenSpec("LPAREN", r"\("),
            TokenSpec("RPAREN", r"\)"),
            TokenSpec("WS", r"\s+", skip=True),
        ])
        tokens = tok.tokenize("3 + 4 * (2 + 1)")
        assert tokens == [
            "NUM", "PLUS", "NUM", "STAR",
            "LPAREN", "NUM", "PLUS", "NUM", "RPAREN",
        ]

    def test_id_keyword(self):
        tok = Tokenizer([
            TokenSpec("IF", r"if"),
            TokenSpec("WHILE", r"while"),
            TokenSpec("ID", r"[a-zA-Z_][a-zA-Z0-9_]*"),
            TokenSpec("WS", r"\s+", skip=True),
        ])
        tokens = tok.tokenize("if while x foo_bar")
        assert tokens == ["IF", "WHILE", "ID", "ID"]