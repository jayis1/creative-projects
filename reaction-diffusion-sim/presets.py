"""
Parameter presets for reaction-diffusion models.

Each preset defines model, params, grid_size, dt, perturbation, and steps.
"""

# ──────────────────────────────────────────────────────
# Gray-Scott Presets
# ──────────────────────────────────────────────────────

GRAY_SCOTT_PRESETS = {
    # Classic patterns
    "spots": {
        "model": "gray-scott",
        "params": {"Du": 0.16, "Dv": 0.08, "F": 0.035, "k": 0.065},
        "grid_size": 128,
        "dt": 1.0,
        "steps": 5000,
        "perturbation": {"type": "center_square", "size": 20, "u_val": 0.0, "v_val": 1.0},
        "description": "Solitary spots pattern",
    },
    "mitosis": {
        "model": "gray-scott",
        "params": {"Du": 0.16, "Dv": 0.08, "F": 0.028, "k": 0.062},
        "grid_size": 128,
        "dt": 1.0,
        "steps": 10000,
        "perturbation": {"type": "center_square", "size": 20, "u_val": 0.0, "v_val": 1.0},
        "description": "Splitting/dividing spots",
    },
    "coral": {
        "model": "gray-scott",
        "params": {"Du": 0.16, "Dv": 0.08, "F": 0.0545, "k": 0.062},
        "grid_size": 128,
        "dt": 1.0,
        "steps": 8000,
        "perturbation": {"type": "center_square", "size": 20, "u_val": 0.0, "v_val": 1.0},
        "description": "Coral-like branching pattern",
    },
    "labyrinth": {
        "model": "gray-scott",
        "params": {"Du": 0.16, "Dv": 0.08, "F": 0.029, "k": 0.057},
        "grid_size": 128,
        "dt": 1.0,
        "steps": 10000,
        "perturbation": {"type": "random", "noise": 0.02},
        "description": "Fingerprint/maze labyrinth pattern",
    },
    "waves": {
        "model": "gray-scott",
        "params": {"Du": 0.16, "Dv": 0.08, "F": 0.014, "k": 0.045},
        "grid_size": 128,
        "dt": 1.0,
        "steps": 10000,
        "perturbation": {"type": "center_square", "size": 20, "u_val": 0.0, "v_val": 1.0},
        "description": "Pulsating wave pattern",
    },
    "finger": {
        "model": "gray-scott",
        "params": {"Du": 0.16, "Dv": 0.08, "F": 0.026, "k": 0.051},
        "grid_size": 128,
        "dt": 1.0,
        "steps": 12000,
        "perturbation": {"type": "center_square", "size": 40, "u_val": 0.0, "v_val": 1.0},
        "description": "Growing finger-like structures",
    },
    "holes": {
        "model": "gray-scott",
        "params": {"Du": 0.16, "Dv": 0.08, "F": 0.039, "k": 0.058},
        "grid_size": 128,
        "dt": 1.0,
        "steps": 8000,
        "perturbation": {"type": "random", "noise": 0.03},
        "description": "Inverse spots (holes) pattern",
    },
    "stripes": {
        "model": "gray-scott",
        "params": {"Du": 0.16, "Dv": 0.08, "F": 0.04, "k": 0.06},
        "grid_size": 128,
        "dt": 1.0,
        "steps": 8000,
        "perturbation": {"type": "random", "noise": 0.02},
        "description": "Stripe formation",
    },
    "worms": {
        "model": "gray-scott",
        "params": {"Du": 0.16, "Dv": 0.08, "F": 0.046, "k": 0.059},
        "grid_size": 128,
        "dt": 1.0,
        "steps": 8000,
        "perturbation": {"type": "random", "noise": 0.02},
        "description": "Worm-like interlaced pattern",
    },
    "mazelike": {
        "model": "gray-scott",
        "params": {"Du": 0.16, "Dv": 0.08, "F": 0.029, "k": 0.057},
        "grid_size": 200,
        "dt": 1.0,
        "steps": 15000,
        "perturbation": {"type": "random", "noise": 0.03},
        "description": "Large maze-like labyrinth (high-res)",
    },
    "chaos": {
        "model": "gray-scott",
        "params": {"Du": 0.16, "Dv": 0.08, "F": 0.018, "k": 0.051},
        "grid_size": 128,
        "dt": 1.0,
        "steps": 12000,
        "perturbation": {"type": "multi_spot", "count": 8, "size": 10},
        "description": "Chaotic splitting pattern",
    },
    "solitons": {
        "model": "gray-scott",
        "params": {"Du": 0.16, "Dv": 0.08, "F": 0.03, "k": 0.062},
        "grid_size": 128,
        "dt": 1.0,
        "steps": 10000,
        "perturbation": {"type": "multi_spot", "count": 12, "size": 8},
        "description": "Stable soliton spots",
    },
    "nucleation": {
        "model": "gray-scott",
        "params": {"Du": 0.16, "Dv": 0.08, "F": 0.025, "k": 0.06},
        "grid_size": 128,
        "dt": 1.0,
        "steps": 15000,
        "perturbation": {"type": "center_square", "size": 10, "u_val": 0.0, "v_val": 1.0},
        "description": "Nucleation and slow growth",
    },
}

# ──────────────────────────────────────────────────────
# FitzHugh-Nagumo Presets
# ──────────────────────────────────────────────────────

FHN_PRESETS = {
    "pulse": {
        "model": "fhn",
        "params": {"Du": 0.001, "Dv": 0.004, "epsilon": 0.04, "beta": 0.5, "gamma": 1.0},
        "grid_size": 128,
        "dt": 0.1,
        "steps": 5000,
        "perturbation": {"type": "center_square", "size": 10, "u_val": 1.0, "v_val": 0.5},
        "description": "Traveling pulse wave",
    },
    "spiral": {
        "model": "fhn",
        "params": {"Du": 0.001, "Dv": 0.004, "epsilon": 0.02, "beta": 0.5, "gamma": 1.0},
        "grid_size": 128,
        "dt": 0.05,
        "steps": 10000,
        "perturbation": {"type": "center_square", "size": 10, "u_val": 1.0, "v_val": 0.5},
        "description": "Spiral wave pattern",
    },
}

# ──────────────────────────────────────────────────────
# Gierer-Meinhardt Presets
# ──────────────────────────────────────────────────────

GM_PRESETS = {
    "spots_gm": {
        "model": "gierer-meinhardt",
        "params": {"Du": 0.02, "Dv": 0.4, "rho": 0.001, "mu": 0.02},
        "grid_size": 128,
        "dt": 0.01,
        "steps": 8000,
        "perturbation": {"type": "random", "noise": 0.01},
        "description": "Self-amplifying spots",
    },
    "stripes_gm": {
        "model": "gierer-meinhardt",
        "params": {"Du": 0.02, "Dv": 0.6, "rho": 0.002, "mu": 0.03},
        "grid_size": 128,
        "dt": 0.01,
        "steps": 8000,
        "perturbation": {"type": "random", "noise": 0.01},
        "description": "Stripe formation",
    },
}

# ──────────────────────────────────────────────────────
# Brusselator Presets
# ──────────────────────────────────────────────────────

BRUSSELATOR_PRESETS = {
    "brusselator": {
        "model": "brusselator",
        "params": {"Du": 0.002, "Dv": 0.008, "A": 1.0, "B": 3.0},
        "grid_size": 128,
        "dt": 0.05,
        "steps": 5000,
        "perturbation": {"type": "random", "noise": 0.05},
        "description": "Oscillating Brusselator pattern",
    },
    "brusselator_hex": {
        "model": "brusselator",
        "params": {"Du": 0.002, "Dv": 0.01, "A": 1.0, "B": 2.5},
        "grid_size": 128,
        "dt": 0.05,
        "steps": 8000,
        "perturbation": {"type": "random", "noise": 0.05},
        "description": "Hexagonal Brusselator pattern",
    },
}

# ──────────────────────────────────────────────────────
# Combined Registry
# ──────────────────────────────────────────────────────

ALL_PRESETS = {}
ALL_PRESETS.update(GRAY_SCOTT_PRESETS)
ALL_PRESETS.update(FHN_PRESETS)
ALL_PRESETS.update(GM_PRESETS)
ALL_PRESETS.update(BRUSSELATOR_PRESETS)


def get_preset(name):
    """Look up a preset by name. Raises KeyError if not found."""
    if name not in ALL_PRESETS:
        available = ", ".join(sorted(ALL_PRESETS.keys()))
        raise KeyError(f"Unknown preset '{name}'. Available: {available}")
    return ALL_PRESETS[name]


def list_presets():
    """Return list of (name, description) tuples for all presets."""
    return [(name, ALL_PRESETS[name]["description"]) for name in sorted(ALL_PRESETS.keys())]