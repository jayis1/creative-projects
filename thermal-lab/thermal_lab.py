#!/usr/bin/env python3
"""Small, deterministic thermal RC network simulator for building zones."""
from __future__ import annotations
import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Zone:
    name: str
    capacity: float  # Wh/K
    outside_conductance: float  # W/K

@dataclass(frozen=True)
class Model:
    zones: tuple[Zone, ...]
    links: tuple[tuple[int, int, float], ...]  # zone indices and W/K

    @classmethod
    def from_dict(cls, data: dict) -> "Model":
        try:
            raw_zones = data["zones"]
            names = [z["name"] for z in raw_zones]
            if len(names) != len(set(names)) or not names:
                raise ValueError("zone names must be unique and non-empty")
            zones = tuple(Zone(str(z["name"]), _positive(z["capacity_wh_k"], "capacity_wh_k"), _nonnegative(z["outside_w_k"], "outside_w_k")) for z in raw_zones)
            index = {z.name: i for i, z in enumerate(zones)}
            links = []
            for link in data.get("links", []):
                a, b = index[link["a"]], index[link["b"]]
                if a == b: raise ValueError("a link must connect distinct zones")
                links.append((a, b, _nonnegative(link["w_k"], "link w_k")))
            return cls(zones, tuple(links))
        except (KeyError, TypeError, IndexError) as exc:
            raise ValueError(f"invalid model: {exc}") from exc

def _positive(value, field):
    value = float(value)
    if not math.isfinite(value) or value <= 0: raise ValueError(f"{field} must be finite and positive")
    return value

def _nonnegative(value, field):
    value = float(value)
    if not math.isfinite(value) or value < 0: raise ValueError(f"{field} must be finite and nonnegative")
    return value

def simulate(model: Model, initial: dict[str, float], outside_c: float, hours: float, step_hours: float, gains_w: dict[str, float] | None = None) -> list[dict[str, float]]:
    """Integrate temperatures by explicit Euler; returns initial and later hourly states."""
    if not math.isfinite(outside_c): raise ValueError("outside temperature must be finite")
    hours = _positive(hours, "hours"); step_hours = _positive(step_hours, "step_hours")
    if step_hours > hours: raise ValueError("step_hours cannot exceed hours")
    names = {z.name for z in model.zones}
    if set(initial) != names: raise ValueError("initial temperatures must specify every zone exactly once")
    gains_w = gains_w or {}
    if not set(gains_w) <= names: raise ValueError("heat gains refer to unknown zones")
    temps = [float(initial[z.name]) for z in model.zones]
    if any(not math.isfinite(t) for t in temps): raise ValueError("initial temperatures must be finite")
    if any(not math.isfinite(float(g)) for g in gains_w.values()): raise ValueError("heat gains must be finite")
    result = [{z.name: t for z, t in zip(model.zones, temps)}]
    elapsed = 0.0
    while elapsed < hours:
        dt = min(step_hours, hours - elapsed)
        delta = []
        for i, zone in enumerate(model.zones):
            power = zone.outside_conductance * (outside_c - temps[i]) + float(gains_w.get(zone.name, 0.0))
            for a, b, conductance in model.links:
                if i == a: power += conductance * (temps[b] - temps[i])
                elif i == b: power += conductance * (temps[a] - temps[i])
            delta.append(power * dt / zone.capacity)
        temps = [t + d for t, d in zip(temps, delta)]
        if any(not math.isfinite(t) for t in temps): raise ValueError("simulation became numerically unstable; reduce step_hours")
        elapsed += dt
        result.append({z.name: t for z, t in zip(model.zones, temps)})
    return result

def main(argv=None):
    parser = argparse.ArgumentParser(description="Simulate heat flow in a lumped building-zone network")
    parser.add_argument("model", type=Path, help="JSON model file")
    parser.add_argument("--outside", type=float, required=True, help="outside temperature in Celsius")
    parser.add_argument("--hours", type=float, default=8)
    parser.add_argument("--step", type=float, default=0.25, help="integration step in hours")
    parser.add_argument("--initial", type=float, default=20, help="uniform initial zone temperature")
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.model.read_text(encoding="utf-8"))
        model = Model.from_dict(data)
        history = simulate(model, {z.name: args.initial for z in model.zones}, args.outside, args.hours, args.step)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(history, indent=2))

if __name__ == "__main__": main()
