"""Model serialization: save and load MLP parameters to/from JSON.

This module provides ``save_model`` and ``load_model`` functions that
serialize the architecture configuration and parameter values of an
``MLP`` to a JSON file, and deserialize them back into a new ``MLP``
instance with identical architecture and restored weights.

Format
------
The JSON file has the following structure::

    {
        "architecture": {
            "nin": 2,
            "nouts": [8, 1],
            "activation": "tanh",
            "init": "xavier",
            "dropout": 0.0
        },
        "parameters": [
            [0.12, -0.34, ...],   # layer 0 weights + biases, flattened
            ...
        ]
    }
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .nn import MLP


def save_model(model: MLP, path: str | Path) -> None:
    """Save an MLP's architecture and parameters to a JSON file."""
    # Collect architecture
    arch: Dict[str, Any] = {
        "nin": len(model.layers[0].neurons[0].w) if model.layers else 0,
        "nouts": [len(layer.neurons) for layer in model.layers],
        "activation": model.layers[0].neurons[0].activation if model.layers else "linear",
        "init": "xavier",
        "dropout": getattr(model.layers[0], "dropout", 0.0) if model.layers else 0.0,
    }
    # Collect parameters as nested lists per layer
    params = []
    for layer in model.layers:
        layer_params = []
        for neuron in layer.neurons:
            layer_params.append([w.data for w in neuron.w] + [neuron.b.data])
        params.append(layer_params)
    data = {"architecture": arch, "parameters": params}
    Path(path).write_text(json.dumps(data, indent=2))


def load_model(path: str | Path) -> MLP:
    """Load an MLP from a JSON file produced by ``save_model``."""
    data = json.loads(Path(path).read_text())
    arch = data["architecture"]
    model = MLP(
        nin=arch["nin"],
        nouts=arch["nouts"],
        activation=arch.get("activation", "tanh"),
        init=arch.get("init", "xavier"),
        dropout=arch.get("dropout", 0.0),
    )
    params = data["parameters"]
    for layer, layer_params in zip(model.layers, params):
        for neuron, neuron_params in zip(layer.neurons, layer_params):
            # neuron_params = [w0, w1, ..., wn, bias]
            for i, w in enumerate(neuron.w):
                w.data = neuron_params[i]
            neuron.b.data = neuron_params[-1]
    return model