"""Shared type aliases used across the Datalog engine modules."""

from __future__ import annotations

from typing import Dict, Set, Tuple

from .ast import Constant

# A binding maps variable name → Constant value.
Binding = Dict[str, Constant]

# A relation is a set of tuples, each tuple being a tuple of Constants.
Relation = Set[Tuple[Constant, ...]]