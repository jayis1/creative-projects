from __future__ import annotations

import json
from pathlib import Path

from .generator import CityMap


def load_city(path: Path) -> CityMap:
    """Load a city snapshot from JSON."""

    return CityMap.from_dict(json.loads(path.read_text()))


def write_text_output(payload: str, output: Path | None) -> None:
    if output is None:
        print(payload)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload)
