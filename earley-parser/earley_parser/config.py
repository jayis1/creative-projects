"""Configuration management for earley-parser.

Supports JSON, YAML, and TOML configuration files for:
- Grammar definitions (inline or file reference)
- Tokenizer specifications
- Parser options (max_trees, error handling mode)
- Logging configuration

Example config file (JSON):

.. code-block:: json

    {
        "grammar": "examples/expr.bnf",
        "tokenizer": [
            {"name": "NUM", "pattern": "[0-9]+"},
            {"name": "PLUS", "pattern": "\\\\+"},
            {"name": "WS", "pattern": "\\\\s+", "skip": true}
        ],
        "parser": {
            "max_trees": 50,
            "algorithm": "earley"
        },
        "logging": {
            "level": "INFO"
        }
    }
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from .tokenizer import TokenSpec
from .grammar import Grammar, GrammarLoader
from .errors import EarleyError


@dataclass
class ParserConfig:
    """Configuration for the earley-parser.

    Attributes
    ----------
    grammar_file : str
        Path to a BNF grammar file.
    grammar_text : str
        Inline BNF grammar text (used if grammar_file is None).
    tokenizer_specs : list[dict]
        List of token spec dicts with keys: name, pattern, skip.
    max_trees : int
        Maximum number of parse trees to extract.
    algorithm : str
        Parsing algorithm: ``"earley"`` or ``"cyk"``.
    log_level : str
        Logging level: ``"DEBUG"``, ``"INFO"``, ``"WARNING"``, ``"ERROR"``.
    """

    grammar_file: Optional[str] = None
    grammar_text: Optional[str] = None
    tokenizer_specs: List[Dict[str, Any]] = field(default_factory=list)
    max_trees: int = 50
    algorithm: str = "earley"
    log_level: str = "WARNING"

    def get_grammar(self) -> Grammar:
        """Load and return the :class:`Grammar` from this config."""
        if self.grammar_file:
            return GrammarLoader.load_file(self.grammar_file)
        if self.grammar_text:
            return GrammarLoader.load(self.grammar_text)
        raise EarleyError("No grammar specified in config.")

    def get_token_specs(self) -> List[TokenSpec]:
        """Build :class:`TokenSpec` objects from this config."""
        return [
            TokenSpec(
                name=spec["name"],
                pattern=spec["pattern"],
                skip=spec.get("skip", False),
            )
            for spec in self.tokenizer_specs
        ]

    def setup_logging(self) -> None:
        """Configure logging based on this config."""
        level = getattr(logging, self.log_level.upper(), logging.WARNING)
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParserConfig":
        """Build a :class:`ParserConfig` from a dictionary."""
        return cls(
            grammar_file=data.get("grammar_file") or data.get("grammar"),
            grammar_text=data.get("grammar_text"),
            tokenizer_specs=data.get("tokenizer", []),
            max_trees=data.get("parser", {}).get("max_trees", 50),
            algorithm=data.get("parser", {}).get("algorithm", "earley"),
            log_level=data.get("logging", {}).get("level", "WARNING"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a dictionary."""
        return {
            "grammar_file": self.grammar_file,
            "grammar_text": self.grammar_text,
            "tokenizer": self.tokenizer_specs,
            "parser": {
                "max_trees": self.max_trees,
                "algorithm": self.algorithm,
            },
            "logging": {"level": self.log_level},
        }


def load_config(path: str) -> ParserConfig:
    """Load a :class:`ParserConfig` from a file.

    Supports ``.json``, ``.yaml``/``.yml``, and ``.toml`` formats.
    The format is determined by the file extension.
    """
    ext = os.path.splitext(path)[1].lower()
    with open(path, "r") as f:
        text = f.read()

    if ext == ".json":
        data = json.loads(text)
    elif ext in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError:
            raise EarleyError(
                "YAML config requires PyYAML: pip install pyyaml"
            )
        data = yaml.safe_load(text)
    elif ext == ".toml":
        if hasattr(__import__("sys"), "version_info") and \
                __import__("sys").version_info >= (3, 11):
            import tomllib
            data = tomllib.loads(text)
        else:
            try:
                import tomllib
                data = tomllib.loads(text)
            except ImportError:
                try:
                    import tomli
                    data = tomli.loads(text)
                except ImportError:
                    raise EarleyError(
                        "TOML config requires Python 3.11+ or tomli: "
                        "pip install tomli"
                    )
    else:
        # Default to JSON
        data = json.loads(text)

    # If grammar_file is specified, resolve relative to config dir
    config_dir = os.path.dirname(os.path.abspath(path))
    grammar_file = data.get("grammar_file") or data.get("grammar")
    if grammar_file and not os.path.isabs(grammar_file):
        resolved = os.path.join(config_dir, grammar_file)
        if os.path.exists(resolved):
            data["grammar_file"] = resolved
        else:
            data["grammar_file"] = grammar_file

    return ParserConfig.from_dict(data)


def save_config(config: ParserConfig, path: str) -> None:
    """Save a :class:`ParserConfig` to a file (JSON format)."""
    ext = os.path.splitext(path)[1].lower()
    data = config.to_dict()
    if ext == ".json":
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    elif ext in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError:
            raise EarleyError("YAML output requires PyYAML.")
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
    else:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)