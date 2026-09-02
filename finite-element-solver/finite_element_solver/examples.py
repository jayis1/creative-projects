from __future__ import annotations

EXAMPLE_MODELS = {
    "triangle": {
        "metadata": {"title": "Cantilever triangle"},
        "materials": [{"id": "steel", "E": 210000000000.0, "density": 7850.0, "yield_strength": 250000000.0}],
        "sections": [{"id": "rod", "A": 0.003}],
        "nodes": [
            {"id": "A", "x": 0.0, "y": 0.0},
            {"id": "B", "x": 1.0, "y": 0.0},
            {"id": "C", "x": 1.0, "y": 1.0},
        ],
        "elements": [
            {"id": "AB", "start": "A", "end": "B", "material": "steel", "section": "rod"},
            {"id": "BC", "start": "B", "end": "C", "material": "steel", "section": "rod"},
            {"id": "AC", "start": "A", "end": "C", "material": "steel", "section": "rod"},
        ],
        "supports": [
            {"node": "A", "fix": [True, True]},
            {"node": "B", "fix": [False, True]},
        ],
        "load_cases": [
            {"name": "service", "node_loads": [{"node": "C", "load": [0.0, -1000.0]}]},
            {"name": "gravity", "gravity": [0.0, -9.81], "include_self_weight": True},
        ],
        "load_combinations": [
            {"name": "service_plus_gravity", "cases": {"service": 1.0, "gravity": 1.0}}
        ],
    },
    "roof": {
        "metadata": {"title": "Roof truss"},
        "materials": [{"id": "steel", "E": 200000000000.0, "density": 7850.0, "yield_strength": 250000000.0}],
        "sections": [{"id": "chord", "A": 0.004}],
        "nodes": [
            {"id": "A", "x": 0.0, "y": 0.0},
            {"id": "B", "x": 2.0, "y": 0.0},
            {"id": "C", "x": 4.0, "y": 0.0},
            {"id": "D", "x": 1.0, "y": 1.0},
            {"id": "E", "x": 3.0, "y": 1.0},
        ],
        "elements": [
            {"id": "AB", "start": "A", "end": "B", "material": "steel", "section": "chord"},
            {"id": "BC", "start": "B", "end": "C", "material": "steel", "section": "chord"},
            {"id": "AD", "start": "A", "end": "D", "material": "steel", "section": "chord"},
            {"id": "DB", "start": "D", "end": "B", "material": "steel", "section": "chord"},
            {"id": "BE", "start": "B", "end": "E", "material": "steel", "section": "chord"},
            {"id": "EC", "start": "E", "end": "C", "material": "steel", "section": "chord"},
            {"id": "DE", "start": "D", "end": "E", "material": "steel", "section": "chord"},
        ],
        "supports": [
            {"node": "A", "fix": [True, True]},
            {"node": "C", "fix": [False, True]},
        ],
        "load_cases": [
            {
                "name": "snow",
                "node_loads": [
                    {"node": "D", "load": [0.0, -6000.0]},
                    {"node": "E", "load": [0.0, -6000.0]}
                ]
            },
            {
                "name": "self-weight",
                "gravity": [0.0, -9.81],
                "include_self_weight": True
            },
            {
                "name": "wind-uplift",
                "node_loads": [
                    {"node": "D", "load": [0.0, 2500.0]},
                    {"node": "E", "load": [0.0, 2500.0]}
                ]
            }
        ],
        "load_combinations": [
            {"name": "ultimate-down", "cases": {"self-weight": 1.2, "snow": 1.6}},
            {"name": "ultimate-uplift", "cases": {"self-weight": 0.9, "wind-uplift": 1.3}}
        ]
    }
}
