"""Configuration file support for training runs.

Supports JSON and YAML (if PyYAML is available; falls back to JSON-only).
A config file fully specifies a model architecture and training hyperparameters,
enabling reproducible experiments without code changes.

Example config (JSON)
---------------------
::

    {
        "model": {
            "nin": 2,
            "nouts": [8, 8, 1],
            "activation": "tanh",
            "init": "xavier",
            "dropout": 0.1
        },
        "optimizer": {
            "type": "adam",
            "lr": 0.01,
            "weight_decay": 0.001
        },
        "training": {
            "epochs": 500,
            "batch_size": 4,
            "seed": 42,
            "classification": true,
            "lr_scheduler": {
                "type": "cosine",
                "base_lr": 0.01,
                "T_max": 500,
                "eta_min": 0.0001
            }
        },
        "logging": {
            "level": "INFO",
            "verbose": true
        }
    }
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .nn import MLP
from .train import SGD, Adam, Optimizer
from .schedulers import LRScheduler, get_scheduler


@dataclass
class ModelConfig:
    nin: int = 2
    nouts: List[int] = field(default_factory=lambda: [8, 1])
    activation: str = "tanh"
    init: str = "xavier"
    dropout: float = 0.0

    def build(self) -> MLP:
        return MLP(
            nin=self.nin,
            nouts=self.nouts,
            activation=self.activation,
            init=self.init,
            dropout=self.dropout,
        )


@dataclass
class OptimizerConfig:
    type: str = "sgd"  # "sgd" or "adam"
    lr: float = 0.01
    momentum: float = 0.0
    weight_decay: float = 0.0
    betas: Tuple[float, float] = (0.9, 0.999)
    eps: float = 1e-8

    def build(self, params) -> Optimizer:
        if self.type == "sgd":
            return SGD(
                params, lr=self.lr,
                momentum=self.momentum, weight_decay=self.weight_decay,
            )
        elif self.type == "adam":
            return Adam(
                params, lr=self.lr,
                betas=self.betas, eps=self.eps, weight_decay=self.weight_decay,
            )
        else:
            raise ValueError(f"Unknown optimizer type: {self.type}")


@dataclass
class SchedulerConfig:
    type: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)

    def build(self) -> Optional[LRScheduler]:
        if self.type is None:
            return None
        return get_scheduler(self.type, **self.params)


@dataclass
class TrainingConfig:
    epochs: int = 100
    batch_size: Optional[int] = None
    seed: int = 42
    classification: bool = False
    lr_scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)

    def build_scheduler(self) -> Optional[LRScheduler]:
        return self.lr_scheduler.build()


@dataclass
class LoggingConfig:
    level: str = "INFO"
    verbose: bool = False

    def setup(self) -> logging.Logger:
        logger = logging.getLogger("autograd_engine")
        logger.setLevel(getattr(logging, self.level.upper(), logging.INFO))
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S"
            ))
            logger.addHandler(handler)
        return logger


@dataclass
class Config:
    model: ModelConfig = field(default_factory=ModelConfig)
    optimizer: OptimizerConfig = field(default_factory=OptimizerConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        model = ModelConfig(**data.get("model", {}))
        opt_data = data.get("optimizer", {})
        # Handle betas as list -> tuple
        if "betas" in opt_data:
            opt_data["betas"] = tuple(opt_data["betas"])
        optimizer = OptimizerConfig(**opt_data)
        train_data = data.get("training", {})
        sched_data = train_data.pop("lr_scheduler", {})
        lr_scheduler = SchedulerConfig(
            type=sched_data.get("type"),
            params=sched_data.get("params", sched_data),
        )
        training = TrainingConfig(lr_scheduler=lr_scheduler, **train_data)
        log_cfg = LoggingConfig(**data.get("logging", {}))
        return cls(model=model, optimizer=optimizer, training=training, logging=log_cfg)

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        """Load config from a JSON or YAML file."""
        text = Path(path).read_text()
        p = str(path)
        if p.endswith(".yaml") or p.endswith(".yml"):
            try:
                import yaml
            except ImportError:
                raise ImportError(
                    "PyYAML is required to load YAML config files. "
                    "Install it with: pip install pyyaml"
                )
            data = yaml.safe_load(text)
        else:
            data = json.loads(text)
        return cls.from_dict(data)

    def to_dict(self) -> Dict[str, Any]:
        import dataclasses
        def _asdict(obj):
            if dataclasses.is_dataclass(obj):
                return {k: _asdict(v) for k, v in dataclasses.asdict(obj).items()}
            return obj
        return _asdict(self)

    def save(self, path: str | Path) -> None:
        """Save config to a JSON file."""
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, default=str))


def default_config() -> Config:
    """Return a sensible default configuration for XOR-like problems."""
    return Config(
        model=ModelConfig(nin=2, nouts=[8, 8, 1], activation="tanh", dropout=0.0),
        optimizer=OptimizerConfig(type="adam", lr=0.01),
        training=TrainingConfig(epochs=300, batch_size=4, seed=42, classification=True),
        logging=LoggingConfig(level="INFO", verbose=True),
    )