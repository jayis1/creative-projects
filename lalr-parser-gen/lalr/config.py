"""Configuration management for the LALR parser generator.

Supports loading parser/lexer configuration from JSON or YAML files.

Example JSON config::

    {
        "grammar_file": "grammar.bnf",
        "lexer": {
            "skip": "[ \\t\\n]+",
            "tokens": [
                {"name": "NUMBER", "pattern": "\\d+", "action": "int"},
                {"name": "ID", "pattern": "[A-Za-z_][A-Za-z0-9_]*"},
                {"name": "PLUS", "pattern": "\\+"},
                {"name": "ASSIGN", "pattern": "="}
            ],
            "keywords": {
                "if": "IF",
                "else": "ELSE",
                "while": "WHILE"
            }
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
        "parser": {
            "debug": false,
            "error_recovery": true,
            "sync_tokens": [";", "}"]
        }
    }
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class LexerConfig:
    """Configuration for the lexer."""

    skip: Optional[str] = None
    tokens: List[Dict[str, Any]] = field(default_factory=list)
    keywords: Dict[str, str] = field(default_factory=dict)


@dataclass
class ParserConfig:
    """Configuration for the parser."""

    debug: bool = False
    error_recovery: bool = False
    sync_tokens: List[str] = field(default_factory=list)
    max_errors: int = 50


@dataclass
class LoggingConfig:
    """Configuration for logging."""

    level: str = "WARNING"
    format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    file: Optional[str] = None


@dataclass
class LALRConfig:
    """Top-level configuration for the LALR parser generator.

    Attributes:
        grammar_file: Path to the BNF grammar file.
        lexer: Lexer configuration.
        parser: Parser configuration.
        logging: Logging configuration.
    """

    grammar_file: Optional[str] = None
    lexer: LexerConfig = field(default_factory=LexerConfig)
    parser: ParserConfig = field(default_factory=ParserConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LALRConfig":
        """Create configuration from a dictionary."""
        lexer_data = data.get("lexer", {})
        parser_data = data.get("parser", {})
        logging_data = data.get("logging", {})

        return cls(
            grammar_file=data.get("grammar_file"),
            lexer=LexerConfig(
                skip=lexer_data.get("skip"),
                tokens=lexer_data.get("tokens", []),
                keywords=lexer_data.get("keywords", {}),
            ),
            parser=ParserConfig(
                debug=parser_data.get("debug", False),
                error_recovery=parser_data.get("error_recovery", False),
                sync_tokens=parser_data.get("sync_tokens", []),
                max_errors=parser_data.get("max_errors", 50),
            ),
            logging=LoggingConfig(
                level=logging_data.get("level", "WARNING"),
                format=logging_data.get(
                    "format",
                    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                ),
                file=logging_data.get("file"),
            ),
        )

    @classmethod
    def load(cls, path: str) -> "LALRConfig":
        """Load configuration from a JSON file.

        Args:
            path: Path to the JSON configuration file.

        Returns:
            A LALRConfig instance.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            ValueError: If the JSON is invalid.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path) as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in config file: {e}") from e

        config = cls.from_dict(data)

        # If grammar_file is relative, resolve relative to config file directory
        if config.grammar_file and not os.path.isabs(config.grammar_file):
            config_dir = os.path.dirname(os.path.abspath(path))
            config.grammar_file = os.path.join(config_dir, config.grammar_file)

        logger.info("Loaded configuration from %s", path)
        return config

    def apply_logging(self) -> None:
        """Apply the logging configuration."""
        level = getattr(logging, self.logging.level.upper(), logging.WARNING)
        handlers: List[logging.Handler] = []

        if self.logging.file:
            handlers.append(logging.FileHandler(self.logging.file))
        else:
            handlers.append(logging.StreamHandler())

        logging.basicConfig(
            level=level,
            format=self.logging.format,
            handlers=handlers,
            force=True,
        )
        logger.info("Logging configured at level %s", self.logging.level)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize config back to a dictionary."""
        return {
            "grammar_file": self.grammar_file,
            "lexer": {
                "skip": self.lexer.skip,
                "tokens": self.lexer.tokens,
                "keywords": self.lexer.keywords,
            },
            "parser": {
                "debug": self.parser.debug,
                "error_recovery": self.parser.error_recovery,
                "sync_tokens": self.parser.sync_tokens,
                "max_errors": self.parser.max_errors,
            },
            "logging": {
                "level": self.logging.level,
                "format": self.logging.format,
                "file": self.logging.file,
            },
        }

    def save(self, path: str) -> None:
        """Save configuration to a JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info("Saved configuration to %s", path)


def setup_logging(
    level: str = "WARNING",
    log_file: Optional[str] = None,
    fmt: Optional[str] = None,
) -> None:
    """Convenience function to set up logging.

    Args:
        level: Logging level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional file path for log output.
        fmt: Optional format string.
    """
    numeric_level = getattr(logging, level.upper(), logging.WARNING)
    fmt = fmt or "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    handlers: List[logging.Handler] = []
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    else:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=numeric_level,
        format=fmt,
        handlers=handlers,
        force=True,
    )