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
    ConflictResolution – agenda strategy enum
    EngineListener  – protocol for event observers

Serialization
-------------
    load_json       – load rules/facts from JSON
    load_yaml        – load rules/facts from YAML (requires PyYAML)
    load_file        – auto-detect format from extension
    load_engine      – load file → return configured Engine
    save_facts       – save working memory to JSON
    save_facts_yaml  – save working memory to YAML
    save_state       – save full engine state to JSON
"""

from .engine import (
    Engine,
    Fact,
    Rule,
    Condition,
    Var,
    Const,
    ConflictResolution,
    EngineListener,
    AlphaNode,
    BetaMemory,
    JoinNode,
    ProductionNode,
    DummyBeta,
)
from .exceptions import (
    ReteError,
    RuleError,
    FactError,
    MatchError,
    InfiniteLoopError,
    SerializationError,
)
from .serialization import (
    load_json,
    load_yaml,
    load_file,
    load_engine,
    save_facts,
    save_facts_yaml,
    save_state,
)

__all__ = [
    # Core
    "Engine",
    "Fact",
    "Rule",
    "Condition",
    "Var",
    "Const",
    "ConflictResolution",
    "EngineListener",
    # Network nodes
    "AlphaNode",
    "BetaMemory",
    "JoinNode",
    "ProductionNode",
    "DummyBeta",
    # Exceptions
    "ReteError",
    "RuleError",
    "FactError",
    "MatchError",
    "InfiniteLoopError",
    "SerializationError",
    # Serialization
    "load_json",
    "load_yaml",
    "load_file",
    "load_engine",
    "save_facts",
    "save_facts_yaml",
    "save_state",
]

__version__ = "3.0.0"