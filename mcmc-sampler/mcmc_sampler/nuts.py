"""
No-U-Turn Sampler (NUTS) — Hoffman & Gelman (2014).

NUTS automatically determines the trajectory length for HMC by building
a binary tree of leapfrog steps and stopping when the trajectory makes a
U-turn (the distance between the endpoints starts decreasing).

This implementation uses the efficient recursive doubling algorithm with
dual-averaging step-size adaptation during burn-in.

Reference
---------
Hoffman, M. D., & Gelman, A. (2014). The No-U-Turn Sampler:
Adaptively setting path lengths in Hamiltonian Monte Carlo. JMLR, 15(1),
1593-1623.
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence

import numpy as np

from .distributions import Target
from .samplers import _BaseSampler
from .trace import Trace


# Maximum tree depth — prevents runaway trajectories
_MAX_TREE_DEPTH = 10


def _leapfrog(target: Target, x: np.ndarray, p: np.ndarray,
              eps: float, n_steps: int = 1) -> tuple:
    """Leapfrog integration for ``n_steps`` steps."""
    for _ in range(n_steps):
        p = p + 0.5 * eps * target.grad_log_pdf(x)
        x = x + eps * p
        p = p + 0.5 * eps * target.grad_log_pdf(x)
    return x, p


def _hamiltonian(lp: float, p: np.ndarray) -> float:
    """Hamiltonian H = -log_pdf + 0.5 * p^T p."""
    return -lp + 0.5 * float(p @ p)


class _TreeResult:
    """Internal result from recursive tree building."""
    __slots__ = ("x_minus", "p_minus", "x_plus", "p_plus",
                 "x_prop", "lp_prop", "n_valid", "s", "alpha_sum", "n_alpha")

    def __init__(self):
        self.x_minus = None
        self.p_minus = None
        self.x_plus = None
        self.p_plus = None
        self.x_prop = None
        self.lp_prop = -math.inf
        self.n_valid = 0
        self.s = False
        self.alpha_sum = 0.0
        self.n_alpha = 0


class NUTS(_BaseSampler):
    """No-U-Turn Sampler with dual-averaging step-size adaptation.

    Parameters
    ----------
    target : Target
    max_tree_depth : int
        Maximum recursion depth for the binary tree (default 10).
    target_accept : float
        Target acceptance probability for dual-averaging (default 0.65,
        or 0.8 for the "efficient" variant suggested in the paper).
    init_step_size : float
        Initial leapfrog step size.
    rng : optional Generator
    """

    def __init__(self, target: Target, max_tree_depth: int = _MAX_TREE_DEPTH,
                 target_accept: float = 0.65,
                 init_step_size: float = 0.1,
                 rng: Optional[np.random.Generator] = None):
        super().__init__(target, rng, "NUTS")
        if max_tree_depth < 1:
            raise ValueError("max_tree_depth must be >= 1")
        if not 0 < target_accept < 1:
            raise ValueError("target_accept must be in (0,1)")
        self.max_tree_depth = int(max_tree_depth)
        self.target_accept = float(target_accept)
        self.step_size = float(init_step_size)
        self._tree_depths: List[int] = []  # diagnostics

    # -- public API ---------------------------------------------------- #

    def sample(self, x0: Sequence[float], n_samples: int = 10000,
               burn: int = 1000, thin: int = 1) -> Trace:
        if n_samples <= 0 or burn < 0 or thin < 1:
            raise ValueError("bad n_samples/burn/thin")
        self._reset()
        x = np.asarray(x0, dtype=float).reshape(-1)
        d = self.target.dim
        lp = self.target.log_pdf(x)
        if not math.isfinite(lp):
            raise ValueError("x0 has log_pdf = -inf")

        # dual-averaging state
        eps = self.step_size
        mu = math.log(10 * eps)
        log_eps_bar = 0.0
        H_bar = 0.0
        gamma, t0, kappa = 0.05, 10.0, 0.75

        total = burn + n_samples * thin
        kept, kept_lp = [], []
        self._tree_depths = []

        for i in range(total):
            p0 = self.rng.normal(size=d)
            H0 = _hamiltonian(lp, p0)
            # slice variable in log space
            log_u = -H0 + math.log(self.rng.random())

            x_minus = x.copy()
            x_plus = x.copy()
            p_minus = p0.copy()
            p_plus = p0.copy()
            j = 0
            x_prop = x.copy()
            lp_prop = lp
            n = 1
            s = True
            alpha_sum = 0.0
            n_alpha = 0
            depth = 0

            while s and j < self.max_tree_depth:
                # choose random direction
                direction = 1 if self.rng.random() < 0.5 else -1
                if direction == -1:
                    (x_minus, p_minus, _, _, x_new, lp_new,
                     n_new, s_new, a, na) = self._build_tree(
                        x_minus, p_minus, log_u, direction, j, eps, H0)
                else:
                    (_, _, x_plus, p_plus, x_new, lp_new,
                     n_new, s_new, a, na) = self._build_tree(
                        x_plus, p_plus, log_u, direction, j, eps, H0)

                if s_new:
                    # accept proposal from new subtree with prob n_new / n
                    if n > 0 and self.rng.random() < min(1.0, n_new / n):
                        x_prop = x_new.copy()
                        lp_prop = lp_new
                        self.accept_count += 1
                    self.total_count += 1

                n += n_new
                alpha_sum += a
                n_alpha += na

                # check U-turn on the full trajectory
                s = s_new and self._no_uturn(x_plus, x_minus, p_plus, p_minus)
                j += 1
                depth += 1

            self._tree_depths.append(depth)

            x = x_prop
            lp = lp_prop

            # dual-averaging step-size adaptation
            accept_stat = alpha_sum / max(n_alpha, 1)
            if i < burn:
                m = i + 1
                H_bar = (1 - 1.0 / (m + t0)) * H_bar + \
                        (1.0 / (m + t0)) * (self.target_accept - accept_stat)
                log_eps = mu - math.sqrt(m) / gamma * H_bar
                eta = m ** (-kappa)
                log_eps_bar = eta * log_eps + (1 - eta) * log_eps_bar
                eps = math.exp(log_eps)
            elif i == burn:
                eps = math.exp(log_eps_bar)

            self.step_size = eps

            if i >= burn and (i - burn) % thin == 0:
                kept.append(x.copy())
                kept_lp.append(lp)

        return self._make_trace(np.array(kept), kept_lp)

    @property
    def mean_tree_depth(self) -> float:
        """Average tree depth across all iterations (diagnostic)."""
        if not self._tree_depths:
            return 0.0
        return float(np.mean(self._tree_depths))

    # -- internal: recursive tree building ----------------------------- #

    def _build_tree(self, x, p, log_u, direction, j, eps, H0):
        """Recursively build a balanced binary tree of depth ``j``.

        Returns a 10-tuple:
        (x_minus, p_minus, x_plus, p_plus, x_prop, lp_prop,
         n_valid, s, alpha_sum, n_alpha)
        """
        if j == 0:
            # base case: single leapfrog step
            x_new, p_new = _leapfrog(
                self.target, x.copy(), p.copy(), eps * direction, n_steps=1)
            lp_new = self.target.log_pdf(x_new)
            H_new = _hamiltonian(lp_new, p_new)

            n_valid = 1 if log_u <= -H_new else 0
            # slice criterion: s = (log_u < Δmax - H_new)
            delta_max = 1000.0  # from the paper
            s = (log_u < delta_max - H_new) and math.isfinite(lp_new)
            # acceptance statistic
            alpha = min(1.0, math.exp(H0 - H_new)) if math.isfinite(lp_new) else 0.0
            return (x_new, p_new, x_new, p_new,
                    x_new, lp_new, n_valid, s, alpha, 1)

        # recursion: build left and right subtrees
        (x_minus, p_minus, x_plus, p_plus,
         x_prop_a, lp_prop_a, n_a, s_a, alpha_a, na_a) = \
            self._build_tree(x, p, log_u, direction, j - 1, eps, H0)

        if not s_a:
            return (x_minus, p_minus, x_plus, p_plus,
                    x_prop_a, lp_prop_a, n_a, s_a, alpha_a, na_a)

        if direction == -1:
            (x_minus, p_minus, _, _, x_prop_b, lp_prop_b,
             n_b, s_b, alpha_b, na_b) = \
                self._build_tree(x_minus, p_minus, log_u, direction, j - 1, eps, H0)
        else:
            (_, _, x_plus, p_plus, x_prop_b, lp_prop_b,
             n_b, s_b, alpha_b, na_b) = \
                self._build_tree(x_plus, p_plus, log_u, direction, j - 1, eps, H0)

        # choose proposal from the two subtrees
        n_total = n_a + n_b
        if n_total > 0 and self.rng.random() < n_b / n_total:
            x_prop_a = x_prop_b
            lp_prop_a = lp_prop_b

        # check U-turn on the combined tree
        s_combined = s_a and s_b and self._no_uturn(
            x_plus, x_minus, p_plus, p_minus)

        alpha_sum = alpha_a + alpha_b
        n_alpha = na_a + na_b

        return (x_minus, p_minus, x_plus, p_plus,
                x_prop_a, lp_prop_a, n_total, s_combined, alpha_sum, n_alpha)

    @staticmethod
    def _no_uturn(x_plus: np.ndarray, x_minus: np.ndarray,
                  p_plus: np.ndarray, p_minus: np.ndarray) -> bool:
        """Check the no-U-turn criterion: the trajectory should continue
        only if the distance between endpoints is still increasing in
        both directions."""
        dx = x_plus - x_minus
        return (float(dx @ p_plus) >= 0) and (float(dx @ p_minus) >= 0)