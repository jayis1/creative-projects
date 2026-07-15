"""
Rete Network — A forward-chaining rule inference engine.

This package implements the classic Rete algorithm (Rete I) for efficient
pattern matching over a working memory of facts.  Rules are defined as
IF <conditions> THEN <actions> and the engine fires them in a data-driven
forward-chaining loop.

Public API
----------
    Fact            – a working-memory element (attribute-value record)
    Rule            – a production rule (conditions + actions)
    Engine          – the Rete inference engine
    Condition       – a single pattern / test on a fact
    Var, Const      – helpers for building conditions
"""

from .engine import Engine, Fact, Rule, Condition, Var, Const, ConflictResolution
from .exceptions import ReteError

__all__ = [
    "Engine",
    "Fact",
    "Rule",
    "Condition",
    "Var",
    "Const",
    "ConflictResolution",
    "ReteError",
]

__version__ = "1.0.0"