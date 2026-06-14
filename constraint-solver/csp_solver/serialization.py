"""
Serialization and import/export utilities for CSP Solver.

Supports exporting CSP problems and solutions to JSON format,
and importing CSP definitions from JSON files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .csp import CSP, Variable, Constraint, Assignment


def export_csp(csp: CSP) -> Dict[str, Any]:
    """Export a CSP to a JSON-serializable dictionary.

    The exported format includes all variables, their domains,
    and constraint metadata. Note: constraint functions cannot
    be serialized, so they are stored as descriptive metadata.

    Args:
        csp: The CSP to export.

    Returns:
        Dictionary suitable for JSON serialization.
    """
    variables = {}
    for name, var in csp.variables.items():
        variables[name] = {
            "domain": sorted(var.domain),
            "initial_domain": sorted(var.initial_domain),
        }

    constraints = []
    for c in csp.constraints:
        entry: Dict[str, Any] = {
            "scope": list(c.scope),
            "arity": c.arity,
            "is_binary": c.is_binary(),
            "has_pair_check": c.pair_check is not None,
        }
        if c._name:
            entry["name"] = c._name
        constraints.append(entry)

    neighbors = {}
    for name in csp.variables:
        neighbor_set = csp.get_neighbors(name)
        if neighbor_set:
            neighbors[name] = sorted(neighbor_set)

    return {
        "variables": variables,
        "constraints": constraints,
        "neighbors": neighbors,
        "num_variables": len(csp.variables),
        "num_constraints": len(csp.constraints),
        "metadata": {
            "export_version": "2.0",
        },
    }


def export_solution(
    assignment: Assignment,
    stats: Optional[Any] = None,
    method: str = "",
    problem_type: str = "",
) -> Dict[str, Any]:
    """Export a solution to a JSON-serializable dictionary.

    Args:
        assignment: The solution assignment.
        stats: Optional SolverStats object.
        method: Solving method string.
        problem_type: Type of problem solved.

    Returns:
        Dictionary suitable for JSON serialization.
    """
    result: Dict[str, Any] = {
        "assignment": {k: v for k, v in sorted(assignment.items())},
        "num_variables": len(assignment),
        "method": method,
        "problem_type": problem_type,
    }

    if stats is not None:
        result["stats"] = stats.to_dict()

    return result


def save_csp(csp: CSP, path: Union[str, Path]) -> None:
    """Save a CSP definition to a JSON file.

    Args:
        csp: The CSP to save.
        path: File path for the JSON output.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = export_csp(csp)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def save_solution(
    assignment: Assignment,
    path: Union[str, Path],
    stats: Optional[Any] = None,
    method: str = "",
    problem_type: str = "",
) -> None:
    """Save a solution to a JSON file.

    Args:
        assignment: The solution assignment.
        path: File path for the JSON output.
        stats: Optional SolverStats object.
        method: Solving method string.
        problem_type: Type of problem solved.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = export_solution(assignment, stats, method, problem_type)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def import_csp(data: Dict[str, Any]) -> CSP:
    """Import a CSP from a JSON-compatible dictionary.

    This creates a CSP with variables and their domains from the
    exported format. Constraints with custom logic cannot be
    reconstructed from JSON, so only variable domains are restored.

    Args:
        data: Dictionary from export_csp or loaded from JSON.

    Returns:
        CSP with variables and domains restored.

    Raises:
        ValueError: If the data format is invalid.
    """
    if "variables" not in data:
        raise ValueError("Invalid CSP data: missing 'variables' key")

    csp = CSP()
    variables_data = data["variables"]

    for name, var_data in variables_data.items():
        if isinstance(var_data, dict):
            domain = set(var_data.get("domain", var_data.get("initial_domain", [])))
        elif isinstance(var_data, list):
            domain = set(var_data)
        else:
            raise ValueError(f"Invalid variable data for {name}: {var_data}")

        csp.add_variable(Variable(name, domain=domain))

    return csp


def load_csp(path: Union[str, Path]) -> CSP:
    """Load a CSP from a JSON file.

    Args:
        path: Path to the JSON file.

    Returns:
        CSP with variables and domains restored.
    """
    path = Path(path)
    with open(path, "r") as f:
        data = json.load(f)
    return import_csp(data)


def export_comparison_results(results: List[Dict]) -> Dict[str, Any]:
    """Export strategy comparison results to JSON-serializable format.

    Args:
        results: List of result dicts from compare_strategies.

    Returns:
        Dictionary suitable for JSON serialization.
    """
    return {
        "comparison_results": results,
        "num_strategies": len(results),
    }