"""Built-in presets for Particle Life."""

from __future__ import annotations

from copy import deepcopy


_PRESETS = {
    "aurora": {
        "width": 120.0,
        "height": 80.0,
        "drag": 0.05,
        "force_scale": 42.0,
        "interaction_radius": 18.0,
        "repulsion_radius": 3.0,
        "max_speed": 9.0,
        "species": [
            {"name": "cyan", "color": "#3ad5ff", "count": 24},
            {"name": "violet", "color": "#9d5cff", "count": 22},
            {"name": "gold", "color": "#ffd166", "count": 18},
        ],
        "interactions": [
            [0.7, -0.9, 0.6],
            [0.8, 0.4, -0.8],
            [-0.7, 0.9, 0.2],
        ],
    },
    "petri": {
        "width": 100.0,
        "height": 100.0,
        "drag": 0.03,
        "force_scale": 36.0,
        "interaction_radius": 16.0,
        "repulsion_radius": 2.5,
        "max_speed": 8.0,
        "species": [
            {"name": "magenta", "color": "#ff4d8d", "count": 30},
            {"name": "mint", "color": "#4dffb8", "count": 30},
            {"name": "sun", "color": "#ffd84d", "count": 30},
        ],
        "interactions": [
            [0.2, 0.9, -0.8],
            [-0.8, 0.2, 0.9],
            [0.9, -0.8, 0.2],
        ],
    },
    "binary-star": {
        "width": 140.0,
        "height": 90.0,
        "drag": 0.07,
        "force_scale": 48.0,
        "interaction_radius": 20.0,
        "repulsion_radius": 3.5,
        "max_speed": 10.0,
        "species": [
            {"name": "ember", "color": "#ff7b54", "count": 28},
            {"name": "ice", "color": "#5cc8ff", "count": 28},
        ],
        "interactions": [
            [0.65, -1.0],
            [-1.0, 0.65],
        ],
    },
}


def built_in_presets() -> dict[str, dict]:
    """Return a deep copy of all bundled presets."""

    return deepcopy(_PRESETS)


def preset_names() -> list[str]:
    """Return sorted preset names."""

    return sorted(_PRESETS)


def get_preset(name: str) -> dict:
    """Return one preset by name."""

    try:
        return deepcopy(_PRESETS[name])
    except KeyError as exc:
        raise KeyError(f"unknown preset {name!r}; available: {', '.join(preset_names())}") from exc
