r"""typeinfer — Hindley-Milner type inference for a small lambda calculus.

Public API:
    infer(source, *, env=None, use_builtins=False, data_types=None) -> Type
    infer_with_trace(source, ...) -> (Type, List[str])
    type_to_string(t) -> str
    scheme_to_string(sc) -> str
    parse(source) -> AST
    tokenize(source) -> List[Token]

Type constructors: TVar, TCon, TFun, Scheme
Built-in types: INT, BOOL, STRING, UNIT
Unification: unify, apply_subst, compose_subst, occurs
Errors: InferError, ParserError, LexerError, UnificationError
Primitive environments: primitives_env, default_env, list_env, maybe_env,
    either_env, string_env, pair_env, io_env

Configuration:
    load_config(path) -> Config
    save_config(path, config) -> None
    default_config() -> Config
"""

from .types import (
    TVar, TCon, TFun, Scheme,
    INT, BOOL, STRING, UNIT,
    type_to_string, scheme_to_string, resolve_type, TypeError_,
)
from .lexer import tokenize, Token, LexerError
from .parser import (
    parse, ParserError,
    EInt, EBool, EString, EVar, ELam, EApp, ELet, ELetMulti, EIf, ETuple,
    EList, EMatch, EDataDecl,
    PVar, PConstr, PInt, PString, PWild, PTuple,
)
from .unify import (
    unify, UnificationError, occurs, apply_subst, compose_subst,
)
from .inference import (
    infer, infer_with_trace, InferContext, InferError,
)
from .config import (
    Config, load_config, save_config, default_config, ConfigError,
)
from .primitives import (
    primitives_env, default_env, list_env, maybe_env,
    either_env, string_env, pair_env, io_env,
)

__version__ = "2.0.0"

__all__ = [
    # Types
    "TVar", "TCon", "TFun", "Scheme",
    "INT", "BOOL", "STRING", "UNIT",
    "type_to_string", "scheme_to_string", "resolve_type", "TypeError_",
    # Lexer
    "tokenize", "Token", "LexerError",
    # Parser
    "parse", "ParserError",
    "EInt", "EBool", "EString", "EVar", "ELam", "EApp", "ELet", "ELetMulti",
    "EIf", "ETuple", "EList", "EMatch", "EDataDecl",
    "PVar", "PConstr", "PInt", "PString", "PWild", "PTuple",
    # Unification
    "unify", "UnificationError", "occurs", "apply_subst", "compose_subst",
    # Inference
    "infer", "infer_with_trace", "InferContext", "InferError",
    # Config
    "Config", "load_config", "save_config", "default_config", "ConfigError",
    # Primitives
    "primitives_env", "default_env", "list_env", "maybe_env",
    "either_env", "string_env", "pair_env", "io_env",
    # Version
    "__version__",
]