"""
JSON serialization / deserialization for persistence diagrams and results.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from .diagram import PersistenceDiagram


def diagrams_to_json(diagrams: Dict[int, PersistenceDiagram]) -> str:
    """Serialize a dict of persistence diagrams to a JSON string."""
    data: Dict[str, Any] = {
        "diagrams": [
            diagrams[dim].to_dict() for dim in sorted(diagrams)
        ]
    }
    return json.dumps(data, indent=2)


def diagrams_from_json(s: str) -> Dict[int, PersistenceDiagram]:
    """Deserialize JSON string back to a dict of persistence diagrams."""
    data = json.loads(s)
    result: Dict[int, PersistenceDiagram] = {}
    for d in data["diagrams"]:
        diag = PersistenceDiagram.from_dict(d)
        result[diag.dimension] = diag
    return result


def save_diagrams(diagrams: Dict[int, PersistenceDiagram], path: str) -> None:
    """Save diagrams to a JSON file."""
    with open(path, "w") as f:
        f.write(diagrams_to_json(diagrams))


def load_diagrams(path: str) -> Dict[int, PersistenceDiagram]:
    """Load diagrams from a JSON file."""
    with open(path) as f:
        return diagrams_from_json(f.read())