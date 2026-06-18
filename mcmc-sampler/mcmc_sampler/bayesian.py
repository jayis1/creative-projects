"""
Bayesian modelling framework — define posteriors as prior × likelihood
and sample from them with any of the library's samplers.

The :class:`BayesianModel` class makes it easy to set up inference
problems without manually writing log-posterior functions::

    model = BayesianModel(dim=2)
    model.set_prior(lambda w: Normal(0, 5).log_pdf([w[0]]) + Normal(0, 5).log_pdf([w[1]]))
    model.set_likelihood(lambda w: np.sum(y * (X @ w) - np.logaddexp(0, X @ w)))
    target = model.as_target(name="my-posterior")

    sampler = NUTS(target, target_accept=0.8, rng=...)
    trace = sampler.sample([0, 0], n_samples=5000, burn=2000)
"""

from __future__ import annotations

import math
from typing import Callable, Optional, Sequence, Union

import numpy as np

from .distributions import Target


Array = Union[np.ndarray, Sequence[float]]

# Type for a log-density function
LogDensityFn = Callable[[Array], float]


class BayesianModel:
    """Composable Bayesian model: posterior ∝ prior × likelihood.

    Parameters
    ----------
    dim : int
        Dimensionality of the parameter vector.
    prior : callable, optional
        ``prior(theta) -> log p(theta)``.  Defaults to a flat
        (improper) prior returning 0.
    likelihood : callable, optional
        ``likelihood(theta) -> log p(data | theta)``.
    """

    def __init__(self, dim: int,
                 prior: Optional[LogDensityFn] = None,
                 likelihood: Optional[LogDensityFn] = None):
        if dim < 1:
            raise ValueError("dim must be >= 1")
        self.dim = int(dim)
        self.prior: LogDensityFn = prior or (lambda theta: 0.0)
        self.likelihood: LogDensityFn = likelihood or (lambda theta: 0.0)
        self._data: Optional[np.ndarray] = None

    def set_prior(self, fn: LogDensityFn) -> "BayesianModel":
        """Set the log-prior function.  Returns self for chaining."""
        self.prior = fn
        return self

    def set_likelihood(self, fn: LogDensityFn) -> "BayesianModel":
        """Set the log-likelihood function.  Returns self for chaining."""
        self.likelihood = fn
        return self

    def log_posterior(self, theta: Array) -> float:
        """Compute log p(theta | data) = log_prior + log_likelihood (unnormalised)."""
        theta = np.asarray(theta, dtype=float).reshape(-1)
        if theta.shape[0] != self.dim:
            raise ValueError(
                f"theta has dim {theta.shape[0]}, expected {self.dim}")
        lp = float(self.prior(theta))
        ll = float(self.likelihood(theta))
        result = lp + ll
        # Guard against NaN from inf - inf
        if math.isnan(result):
            return -math.inf
        return result

    def as_target(self, name: str = "bayesian-posterior") -> Target:
        """Wrap this model as a :class:`Target` for use with any sampler."""
        return Target(self.log_posterior, dim=self.dim, name=name)

    # -- convenience constructors ------------------------------------- #

    @classmethod
    def linear_regression(cls, X: np.ndarray, y: np.ndarray,
                         prior_std: float = 10.0,
                         noise_std: Optional[float] = None
                         ) -> "BayesianModel":
        """Create a Bayesian linear regression model.

        Parameters
        ----------
        X : array of shape (n, d)
            Design matrix.
        y : array of shape (n,)
            Response vector.
        prior_std : float
            Standard deviation of the Gaussian prior on each weight.
        noise_std : float, optional
            Known noise standard deviation.  If None, a noise precision
            parameter is added (so dim = d + 1).

        Returns
        -------
        BayesianModel
        """
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()
        n, d = X.shape
        from .distributions import Normal

        if noise_std is None:
            dim = d + 1
            # last parameter is log(noise_std) for positivity
            def prior_fn(theta):
                p = 0.0
                for i in range(d):
                    p += Normal(0, prior_std).log_pdf([theta[i]])
                # weak prior on log_sigma
                p += Normal(0, 2).log_pdf([theta[d]])
                return p

            def likelihood_fn(theta):
                w = theta[:d]
                sigma = math.exp(theta[d])
                resid = y - X @ w
                return float(-0.5 * np.sum(resid ** 2) / sigma ** 2
                             - n * math.log(sigma)
                             - 0.5 * n * math.log(2 * math.pi))
        else:
            dim = d
            sigma = float(noise_std)

            def prior_fn(theta):
                return float(sum(
                    Normal(0, prior_std).log_pdf([theta[i]])
                    for i in range(d)))

            def likelihood_fn(theta):
                w = theta[:d]
                resid = y - X @ w
                return float(-0.5 * np.sum(resid ** 2) / sigma ** 2
                             - 0.5 * n * math.log(2 * math.pi * sigma ** 2))

        model = cls(dim=dim, prior=prior_fn, likelihood=likelihood_fn)
        model._data = (X, y)
        return model

    @classmethod
    def logistic_regression(cls, X: np.ndarray, y: np.ndarray,
                            prior_std: float = 5.0) -> "BayesianModel":
        """Create a Bayesian logistic regression model.

        Parameters
        ----------
        X : array of shape (n, d)
            Design matrix (without intercept column — it is added
            automatically).
        y : array of shape (n,)
            Binary labels (0 or 1).
        prior_std : float
            Standard deviation of the Gaussian prior on each weight.

        Returns
        -------
        BayesianModel
        """
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()
        n, d = X.shape
        # add intercept column
        X_aug = np.column_stack([np.ones(n), X])
        dim = d + 1
        from .distributions import Normal

        def prior_fn(theta):
            return float(sum(
                Normal(0, prior_std).log_pdf([theta[i]])
                for i in range(dim)))

        def likelihood_fn(theta):
            logits = X_aug @ theta
            return float(np.sum(y * logits - np.logaddexp(0, logits)))

        model = cls(dim=dim, prior=prior_fn, likelihood=likelihood_fn)
        model._data = (X_aug, y)
        return model

    def __repr__(self) -> str:  # pragma: no cover
        return f"BayesianModel(dim={self.dim})"