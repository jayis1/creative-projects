"""
Trace — stores MCMC samples and provides summary / export utilities.
"""

from __future__ import annotations

import json
import math
from typing import Dict, List, Optional, Sequence

import numpy as np


class Trace:
    """Container for MCMC samples with diagnostics helpers.

    Parameters
    ----------
    samples : ndarray of shape (n_samples, dim) or (n_samples,)
    log_prob : list of float, optional
    names : list of str, optional — parameter names
    """

    def __init__(
        self,
        samples: np.ndarray,
        log_prob: Optional[Sequence[float]] = None,
        names: Optional[List[str]] = None,
    ):
        self.samples = np.asarray(samples, dtype=float)
        if self.samples.ndim == 1:
            self.samples = self.samples.reshape(-1, 1)
        self.n_samples, self.dim = self.samples.shape
        self.log_prob = (np.asarray(log_prob, dtype=float)
                         if log_prob is not None else None)
        if names is None:
            names = [f"x{i}" for i in range(self.dim)]
        if len(names) != self.dim:
            raise ValueError("names length must equal dim")
        self.names = names

    # ---- basic stats ---------------------------------------------------- #

    def mean(self, burn: int = 0) -> np.ndarray:
        return self.samples[burn:].mean(axis=0)

    def std(self, burn: int = 0) -> np.ndarray:
        return self.samples[burn:].std(axis=0)

    def var(self, burn: int = 0) -> np.ndarray:
        return self.samples[burn:].var(axis=0)

    def median(self, burn: int = 0) -> np.ndarray:
        return np.median(self.samples[burn:], axis=0)

    def quantiles(self, qs=(0.025, 0.25, 0.5, 0.75, 0.975), burn: int = 0) -> np.ndarray:
        return np.quantile(self.samples[burn:], qs, axis=0)

    def summary(self, burn: int = 0) -> Dict[str, Dict[str, float]]:
        q = self.quantiles(burn=burn)
        out: Dict[str, Dict[str, float]] = {}
        for i, nm in enumerate(self.names):
            out[nm] = {
                "mean": float(self.mean(burn)[i]),
                "std": float(self.std(burn)[i]),
                "2.5%": float(q[0, i]),
                "25%": float(q[1, i]),
                "50%": float(q[2, i]),
                "75%": float(q[3, i]),
                "97.5%": float(q[4, i]),
            }
        return out

    # ---- export --------------------------------------------------------- #

    def to_json(self, path: Optional[str] = None) -> str:
        data = {
            "names": self.names,
            "samples": self.samples.tolist(),
            "log_prob": self.log_prob.tolist() if self.log_prob is not None else None,
        }
        text = json.dumps(data, indent=2)
        if path:
            with open(path, "w") as fh:
                fh.write(text)
        return text

    @classmethod
    def from_json(cls, path_or_str: str) -> "Trace":
        import os
        if os.path.isfile(path_or_str):
            with open(path_or_str) as fh:
                data = json.load(fh)
        else:
            data = json.loads(path_or_str)
        return cls(
            samples=np.array(data["samples"]),
            log_prob=data.get("log_prob"),
            names=data.get("names"),
        )

    def __len__(self) -> int:
        return self.n_samples

    def __repr__(self) -> str:  # pragma: no cover
        return (f"Trace(n_samples={self.n_samples}, dim={self.dim}, "
                f"names={self.names})")