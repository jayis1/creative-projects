r"""typeinfer — Hindley-Milner type inference for a small lambda calculus."""

from .types import (
    TVar, TCon, TFun, Scheme,
    type_to_string, scheme_to_string,
)
from .lexer import tokenize, Token, LexerError
from .parser import parse, ParserError
from .unify import unify, UnificationError, occurs, apply_subst, compose_subst
from .inference import (
    infer, infer_with_trace, InferContext, InferError,
)
from .primitives import primitives_env, default_env, list_env, maybe_env

__all__ = [
    "TVar", "TCon", "TFun", "Scheme",
    "type_to_string", "scheme_to_string",
    "tokenize", "Token", "LexerError",
    "parse", "ParserError",
    "unify", "UnificationError", "occurs", "apply_subst", "compose_subst",
    "infer", "infer_with_trace", "InferContext", "InferError",
    "primitives_env", "default_env", "list_env", "maybe_env",
]