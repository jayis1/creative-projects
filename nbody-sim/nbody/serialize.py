"""JSON serialization for simulation snapshots and full runs.

Format
------
A snapshot file is a JSON object::

    {
      "step": 200,
      "t": 2.0,
      "bodies": [{"x":.., "y":.., "vx":.., "vy":.., "m":.., "name":..}, ...],
      "energy": -1.287,
      "momentum": [0.0, 0.0]
    }

A run file is a JSON object::

    {
      "config": {"dt":.., "theta":.., "softening":.., "G":..},
      "snapshots": [ <snapshot>, ... ],
      "initial_energy": ..., "final_energy": ...,
      "initial_momentum": [...], "final_momentum": [...]
    }
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from .body import Body
from .simulation import Simulation, SimulationResult, Snapshot


def body_to_dict(b: Body) -> Dict[str, Any]:
    return {"x": b.x, "y": b.y, "vx": b.vx, "vy": b.vy, "m": b.m, "name": b.name}


def body_from_dict(d: Dict[str, Any]) -> Body:
    return Body(
        x=float(d["x"]), y=float(d["y"]),
        vx=float(d.get("vx", 0.0)), vy=float(d.get("vy", 0.0)),
        m=float(d.get("m", 1.0)),
        name=str(d.get("name", "")),
    )


def snapshot_to_dict(s: Snapshot) -> Dict[str, Any]:
    return {
        "step": s.step,
        "t": s.t,
        "bodies": [body_to_dict(b) for b in s.bodies],
        "energy": s.energy,
        "momentum": list(s.momentum),
    }


def snapshot_from_dict(d: Dict[str, Any]) -> Snapshot:
    return Snapshot(
        step=int(d["step"]),
        t=float(d["t"]),
        bodies=[body_from_dict(b) for b in d["bodies"]],
        energy=float(d["energy"]),
        momentum=tuple(d["momentum"]),
    )


def result_to_dict(result: SimulationResult, sim: Simulation) -> Dict[str, Any]:
    return {
        "config": {
            "dt": sim.dt, "theta": sim.theta,
            "softening": sim.softening, "G": sim.G,
        },
        "snapshots": [snapshot_to_dict(s) for s in result.snapshots],
        "initial_energy": result.initial_energy,
        "final_energy": result.final_energy,
        "initial_momentum": list(result.initial_momentum),
        "final_momentum": list(result.final_momentum),
        "n_steps": result.n_steps,
    }


def save_snapshot(s: Snapshot, path: str) -> None:
    with open(path, "w") as f:
        json.dump(snapshot_to_dict(s), f, indent=2)


def load_snapshot(path: str) -> Snapshot:
    with open(path) as f:
        return snapshot_from_dict(json.load(f))


def save_result(result: SimulationResult, sim: Simulation, path: str) -> None:
    with open(path, "w") as f:
        json.dump(result_to_dict(result, sim), f, indent=2)


__all__ = [
    "body_to_dict", "body_from_dict",
    "snapshot_to_dict", "snapshot_from_dict",
    "result_to_dict",
    "save_snapshot", "load_snapshot", "save_result",
]