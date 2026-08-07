"""
Serialization for boolean functions and minimization results.

Provides JSON import/export for:

* :class:`BooleanFunction` — minterms, dontcares, n_vars, name.
* :class:`MinimizationResult` — full result with primes, essentials, SOP.
* :class:`POSResult` — POS minimization result.
* :class:`MultiOutputResult` — multi-output result.

Also provides a ``serialize`` / ``deserialize`` generic dispatcher.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Sequence, Union

from .boolean import BooleanFunction, Implicant, var_names
from .quine_mccluskey import MinimizationResult
from .pos import POSResult
from .multi_output import MultiOutputResult, SharedImplicant


# ---------------------------------------------------------------------------
# BooleanFunction
# ---------------------------------------------------------------------------

def function_to_dict(func: BooleanFunction) -> Dict[str, Any]:
    """Serialize a :class:`BooleanFunction` to a dict."""
    return {
        "type": "BooleanFunction",
        "n_vars": func.n_vars,
        "minterms": sorted(func.minterms),
        "dontcare": sorted(func.dontcare),
        "name": func.name,
    }


def function_from_dict(d: Dict[str, Any]) -> BooleanFunction:
    """Deserialize a :class:`BooleanFunction` from a dict."""
    return BooleanFunction(
        n_vars=d["n_vars"],
        minterms=d.get("minterms", []),
        dontcare=d.get("dontcare", []),
        name=d.get("name", "f"),
    )


def function_to_json(func: BooleanFunction) -> str:
    """Serialize a :class:`BooleanFunction` to JSON."""
    return json.dumps(function_to_dict(func), indent=2)


def function_from_json(text: str) -> BooleanFunction:
    """Deserialize a :class:`BooleanFunction` from JSON."""
    return function_from_dict(json.loads(text))


# ---------------------------------------------------------------------------
# MinimizationResult
# ---------------------------------------------------------------------------

def result_to_dict(result: MinimizationResult) -> Dict[str, Any]:
    """Serialize a :class:`MinimizationResult` to a dict."""
    names = result.function.var_names
    return {
        "type": "MinimizationResult",
        "method": result.method,
        "sop": result.sop,
        "n_terms": result.n_terms,
        "n_literals": result.n_literals,
        "sop_cubes": result.sop_cubes,
        "minterms_covered": result.minterms_covered,
        "iterations": result.iterations,
        "prime_implicants": [
            {
                "cube": p.cube,
                "sop_term": p.sop_term(names),
                "n_literals": p.n_literals,
            }
            for p in result.prime_implicants
        ],
        "essential_implicants": [
            {
                "cube": p.cube,
                "sop_term": p.sop_term(names),
                "n_literals": p.n_literals,
            }
            for p in result.essential_implicants
        ],
        "function": function_to_dict(result.function),
    }


def result_to_json(result: MinimizationResult) -> str:
    """Serialize a :class:`MinimizationResult` to JSON."""
    return json.dumps(result_to_dict(result), indent=2)


# ---------------------------------------------------------------------------
# POSResult
# ---------------------------------------------------------------------------

def pos_result_to_dict(result: POSResult) -> Dict[str, Any]:
    """Serialize a :class:`POSResult` to a dict."""
    return {
        "type": "POSResult",
        "method": result.method,
        "pos": result.pos,
        "pos_clauses": result.pos_clauses,
        "n_clauses": result.n_clauses,
        "n_literals": result.n_literals,
        "dual_sop": result.dual_sop,
        "function": function_to_dict(result.function),
    }


def pos_result_to_json(result: POSResult) -> str:
    """Serialize a :class:`POSResult` to JSON."""
    return json.dumps(pos_result_to_dict(result), indent=2)


# ---------------------------------------------------------------------------
# MultiOutputResult
# ---------------------------------------------------------------------------

def multi_result_to_dict(result: MultiOutputResult) -> Dict[str, Any]:
    """Serialize a :class:`MultiOutputResult` to a dict."""
    names = var_names(result.functions[0].n_vars) if result.functions else []
    return {
        "type": "MultiOutputResult",
        "method": result.method,
        "n_outputs": len(result.functions),
        "total_terms": result.total_terms,
        "total_literals": result.total_literals,
        "sop": result.sop,
        "functions": [function_to_dict(f) for f in result.functions],
        "shared_implicants": [
            {
                "cube": s.cube,
                "sop_term": s.implicant.sop_term(names),
                "outputs": sorted(s.outputs),
            }
            for s in result.shared_implicants
        ],
    }


def multi_result_to_json(result: MultiOutputResult) -> str:
    """Serialize a :class:`MultiOutputResult` to JSON."""
    return json.dumps(multi_result_to_dict(result), indent=2)


# ---------------------------------------------------------------------------
# Generic dispatcher
# ---------------------------------------------------------------------------

def serialize(obj: Union[BooleanFunction, MinimizationResult, POSResult, MultiOutputResult]) -> str:
    """Serialize any supported result/function to JSON.

    The object type is auto-detected.
    """
    if isinstance(obj, BooleanFunction):
        return function_to_json(obj)
    if isinstance(obj, MinimizationResult):
        return result_to_json(obj)
    if isinstance(obj, POSResult):
        return pos_result_to_json(obj)
    if isinstance(obj, MultiOutputResult):
        return multi_result_to_json(obj)
    raise TypeError(f"unsupported type for serialization: {type(obj).__name__}")


def deserialize_function(text: str) -> BooleanFunction:
    """Deserialize a :class:`BooleanFunction` from JSON."""
    return function_from_json(text)


# ---------------------------------------------------------------------------
# Save/load to file
# ---------------------------------------------------------------------------

def save_function(func: BooleanFunction, path: str) -> None:
    """Save a :class:`BooleanFunction` to a JSON file."""
    with open(path, "w") as fh:
        fh.write(function_to_json(func))


def load_function(path: str) -> BooleanFunction:
    """Load a :class:`BooleanFunction` from a JSON file."""
    with open(path) as fh:
        return function_from_json(fh.read())


def save_result(result: MinimizationResult, path: str) -> None:
    """Save a :class:`MinimizationResult` to a JSON file."""
    with open(path, "w") as fh:
        fh.write(result_to_json(result))


def save_multi_result(result: MultiOutputResult, path: str) -> None:
    """Save a :class:`MultiOutputResult` to a JSON file."""
    with open(path, "w") as fh:
        fh.write(multi_result_to_json(result))