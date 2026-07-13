"""Tests for the configuration module."""
import pytest
import json
import os
import tempfile
from lalr.config import LALRConfig, LexerConfig, ParserConfig, LoggingConfig, setup_logging


class TestLALRConfig:
    def test_from_dict(self):
        data = {
            "grammar_file": "grammar.bnf",
            "lexer": {
                "skip": r"\s+",
                "tokens": [{"name": "NUMBER", "pattern": r"\d+"}],
                "keywords": {"if": "IF"},
            },
            "parser": {
                "debug": True,
                "error_recovery": True,
                "sync_tokens": [";"],
                "max_errors": 30,
            },
            "logging": {
                "level": "DEBUG",
            }
        }
        config = LALRConfig.from_dict(data)
        assert config.grammar_file == "grammar.bnf"
        assert config.lexer.skip == r"\s+"
        assert len(config.lexer.tokens) == 1
        assert config.parser.debug is True
        assert config.parser.error_recovery is True
        assert config.parser.max_errors == 30
        assert config.logging.level == "DEBUG"

    def test_defaults(self):
        config = LALRConfig()
        assert config.grammar_file is None
        assert config.parser.debug is False
        assert config.parser.max_errors == 50
        assert config.logging.level == "WARNING"

    def test_load_from_file(self):
        data = {
            "grammar_file": "grammar.bnf",
            "parser": {"debug": True},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                         delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            config = LALRConfig.load(path)
            assert config.grammar_file is not None
            assert "grammar.bnf" in config.grammar_file
            assert config.parser.debug is True
        finally:
            os.unlink(path)

    def test_load_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            LALRConfig.load("/nonexistent/path.json")

    def test_to_dict_roundtrip(self):
        config = LALRConfig(
            grammar_file="test.bnf",
            parser=ParserConfig(debug=True, max_errors=25),
        )
        d = config.to_dict()
        assert d["grammar_file"] == "test.bnf"
        assert d["parser"]["debug"] is True
        assert d["parser"]["max_errors"] == 25
        # Roundtrip
        config2 = LALRConfig.from_dict(d)
        assert config2.grammar_file == "test.bnf"
        assert config2.parser.debug is True

    def test_save(self):
        config = LALRConfig(grammar_file="test.bnf")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                         delete=False) as f:
            path = f.name
        try:
            config.save(path)
            with open(path) as f:
                data = json.load(f)
            assert data["grammar_file"] == "test.bnf"
        finally:
            os.unlink(path)

    def test_relative_grammar_path(self):
        """Relative grammar_file should be resolved relative to config dir."""
        data = {"grammar_file": "grammar.bnf"}
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            with open(config_path, "w") as f:
                json.dump(data, f)
            config = LALRConfig.load(config_path)
            # Should resolve relative to tmpdir
            assert os.path.dirname(config.grammar_file) == tmpdir


class TestSetupLogging:
    def test_setup_logging(self):
        setup_logging("DEBUG")
        import logging
        assert logging.getLogger().level == logging.DEBUG

    def test_setup_logging_warning(self):
        setup_logging("WARNING")
        import logging
        assert logging.getLogger().level == logging.WARNING