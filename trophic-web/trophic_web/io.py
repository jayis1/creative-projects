"""JSON model loading and trajectory export helpers."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Iterable

from .model import Web


def load_web(path: str | Path) -> tuple[Web, tuple[float, ...]]:
    """Read a JSON model containing names, growth, interactions, and initial."""
    try:
        with Path(path).open("r", encoding="utf-8") as stream:
            data = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read model JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("model JSON must be an object")
    try:
        names = data["names"]
        growth = data["growth"]
        interactions = data["interactions"]
        initial = data["initial"]
    except KeyError as exc:
        raise ValueError(f"missing model field: {exc.args[0]}") from exc
    if not isinstance(names, list) or any(not isinstance(name, str) or not name for name in names):
        raise ValueError("names must be a list of non-empty strings")
    try:
        web = Web(tuple(names), tuple(float(x) for x in growth),
                  tuple(tuple(float(x) for x in row) for row in interactions))
        state = tuple(float(x) for x in initial)
    except (TypeError, ValueError) as exc:
        raise ValueError("growth, interactions, and initial must be numeric lists") from exc
    web.validate()
    if len(state) != len(names) or any(not math.isfinite(x) or x < 0 for x in state):
        raise ValueError("initial must contain one finite nonnegative abundance per species")
    return web, state


def write_csv(path: str | Path, web: Web, states: Iterable[tuple[float, ...]], dt: float) -> None:
    """Write a complete trajectory; validate the interval and row dimensions."""
    if not math.isfinite(dt) or dt <= 0:
        raise ValueError("dt must be positive and finite")
    target = Path(path)
    with target.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("time", *web.names))
        for index, state in enumerate(states):
            if len(state) != len(web.names) or any(not math.isfinite(x) for x in state):
                raise ValueError("trajectory row has invalid dimensions or values")
            writer.writerow((f"{index * dt:.9g}", *(f"{x:.9g}" for x in state)))
