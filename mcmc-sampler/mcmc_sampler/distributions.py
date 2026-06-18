"""
Target distributions for MCMC sampling.

Every distribution exposes a ``log_pdf(x)`` method returning the log-density
(unnormalised is fine — MCMC only needs the ratio).  Multi-variate targets
return a scalar log-density for a vector ``x`` (numpy array or list).
"""

from __future__ import annotations

import math
from typing import Callable, List, Optional, Sequence, Union

import numpy as np

Array = Union[np.ndarray, Sequence[float]]


class Target:
    """Base class — wrap any log-density callable into a target.

    Parameters
    ----------
    log_pdf : callable
        ``log_pdf(x) -> float``.  May be unnormalised.
    dim : int
        Dimensionality of the sample space.
    name : str
        Human-readable label used in traces / reports.
    """

    def __init__(self, log_pdf: Callable[[Array], float], dim: int = 1, name: str = "custom"):
        if dim < 1:
            raise ValueError("dim must be >= 1")
        self._log_pdf = log_pdf
        self.dim = dim
        self.name = name

    def log_pdf(self, x: Array) -> float:
        """Return log p(x) (may be unnormalised)."""
        return float(self._log_pdf(np.asarray(x, dtype=float)))

    # convenience for samplers that want the gradient
    def grad_log_pdf(self, x: Array) -> np.ndarray:
        """Numerical gradient via central differences (fallback)."""
        x = np.asarray(x, dtype=float)
        eps = 1e-6
        g = np.zeros_like(x)
        for i in range(x.shape[0]):
            xp = x.copy(); xp[i] += eps
            xm = x.copy(); xm[i] -= eps
            g[i] = (self.log_pdf(xp) - self.log_pdf(xm)) / (2 * eps)
        return g

    def __repr__(self) -> str:  # pragma: no cover
        return f"Target(name={self.name!r}, dim={self.dim})"


# --------------------------------------------------------------------------- #
# Built-in parametric distributions
# --------------------------------------------------------------------------- #


class Normal(Target):
    """Univariate normal N(mu, sigma^2)."""

    def __init__(self, mu: float = 0.0, sigma: float = 1.0):
        if sigma <= 0:
            raise ValueError("sigma must be positive")
        self.mu = float(mu)
        self.sigma = float(sigma)
        super().__init__(self._logpdf, dim=1, name=f"Normal({mu},{sigma})")

    def _logpdf(self, x: np.ndarray) -> float:
        z = (float(x[0]) if x.ndim else float(x)) - self.mu
        return -0.5 * (z / self.sigma) ** 2 - math.log(self.sigma) - 0.5 * math.log(2 * math.pi)


class MultivariateNormal(Target):
    """Multivariate normal N(mu, Sigma)."""

    def __init__(self, mu: Sequence[float], cov: Sequence[Sequence[float]]):
        self.mu = np.asarray(mu, dtype=float)
        self.cov = np.asarray(cov, dtype=float)
        if self.cov.ndim != 2 or self.cov.shape[0] != self.cov.shape[1]:
            raise ValueError("cov must be a square 2-D array")
        if self.mu.shape[0] != self.cov.shape[0]:
            raise ValueError("mu and cov dimension mismatch")
        self._k = self.mu.shape[0]
        self._sign, self._logdet = np.linalg.slogdet(self.cov)
        if self._sign <= 0:
            raise ValueError("cov must be positive-definite")
        self._prec = np.linalg.inv(self.cov)
        super().__init__(self._logpdf, dim=self._k, name="MultivariateNormal")

    def _logpdf(self, x: np.ndarray) -> float:
        x = np.asarray(x, dtype=float).reshape(-1)
        d = x - self.mu
        quad = float(d @ self._prec @ d)
        return -0.5 * quad - 0.5 * self._logdet - 0.5 * self._k * math.log(2 * math.pi)


class Exponential(Target):
    """Exponential distribution with rate lambda: p(x) = lambda e^{-lambda x}."""

    def __init__(self, lam: float = 1.0):
        if lam <= 0:
            raise ValueError("lambda must be positive")
        self.lam = float(lam)
        super().__init__(self._logpdf, dim=1, name=f"Exponential({lam})")

    def _logpdf(self, x: np.ndarray) -> float:
        v = float(x[0]) if x.ndim else float(x)
        if v < 0:
            return -math.inf
        return math.log(self.lam) - self.lam * v


class Beta(Target):
    """Beta(alpha, beta) distribution on [0, 1]."""

    def __init__(self, alpha: float = 1.0, beta: float = 1.0):
        if alpha <= 0 or beta <= 0:
            raise ValueError("alpha and beta must be positive")
        self.alpha = float(alpha)
        self.beta = float(beta)
        self._log_beta = math.lgamma(alpha) + math.lgamma(beta) - math.lgamma(alpha + beta)
        super().__init__(self._logpdf, dim=1, name=f"Beta({alpha},{beta})")

    def _logpdf(self, x: np.ndarray) -> float:
        v = float(x[0]) if x.ndim else float(x)
        if v <= 0 or v >= 1:
            return -math.inf
        return (self.alpha - 1) * math.log(v) + (self.beta - 1) * math.log(1 - v) - self._log_beta


class Uniform(Target):
    """Uniform distribution on [a, b]."""

    def __init__(self, a: float = 0.0, b: float = 1.0):
        if b <= a:
            raise ValueError("b must be > a")
        self.a = float(a)
        self.b = float(b)
        self._log_h = -math.log(b - a)
        super().__init__(self._logpdf, dim=1, name=f"Uniform({a},{b})")

    def _logpdf(self, x: np.ndarray) -> float:
        v = float(x[0]) if x.ndim else float(x)
        if v < self.a or v > self.b:
            return -math.inf
        return self._log_h


class Gamma(Target):
    """Gamma(shape=k, scale=theta): p(x) = x^{k-1} e^{-x/theta} / (Gamma(k) theta^k)."""

    def __init__(self, k: float = 1.0, theta: float = 1.0):
        if k <= 0 or theta <= 0:
            raise ValueError("k and theta must be positive")
        self.k = float(k)
        self.theta = float(theta)
        self._log_norm = math.lgamma(k) + k * math.log(theta)
        super().__init__(self._logpdf, dim=1, name=f"Gamma({k},{theta})")

    def _logpdf(self, x: np.ndarray) -> float:
        v = float(x[0]) if x.ndim else float(x)
        if v <= 0:
            return -math.inf
        return (self.k - 1) * math.log(v) - v / self.theta - self._log_norm


class StudentT(Target):
    """Student-t distribution with nu degrees of freedom, location mu, scale sigma."""

    def __init__(self, nu: float = 3.0, mu: float = 0.0, sigma: float = 1.0):
        if nu <= 0:
            raise ValueError("nu must be positive")
        if sigma <= 0:
            raise ValueError("sigma must be positive")
        self.nu = float(nu)
        self.mu = float(mu)
        self.sigma = float(sigma)
        self._log_norm = (math.lgamma((nu + 1) / 2) - math.lgamma(nu / 2)
                          - 0.5 * math.log(nu * math.pi) - math.log(sigma))
        super().__init__(self._logpdf, dim=1, name=f"StudentT({nu},{mu},{sigma})")

    def _logpdf(self, x: np.ndarray) -> float:
        v = float(x[0]) if x.ndim else float(x)
        z = (v - self.mu) / self.sigma
        return self._log_norm - 0.5 * (self.nu + 1) * math.log(1 + z * z / self.nu)


class Dirichlet(Target):
    """Dirichlet distribution on the simplex.

    Parameters
    ----------
    alpha : sequence of float
        Concentration parameters (all positive).
    """

    def __init__(self, alpha: Sequence[float]):
        alpha = np.asarray(alpha, dtype=float)
        if alpha.ndim != 1 or alpha.shape[0] < 2:
            raise ValueError("alpha must be a 1-D vector of length >= 2")
        if np.any(alpha <= 0):
            raise ValueError("all alpha values must be positive")
        self.alpha = alpha
        self._k = alpha.shape[0]
        # log normalising constant
        self._log_norm = sum(math.lgamma(a) for a in alpha) - math.lgamma(float(alpha.sum()))
        super().__init__(self._logpdf, dim=self._k, name=f"Dirichlet({list(alpha)})")

    def _logpdf(self, x: np.ndarray) -> float:
        x = np.asarray(x, dtype=float).reshape(-1)
        if x.shape[0] != self._k:
            return -math.inf
        if np.any(x < 0) or abs(float(x.sum()) - 1.0) > 1e-6:
            return -math.inf
        if np.any(x <= 0):  # x_i = 0 with alpha < 1 gives -inf
            # handle: if any x_i == 0 and alpha_i < 1 => -inf
            for i in range(self._k):
                if x[i] <= 0 and self.alpha[i] < 1:
                    return -math.inf
                if x[i] < 0:
                    return -math.inf
        val = 0.0
        for i in range(self._k):
            if x[i] > 0:
                val += (self.alpha[i] - 1) * math.log(x[i])
        return val - self._log_norm


class Poisson(Target):
    """Poisson distribution with rate lambda.

    .. note:: Works on the non-negative integers; the log-pdf treats
        ``x`` as a real number and uses ``x! ≈ Gamma(x+1)``.
    """

    def __init__(self, lam: float = 1.0):
        if lam <= 0:
            raise ValueError("lambda must be positive")
        self.lam = float(lam)
        super().__init__(self._logpdf, dim=1, name=f"Poisson({lam})")

    def _logpdf(self, x: np.ndarray) -> float:
        v = float(x[0]) if x.ndim else float(x)
        if v < 0:
            return -math.inf
        return v * math.log(self.lam) - self.lam - math.lgamma(v + 1)


class Bernoulli(Target):
    """Bernoulli distribution with success probability p."""

    def __init__(self, p: float = 0.5):
        if not 0 < p < 1:
            raise ValueError("p must be in (0, 1)")
        self.p = float(p)
        super().__init__(self._logpdf, dim=1, name=f"Bernoulli({p})")

    def _logpdf(self, x: np.ndarray) -> float:
        v = float(x[0]) if x.ndim else float(x)
        if v == 1:
            return math.log(self.p)
        if v == 0:
            return math.log(1.0 - self.p)
        return -math.inf


class Categorical(Target):
    """Categorical distribution over {0, 1, ..., K-1}.

    Parameters
    ----------
    probs : sequence of float
        probabilities (must sum to 1, all non-negative).
    """

    def __init__(self, probs: Sequence[float]):
        probs = np.asarray(probs, dtype=float)
        if probs.ndim != 1 or probs.shape[0] < 2:
            raise ValueError("probs must be a 1-D vector of length >= 2")
        if np.any(probs < 0):
            raise ValueError("probs must be non-negative")
        s = float(probs.sum())
        if abs(s - 1.0) > 1e-6:
            raise ValueError("probs must sum to 1")
        self.probs = probs
        self._k = probs.shape[0]
        # guard against log(0)
        self._log_probs = np.where(probs > 0, np.log(probs + 1e-300), -math.inf)
        super().__init__(self._logpdf, dim=1, name=f"Categorical({list(probs)})")

    def _logpdf(self, x: np.ndarray) -> float:
        v = float(x[0]) if x.ndim else float(x)
        idx = int(round(v))
        if idx < 0 or idx >= self._k:
            return -math.inf
        return float(self._log_probs[idx])


class TruncatedNormal(Target):
    """Truncated normal distribution on [a, b]."""

    def __init__(self, mu: float = 0.0, sigma: float = 1.0,
                 a: float = 0.0, b: float = 1.0):
        if sigma <= 0:
            raise ValueError("sigma must be positive")
        if b <= a:
            raise ValueError("b must be > a")
        self.mu = float(mu)
        self.sigma = float(sigma)
        self.a = float(a)
        self.b = float(b)
        # normalisation: Phi((b-mu)/sigma) - Phi((a-mu)/sigma)
        from math import erf, sqrt
        def Phi(z):
            return 0.5 * (1.0 + erf(z / sqrt(2.0)))
        self._log_Z = math.log(Phi((b - mu) / sigma) - Phi((a - mu) / sigma))
        self._log_base = -math.log(sigma) - 0.5 * math.log(2 * math.pi)
        super().__init__(self._logpdf, dim=1,
                         name=f"TruncatedNormal({mu},{sigma},{a},{b})")

    def _logpdf(self, x: np.ndarray) -> float:
        v = float(x[0]) if x.ndim else float(x)
        if v < self.a or v > self.b:
            return -math.inf
        z = (v - self.mu) / self.sigma
        return self._log_base - 0.5 * z * z - self._log_Z


class Logistic(Target):
    """Logistic distribution with location mu and scale s."""

    def __init__(self, mu: float = 0.0, s: float = 1.0):
        if s <= 0:
            raise ValueError("scale s must be positive")
        self.mu = float(mu)
        self.s = float(s)
        super().__init__(self._logpdf, dim=1, name=f"Logistic({mu},{s})")

    def _logpdf(self, x: np.ndarray) -> float:
        v = float(x[0]) if x.ndim else float(x)
        z = (v - self.mu) / self.s
        # log pdf = -z - 2*log(1+exp(-z)) - log(s)
        return -z - 2.0 * math.log1p(math.exp(-z)) - math.log(self.s)


class Weibull(Target):
    """Weibull distribution with shape k and scale lambda."""

    def __init__(self, k: float = 1.0, lam: float = 1.0):
        if k <= 0 or lam <= 0:
            raise ValueError("k and lambda must be positive")
        self.k = float(k)
        self.lam = float(lam)
        super().__init__(self._logpdf, dim=1, name=f"Weibull({k},{lam})")

    def _logpdf(self, x: np.ndarray) -> float:
        v = float(x[0]) if x.ndim else float(x)
        if v < 0:
            return -math.inf
        if v == 0:
            return -math.inf if self.k < 1 else (
                math.log(self.k) - self.k * math.log(self.lam)
            )
        return (math.log(self.k) - self.k * math.log(self.lam)
                + (self.k - 1) * math.log(v)
                - (v / self.lam) ** self.k)


class ChiSquared(Target):
    """Chi-squared distribution with k degrees of freedom."""

    def __init__(self, k: int = 1):
        if k < 1:
            raise ValueError("k must be >= 1")
        self.k = int(k)
        self._log_norm = (math.lgamma(k / 2.0)
                         + (k / 2.0) * math.log(2.0))
        super().__init__(self._logpdf, dim=1, name=f"ChiSquared({k})")

    def _logpdf(self, x: np.ndarray) -> float:
        v = float(x[0]) if x.ndim else float(x)
        if v <= 0:
            return -math.inf
        return ((self.k / 2.0 - 1) * math.log(v)
                - v / 2.0 - self._log_norm)


class Mixture(Target):
    """Mixture of target distributions.

    Parameters
    ----------
    components : list of Target
    weights : list of float, optional (defaults to uniform)
    """

    def __init__(self, components: List[Target], weights: Optional[List[float]] = None):
        if not components:
            raise ValueError("need at least one component")
        self.components = components
        self.dim = components[0].dim
        if any(c.dim != self.dim for c in components):
            raise ValueError("all components must have the same dimension")
        if weights is None:
            weights = [1.0 / len(components)] * len(components)
        if len(weights) != len(components):
            raise ValueError("weights/components length mismatch")
        w = np.asarray(weights, dtype=float)
        if np.any(w < 0):
            raise ValueError("weights must be non-negative")
        s = w.sum()
        if s <= 0:
            raise ValueError("weights must sum to > 0")
        self.weights = w / s
        self._log_w = np.log(self.weights)
        super().__init__(self._logpdf, dim=self.dim, name="Mixture")

    def _logpdf(self, x: np.ndarray) -> float:
        # log-sum-exp trick for numerical stability
        log_vals = np.array([self._log_w[i] + self.components[i].log_pdf(x)
                             for i in range(len(self.components))])
        # Handle case where all components return -inf (point outside all supports)
        # max(-inf, -inf) = -inf, and exp(-inf - (-inf)) = exp(nan) = nan
        m = np.max(log_vals)
        if not math.isfinite(m):
            # all components are -inf (or the max is -inf)
            return -math.inf
        return float(m + math.log(np.sum(np.exp(log_vals - m))))