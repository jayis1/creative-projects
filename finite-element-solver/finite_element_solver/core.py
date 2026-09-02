"""Backward-compatible exports for the finite element solver package."""

from .model import (
    Element,
    ElementResult,
    LoadCase,
    LoadCombination,
    Material,
    Node,
    Section,
    SolveResult,
    Support,
    TrussModel,
    ValidationError,
)
from .reporting import build_envelope, summarize_model
from .solver import TrussSolver

__all__ = [
    "Element",
    "ElementResult",
    "LoadCase",
    "LoadCombination",
    "Material",
    "Node",
    "Section",
    "SolveResult",
    "Support",
    "TrussModel",
    "TrussSolver",
    "ValidationError",
    "build_envelope",
    "summarize_model",
]
