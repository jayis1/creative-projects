"""
MCMC sampler implementations.

All samplers follow the same interface:

    sampler = MetropolisHastings(target, proposal_std=1.0)
    trace = sampler.sample(x0, n_samples=10_000, burn=1000, thin=1)

They return a :class:`Trace` object.
"""

from __future__ import annotations

import math
from typing import Callable, List, Optional, Sequence

import numpy as np

from .distributions import Target
from .trace import Trace


# --------------------------------------------------------------------------- #
# Base
# --------------------------------------------------------------------------- #


class _BaseSampler:
    """Common scaffolding for all samplers."""

    def __init__(self, target: Target, rng: Optional[np.random.Generator] = None, name: str = "sampler"):
        self.target = target
        self.rng = rng or np.random.default_rng()
        self.name = name
        self.accept_count = 0
        self.total_count = 0

    @property
    def acceptance_rate(self) -> float:
        return self.accept_count / max(self.total_count, 1)

    def _reset(self) -> None:
        self.accept_count = 0
        self.total_count = 0

    def _make_trace(self, samples: np.ndarray, log_prob: List[float]) -> Trace:
        return Trace(samples, log_prob=log_prob)


# --------------------------------------------------------------------------- #
# Metropolis–Hastings (random-walk)
# --------------------------------------------------------------------------- #


class MetropolisHastings(_BaseSampler):
    """Random-walk Metropolis–Hastings with a Gaussian proposal.

    Parameters
    ----------
    target : Target
    proposal_std : float or array
        Std-dev of the symmetric Gaussian proposal.  Scalar broadcasts to
        every dimension.
    rng : optional Generator
    """

    def __init__(self, target: Target, proposal_std: float = 1.0,
                 rng: Optional[np.random.Generator] = None):
        super().__init__(target, rng, "MetropolisHastings")
        if np.isscalar(proposal_std):
            self.proposal_std = np.full(target.dim, float(proposal_std))
        else:
            self.proposal_std = np.asarray(proposal_std, dtype=float)
            if self.proposal_std.shape[0] != target.dim:
                raise ValueError("proposal_std length must equal target.dim")

    def sample(self, x0: Sequence[float], n_samples: int = 10000,
               burn: int = 1000, thin: int = 1) -> Trace:
        if n_samples <= 0:
            raise ValueError("n_samples must be positive")
        if burn < 0:
            raise ValueError("burn must be non-negative")
        if thin < 1:
            raise ValueError("thin must be >= 1")
        self._reset()
        x = np.asarray(x0, dtype=float).reshape(-1)
        if x.shape[0] != self.target.dim:
            raise ValueError("x0 dimension mismatch")
        lp = self.target.log_pdf(x)
        if not math.isfinite(lp):
            raise ValueError("initial point has log_pdf = -inf; pick another x0")

        total_iters = burn + n_samples * thin
        kept: List[np.ndarray] = []
        kept_lp: List[float] = []
        for i in range(total_iters):
            proposal = x + self.rng.normal(size=self.target.dim) * self.proposal_std
            lp_prop = self.target.log_pdf(proposal)
            self.total_count += 1
            # accept w/ MH ratio (symmetric proposal ⇒ q cancels)
            if math.isfinite(lp_prop):
                log_alpha = lp_prop - lp
                if log_alpha >= 0 or math.log(self.rng.random()) < log_alpha:
                    x, lp = proposal, lp_prop
                    self.accept_count += 1
            if i >= burn and (i - burn) % thin == 0:
                kept.append(x.copy())
                kept_lp.append(lp)
        return self._make_trace(np.array(kept), kept_lp)


# --------------------------------------------------------------------------- #
# Adaptive Metropolis
# --------------------------------------------------------------------------- #


class AdaptiveMetropolis(_BaseSampler):
    """Adaptive Metropolis (Haario et al. 2001).

    Continuously tunes the proposal covariance from the empirical covariance
    of the chain so far, scaled by ``(2.38^2 / dim) * eps``.
    """

    def __init__(self, target: Target, init_std: float = 1.0,
                 scale: float = 2.38, rng: Optional[np.random.Generator] = None):
        super().__init__(target, rng, "AdaptiveMetropolis")
        self.init_std = float(init_std)
        self.scale = float(scale)

    def sample(self, x0: Sequence[float], n_samples: int = 10000,
               burn: int = 1000, thin: int = 1,
               adapt_start: int = 100) -> Trace:
        if n_samples <= 0 or burn < 0 or thin < 1:
            raise ValueError("bad n_samples/burn/thin")
        self._reset()
        x = np.asarray(x0, dtype=float).reshape(-1)
        d = self.target.dim
        lp = self.target.log_pdf(x)
        if not math.isfinite(lp):
            raise ValueError("x0 has log_pdf = -inf")
        cov = np.eye(d) * self.init_std ** 2
        chol = np.linalg.cholesky(cov)
        hist = [x.copy()]
        total = burn + n_samples * thin
        kept, kept_lp = [], []
        for i in range(total):
            z = self.rng.normal(size=d)
            proposal = x + chol @ z
            lp_prop = self.target.log_pdf(proposal)
            self.total_count += 1
            if math.isfinite(lp_prop):
                log_alpha = lp_prop - lp
                if log_alpha >= 0 or math.log(self.rng.random()) < log_alpha:
                    x, lp = proposal, lp_prop
                    self.accept_count += 1
            hist.append(x.copy())
            if i >= adapt_start and i % 50 == 0:
                arr = np.array(hist)
                emp = np.cov(arr.T) if d > 1 else np.array([[arr[:, 0].var()]])
                emp += np.eye(d) * 1e-8
                try:
                    chol = np.linalg.cholesky(
                        (self.scale ** 2 / d) * emp + np.eye(d) * 1e-10
                    )
                except np.linalg.LinAlgError:
                    pass
            if i >= burn and (i - burn) % thin == 0:
                kept.append(x.copy())
                kept_lp.append(lp)
        return self._make_trace(np.array(kept), kept_lp)


# --------------------------------------------------------------------------- #
# Hamiltonian Monte Carlo
# --------------------------------------------------------------------------- #


class HamiltonianMC(_BaseSampler):
    """Hamiltonian Monte Carlo with leapfrog integration.

    Uses the gradient of the log-density (analytical if provided by the
    target, otherwise central-difference numerical gradient).

    Parameters
    ----------
    target : Target
    step_size : float — leapfrog step length
    n_steps : int — number of leapfrog steps per proposal
    """

    def __init__(self, target: Target, step_size: float = 0.1,
                 n_steps: int = 20, rng: Optional[np.random.Generator] = None):
        super().__init__(target, rng, "HamiltonianMC")
        if step_size <= 0:
            raise ValueError("step_size must be positive")
        if n_steps < 1:
            raise ValueError("n_steps must be >= 1")
        self.step_size = float(step_size)
        self.n_steps = int(n_steps)

    def _leapfrog(self, x: np.ndarray, p: np.ndarray) -> tuple:
        eps = self.step_size
        p = p + 0.5 * eps * self.target.grad_log_pdf(x)
        for _ in range(self.n_steps - 1):
            x = x + eps * p
            p = p + eps * self.target.grad_log_pdf(x)
        x = x + eps * p
        p = p + 0.5 * eps * self.target.grad_log_pdf(x)
        return x, p

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
        total = burn + n_samples * thin
        kept, kept_lp = [], []
        for i in range(total):
            p0 = self.rng.normal(size=d)
            x_new, p_new = self._leapfrog(x.copy(), p0.copy())
            lp_new = self.target.log_pdf(x_new)
            # Hamiltonian: H = -log_pdf + 0.5*p^2
            H_old = -lp + 0.5 * float(p0 @ p0)
            H_new = -lp_new + 0.5 * float(p_new @ p_new)
            self.total_count += 1
            if math.isfinite(lp_new):
                log_alpha = H_old - H_new  # accept if ΔH ≤ 0
                if log_alpha >= 0 or math.log(self.rng.random()) < log_alpha:
                    x, lp = x_new, lp_new
                    self.accept_count += 1
            if i >= burn and (i - burn) % thin == 0:
                kept.append(x.copy())
                kept_lp.append(lp)
        return self._make_trace(np.array(kept), kept_lp)


class HMCWithAdaptation(_BaseSampler):
    """HMC with dual-averaging step-size adaptation (Nesterov, Hoffman & Gelman 2014).

    During the burn-in period the step size is adapted to target a desired
    acceptance probability.  After burn-in the step size is frozen.
    """

    def __init__(self, target: Target, n_steps: int = 20,
                 target_accept: float = 0.65,
                 init_step_size: float = 0.1,
                 rng: Optional[np.random.Generator] = None):
        super().__init__(target, rng, "HMCWithAdaptation")
        if n_steps < 1:
            raise ValueError("n_steps must be >= 1")
        if not 0 < target_accept < 1:
            raise ValueError("target_accept must be in (0,1)")
        self.n_steps = int(n_steps)
        self.target_accept = float(target_accept)
        self.step_size = float(init_step_size)

    def _leapfrog(self, x, p, eps):
        p = p + 0.5 * eps * self.target.grad_log_pdf(x)
        for _ in range(self.n_steps - 1):
            x = x + eps * p
            p = p + eps * self.target.grad_log_pdf(x)
        x = x + eps * p
        p = p + 0.5 * eps * self.target.grad_log_pdf(x)
        return x, p

    def sample(self, x0, n_samples=10000, burn=1000, thin=1) -> Trace:
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
        for i in range(total):
            p0 = self.rng.normal(size=d)
            x_new, p_new = self._leapfrog(x.copy(), p0.copy(), eps)
            lp_new = self.target.log_pdf(x_new)
            H_old = -lp + 0.5 * float(p0 @ p0)
            H_new = -lp_new + 0.5 * float(p_new @ p_new)
            self.total_count += 1
            accept_prob = 0.0
            if math.isfinite(lp_new):
                log_alpha = H_old - H_new
                accept_prob = min(1.0, math.exp(log_alpha)) if log_alpha < 0 else 1.0
                if log_alpha >= 0 or math.log(self.rng.random()) < log_alpha:
                    x, lp = x_new, lp_new
                    self.accept_count += 1
            # adapt step size during burn-in
            if i < burn:
                m = i + 1
                H_bar = (1 - 1.0 / (m + t0)) * H_bar + (1.0 / (m + t0)) * (self.target_accept - accept_prob)
                log_eps = mu - math.sqrt(m) / gamma * H_bar
                eta = m ** (-kappa)
                log_eps_bar = eta * log_eps + (1 - eta) * log_eps_bar
                eps = math.exp(log_eps)
            elif i == burn:
                eps = math.exp(log_eps_bar)  # freeze adapted step
            self.step_size = eps
            if i >= burn and (i - burn) % thin == 0:
                kept.append(x.copy())
                kept_lp.append(lp)
        return self._make_trace(np.array(kept), kept_lp)


# --------------------------------------------------------------------------- #
# Slice sampler (univariate, applied coordinate-wise)
# --------------------------------------------------------------------------- #


class SliceSampler(_BaseSampler):
    """Coordinate-wise slice sampler (Neal 2003).

    Updates each dimension in turn using stepping-out and shrinkage.
    """

    def __init__(self, target: Target, width: float = 1.0,
                 max_steps: int = 50, rng: Optional[np.random.Generator] = None):
        super().__init__(target, rng, "SliceSampler")
        self.width = float(width)
        self.max_steps = int(max_steps)

    def _slice_1d(self, x: np.ndarray, idx: int, lp: float) -> tuple:
        w = self.width
        y = lp + math.log(self.rng.random())  # slice level (log space)
        # stepping out
        u = self.rng.random()
        L = x[idx] - w * u
        R = L + w
        steps = 0
        xc = x.copy()
        xc[idx] = L
        while steps < self.max_steps and self.target.log_pdf(xc) > y:
            L -= w
            xc[idx] = L
            steps += 1
        xc = x.copy()
        xc[idx] = R
        steps = 0
        while steps < self.max_steps and self.target.log_pdf(xc) > y:
            R += w
            xc[idx] = R
            steps += 1
        # shrinkage
        while True:
            xp = L + self.rng.random() * (R - L)
            xc = x.copy()
            xc[idx] = xp
            lp_new = self.target.log_pdf(xc)
            if lp_new > y:
                return xc, lp_new
            if xp < x[idx]:
                L = xp
            else:
                R = xp

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
        total = burn + n_samples * thin
        kept, kept_lp = [], []
        for i in range(total):
            for idx in range(d):
                x, lp = self._slice_1d(x, idx, lp)
                self.total_count += 1
                self.accept_count += 1  # slice always "accepts"
            if i >= burn and (i - burn) % thin == 0:
                kept.append(x.copy())
                kept_lp.append(lp)
        return self._make_trace(np.array(kept), kept_lp)


# --------------------------------------------------------------------------- #
# Gibbs sampler
# --------------------------------------------------------------------------- #


class GibbsSampler(_BaseSampler):
    """Gibbs sampler that uses user-provided conditional samplers.

    Parameters
    ----------
    target : Target
    conditionals : list of callables
        ``conditionals[i](x, rng) -> float`` draws from p(x_i | x_{-i}).
    """

    def __init__(self, target: Target, conditionals: Sequence[Callable],
                 rng: Optional[np.random.Generator] = None):
        super().__init__(target, rng, "GibbsSampler")
        if len(conditionals) != target.dim:
            raise ValueError("need one conditional per dimension")
        self.conditionals = list(conditionals)

    def sample(self, x0: Sequence[float], n_samples: int = 10000,
               burn: int = 1000, thin: int = 1) -> Trace:
        if n_samples <= 0 or burn < 0 or thin < 1:
            raise ValueError("bad n_samples/burn/thin")
        self._reset()
        x = np.asarray(x0, dtype=float).reshape(-1)
        d = self.target.dim
        total = burn + n_samples * thin
        kept, kept_lp = [], []
        for i in range(total):
            for idx in range(d):
                x[idx] = float(self.conditionals[idx](x.copy(), self.rng))
                self.total_count += 1
                self.accept_count += 1
            lp = self.target.log_pdf(x)
            if i >= burn and (i - burn) % thin == 0:
                kept.append(x.copy())
                kept_lp.append(lp)
        return self._make_trace(np.array(kept), kept_lp)