"""Hidden Markov Model core data structure (pure Python, no dependencies)."""

from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Sequence, Tuple


def _normalise_row(row: Sequence[float]) -> List[float]:
    """Normalise a list of floats so it sums to 1.0 (all-zero → uniform)."""
    s = sum(row)
    if s <= 0:
        n = len(row)
        return [1.0 / n] * n if n else []
    return [v / s for v in row]


def _normalise_rows(mat: Sequence[Sequence[float]]) -> List[List[float]]:
    return [_normalise_row(r) for r in mat]


def _validate_non_negative(name: str, mat: Sequence[Sequence[float]], tol: float = 1e-9) -> None:
    """Check that all entries are non-negative (values > 1 are allowed since
    rows are normalised on construction — callers may pass un-normalised weights)."""
    for i, row in enumerate(mat):
        for j, v in enumerate(row):
            if v < -tol:
                raise ValueError(f"{name}[{i}][{j}] is negative ({v})")


def _validate_vector(name: str, vec: Sequence[float], tol: float = 1e-9) -> None:
    for i, v in enumerate(vec):
        if v < -tol:
            raise ValueError(f"{name}[{i}] is negative ({v})")


class HMM:
    """A discrete Hidden Markov Model.

    Parameters
    ----------
    states : Sequence[str]
        Names of the hidden states.
    symbols : Sequence[str]
        Names of the observable emission symbols.
    A : Sequence[Sequence[float]], shape (N, N)
        State transition probability matrix. ``A[i][j]`` is the probability of
        transitioning from state *i* to state *j*.
    B : Sequence[Sequence[float]], shape (N, M)
        Emission probability matrix. ``B[i][k]`` is the probability of emitting
        symbol *k* while in state *i*.
    pi : Sequence[float], shape (N,)
        Initial state distribution. ``pi[i]`` is the probability of starting in
        state *i*.

    Notes
    -----
    All probability rows are normalised on construction so the caller does not
    need to be overly precise.  Validation raises ``ValueError`` for shapes that
    cannot be reconciled with ``states`` / ``symbols``.
    """

    def __init__(
        self,
        states: Sequence[str],
        symbols: Sequence[str],
        A: Sequence[Sequence[float]],
        B: Sequence[Sequence[float]],
        pi: Sequence[float],
    ) -> None:
        self.states: List[str] = list(states)
        self.symbols: List[str] = list(symbols)
        self.n_states: int = len(self.states)
        self.n_symbols: int = len(self.symbols)

        self._state_index: Dict[str, int] = {s: i for i, s in enumerate(self.states)}
        self._symbol_index: Dict[str, int] = {s: i for i, s in enumerate(self.symbols)}

        self._validate_shapes(A, B, pi)
        _validate_non_negative("A", A)
        _validate_non_negative("B", B)
        _validate_vector("pi", pi)

        self.A: List[List[float]] = _normalise_rows(A)
        self.B: List[List[float]] = _normalise_rows(B)
        self.pi: List[float] = _normalise_row(pi)

        # cached log-space versions (built lazily)
        self._log_A: Optional[List[List[float]]] = None
        self._log_B: Optional[List[List[float]]] = None
        self._log_pi: Optional[List[float]] = None

    # ------------------------------------------------------------------ utils
    def _validate_shapes(self, A, B, pi) -> None:
        if len(A) != self.n_states:
            raise ValueError(f"A must have {self.n_states} rows, got {len(A)}")
        for i, row in enumerate(A):
            if len(row) != self.n_states:
                raise ValueError(f"A[{i}] must have {self.n_states} cols, got {len(row)}")
        if len(B) != self.n_states:
            raise ValueError(f"B must have {self.n_states} rows, got {len(B)}")
        for i, row in enumerate(B):
            if len(row) != self.n_symbols:
                raise ValueError(f"B[{i}] must have {self.n_symbols} cols, got {len(row)}")
        if len(pi) != self.n_states:
            raise ValueError(f"pi must have {self.n_states} entries, got {len(pi)}")

    # ----------------------------------------------------------- log caching
    @staticmethod
    def _safe_log(x: float) -> float:
        return math.log(x) if x > 0 else -math.inf

    def _log_matrix(self, mat: Sequence[Sequence[float]]) -> List[List[float]]:
        return [[self._safe_log(v) for v in row] for row in mat]

    @property
    def log_A(self) -> List[List[float]]:
        if self._log_A is None:
            self._log_A = self._log_matrix(self.A)
        return self._log_A

    @property
    def log_B(self) -> List[List[float]]:
        if self._log_B is None:
            self._log_B = self._log_matrix(self.B)
        return self._log_B

    @property
    def log_pi(self) -> List[float]:
        if self._log_pi is None:
            self._log_pi = [self._safe_log(v) for v in self.pi]
        return self._log_pi

    def reset_log_cache(self) -> None:
        """Invalidate cached log-space matrices (call after manual mutation)."""
        self._log_A = None
        self._log_B = None
        self._log_pi = None

    # ------------------------------------------------------------- accessors
    def state_index(self, name: str) -> int:
        try:
            return self._state_index[name]
        except KeyError:
            raise ValueError(f"unknown state: {name!r}") from None

    def symbol_index(self, name: str) -> int:
        try:
            return self._symbol_index[name]
        except KeyError:
            raise ValueError(f"unknown symbol: {name!r}") from None

    def observation_sequence(self, symbols: Sequence[str]) -> List[int]:
        """Convert a list of symbol names into integer indices."""
        return [self.symbol_index(s) for s in symbols]

    # ------------------------------------------------------------- factories
    @classmethod
    def random(
        cls,
        states: Sequence[str],
        symbols: Sequence[str],
        rng: Optional[random.Random] = None,
        seed: Optional[int] = None,
    ) -> "HMM":
        """Create an HMM with randomly initialised (but valid) parameters."""
        if rng is None:
            rng = random.Random(seed)
        n, m = len(states), len(symbols)

        def rand_row(k: int) -> List[float]:
            vals = [rng.random() for _ in range(k)]
            s = sum(vals)
            return [v / s for v in vals]

        A = [rand_row(n) for _ in range(n)]
        B = [rand_row(m) for _ in range(n)]
        pi = rand_row(n)
        return cls(states, symbols, A, B, pi)

    @classmethod
    def uniform(cls, states: Sequence[str], symbols: Sequence[str]) -> "HMM":
        """Create an HMM with uniform transition / emission / initial probs."""
        n, m = len(states), len(symbols)
        A = [[1.0 / n] * n for _ in range(n)]
        B = [[1.0 / m] * m for _ in range(n)]
        pi = [1.0 / n] * n
        return cls(states, symbols, A, B, pi)

    # ------------------------------------------------------------- mutation
    def set_parameters(
        self,
        A: Optional[Sequence[Sequence[float]]] = None,
        B: Optional[Sequence[Sequence[float]]] = None,
        pi: Optional[Sequence[float]] = None,
    ) -> None:
        """Replace one or more parameter matrices, with validation + normalisation."""
        if A is not None:
            self._validate_shapes(A, self.B, self.pi)
            _validate_non_negative("A", A)
            self.A = _normalise_rows(A)
        if B is not None:
            self._validate_shapes(self.A, B, self.pi)
            _validate_non_negative("B", B)
            self.B = _normalise_rows(B)
        if pi is not None:
            self._validate_shapes(self.A, self.B, pi)
            _validate_vector("pi", pi)
            self.pi = _normalise_row(pi)
        self.reset_log_cache()

    # ------------------------------------------------------------- repr
    def __repr__(self) -> str:
        return (
            f"HMM(states={self.states}, symbols={self.symbols}, "
            f"n_states={self.n_states}, n_symbols={self.n_symbols})"
        )

    # ----------------------------------------------------------- equality
    def parameters_almost_equal(self, other: "HMM", tol: float = 1e-6) -> bool:
        """Compare parameters with a tolerance (order of states/symbols matters)."""
        if self.states != other.states or self.symbols != other.symbols:
            return False
        for i in range(self.n_states):
            for j in range(self.n_states):
                if abs(self.A[i][j] - other.A[i][j]) > tol:
                    return False
            for k in range(self.n_symbols):
                if abs(self.B[i][k] - other.B[i][k]) > tol:
                    return False
            if abs(self.pi[i] - other.pi[i]) > tol:
                return False
        return True