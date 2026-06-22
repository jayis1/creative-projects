"""Tests for configuration management."""
import json
import pytest
import tempfile
import os
from earley_parser import ParserConfig, load_config, save_config


class TestParserConfig:
    def test_default_config(self):
        cfg = ParserConfig()
        assert cfg.max_trees == 50
        assert cfg.algorithm == "earley"
        assert cfg.log_level == "WARNING"

    def test_from_dict(self):
        data = {
            "grammar_file": "test.bnf",
            "tokenizer": [
                {"name": "NUM", "pattern": "[0-9]+"},
                {"name": "WS", "pattern": r"\s+", "skip": True},
            ],
            "parser": {"max_trees": 100, "algorithm": "earley"},
            "logging": {"level": "DEBUG"},
        }
        cfg = ParserConfig.from_dict(data)
        assert cfg.grammar_file == "test.bnf"
        assert cfg.max_trees == 100
        assert cfg.algorithm == "earley"
        assert cfg.log_level == "DEBUG"
        assert len(cfg.tokenizer_specs) == 2

    def test_to_dict(self):
        cfg = ParserConfig(
            grammar_file="test.bnf",
            max_trees=25,
            algorithm="cyk",
        )
        d = cfg.to_dict()
        assert d["grammar_file"] == "test.bnf"
        assert d["parser"]["max_trees"] == 25
        assert d["parser"]["algorithm"] == "cyk"

    def test_to_dict_roundtrip(self):
        cfg = ParserConfig(
            grammar_file="test.bnf",
            max_trees=25,
            tokenizer_specs=[{"name": "NUM", "pattern": "[0-9]+"}],
        )
        d = cfg.to_dict()
        cfg2 = ParserConfig.from_dict(d)
        assert cfg2.grammar_file == cfg.grammar_file
        assert cfg2.max_trees == cfg.max_trees

    def test_get_token_specs(self):
        cfg = ParserConfig(
            tokenizer_specs=[
                {"name": "NUM", "pattern": "[0-9]+"},
                {"name": "WS", "pattern": r"\s+", "skip": True},
            ],
        )
        specs = cfg.get_token_specs()
        assert len(specs) == 2
        assert specs[0].name == "NUM"
        assert specs[1].skip is True

    def test_get_grammar_no_spec_raises(self):
        from earley_parser import EarleyError
        cfg = ParserConfig()
        with pytest.raises(EarleyError):
            cfg.get_grammar()

    def test_get_grammar_from_text(self):
        cfg = ParserConfig(
            grammar_text='start ::= <E>\n<E> ::= "a"\n'
        )
        g = cfg.get_grammar()
        assert g.start == "E"

    def test_setup_logging(self):
        cfg = ParserConfig(log_level="ERROR")
        cfg.setup_logging()
        # No assertion needed — just shouldn't crash


class TestLoadSaveConfig:
    def test_load_json_config(self, tmp_path):
        config_data = {
            "grammar_file": "expr.bnf",
            "tokenizer": [
                {"name": "NUM", "pattern": "[0-9]+"},
            ],
            "parser": {"max_trees": 10},
        }
        p = tmp_path / "config.json"
        p.write_text(json.dumps(config_data))
        cfg = load_config(str(p))
        assert cfg.max_trees == 10
        assert len(cfg.tokenizer_specs) == 1

    def test_save_json_config(self, tmp_path):
        cfg = ParserConfig(
            grammar_file="test.bnf",
            max_trees=42,
        )
        p = tmp_path / "output.json"
        save_config(cfg, str(p))
        cfg2 = load_config(str(p))
        assert cfg2.grammar_file == "test.bnf"
        assert cfg2.max_trees == 42

    def test_relative_grammar_path_resolution(self, tmp_path):
        """Grammar file paths should be resolved relative to the config dir."""
        # Create a grammar file
        grammar_path = tmp_path / "grammar.bnf"
        grammar_path.write_text('start ::= <E>\n<E> ::= "a"\n')
        config_data = {
            "grammar_file": "grammar.bnf",
        }
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config_data))
        cfg = load_config(str(config_path))
        assert os.path.isabs(cfg.grammar_file) or os.path.exists(cfg.grammar_file)