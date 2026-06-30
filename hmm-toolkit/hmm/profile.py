"""Profile HMMs for biological sequence alignment.

A Profile HMM represents a multiple sequence alignment (MSA) as an HMM with
three classes of states:

* **Match** (M) — aligned consensus columns
* **Insert** (I) — insertions relative to the consensus
* **Delete** (D) — gaps / deletions in the consensus

This module provides:

* ``ProfileHMM`` — construction from a multiple sequence alignment
* Forward / Backward / Viterbi specialised for the profile architecture
* Parameter training via Baum-Welch or maximum-likelihood from the MSA
* Log-odds scoring against a background null model
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Sequence, Tuple


class ProfileHMM:
    """A Profile HMM for a multiple sequence alignment.

    Parameters
    ----------
    alphabet : Sequence[str]
        The character alphabet (e.g. amino-acid or DNA letters).
    match_columns : List[int]
        Indices of columns in the original MSA that are *match* columns
        (non-gap majority).  Length determines the number of match states.
    A, B, pi : optional
        Pre-computed transition / emission / initial probabilities.  If
        ``None`` they are estimated from the alignment.
    """

    def __init__(
        self,
        alphabet: Sequence[str],
        match_columns: Sequence[int],
        A: Optional[Sequence[Sequence[float]]] = None,
        B: Optional[Sequence[Sequence[float]]] = None,
        pi: Optional[Sequence[float]] = None,
        pseudocount: float = 1.0,
    ) -> None:
        self.alphabet: List[str] = list(alphabet)
        self.n_symbols: int = len(self.alphabet)
        self.match_columns: List[int] = list(match_columns)
        self.n_matches: int = len(self.match_columns)
        if self.n_matches == 0:
            raise ValueError("ProfileHMM requires at least one match column")
        if len(set(self.alphabet)) != self.n_symbols:
            raise ValueError("Duplicate alphabet symbols are not allowed")
        self._sym_idx: Dict[str, int] = {s: i for i, s in enumerate(self.alphabet)}
        self.pseudocount: float = pseudocount

        # State layout: M_1..M_L, I_1..I_L, D_1..D_L  (0-indexed internally)
        # plus a begin (B) and end (E) — we fold begin into pi and end into A.
        self.n_states: int = 3 * self.n_matches
        self._build_state_labels()

        if A is not None and B is not None and pi is not None:
            self.A = [list(r) for r in A]
            self.B = [list(r) for r in B]
            self.pi = list(pi)
        else:
            # will be set by ``estimate_from_alignment``
            self.A = [[0.0] * self.n_states for _ in range(self.n_states)]
            self.B = [[0.0] * self.n_symbols for _ in range(self.n_states)]
            self.pi = [0.0] * self.n_states

        self._log_A: Optional[List[List[float]]] = None
        self._log_B: Optional[List[List[float]]] = None
        self._log_pi: Optional[List[float]] = None

    # ------------------------------------------------------------------
    # State indexing helpers
    # ------------------------------------------------------------------
    def _build_state_labels(self) -> None:
        """Build labels like M0, I0, D0, M1, I1, D1, ..."""
        L = self.n_matches
        self.state_labels: List[str] = []
        for i in range(L):
            self.state_labels.append(f"M{i}")
            self.state_labels.append(f"I{i}")
            self.state_labels.append(f"D{i}")
        self._state_index: Dict[str, int] = {s: i for i, s in enumerate(self.state_labels)}

    def _mi(self, i: int) -> int:
        """Index of match state M_i."""
        return 3 * i

    def _ii(self, i: int) -> int:
        """Index of insert state I_i."""
        return 3 * i + 1

    def _di(self, i: int) -> int:
        """Index of delete state D_i."""
        return 3 * i + 2

    # ------------------------------------------------------------------
    # Estimation from a multiple sequence alignment
    # ------------------------------------------------------------------
    def estimate_from_alignment(self, alignment: Sequence[str]) -> None:
        """Estimate A, B, and pi from an MSA (strings of equal length).

        Columns in ``self.match_columns`` are consensus columns.  All other
        columns are insert columns.  Gap characters ``-`` or ``.`` denote
        deletions.
        """
        L = self.n_matches
        pc = self.pseudocount
        alphabet_set = set(self.alphabet)

        # Counters
        # transitions: for each match-step we track M→M, M→I, M→D, I→M, I→I, D→M, D→I, D→D
        # We simplify by counting per (from-class, to-class) at each position.
        # state index helper: we'll accumulate counts in full n_states×n_states

        trans_counts = [[pc] * self.n_states for _ in range(self.n_states)]
        emit_counts_M = [[pc] * self.n_symbols for _ in range(L)]
        emit_counts_I = [[pc] * self.n_symbols for _ in range(L)]
        init_counts = [pc] * self.n_states

        match_cols = self.match_columns
        all_cols = list(range(len(alignment[0]))) if alignment else []
        # Determine insert columns (all non-match)
        insert_cols = [c for c in all_cols if c not in set(match_cols)]

        for seq in alignment:
            # Walk through the alignment column-by-column, classifying each
            # position as match or insert.
            # We track current "state class": start before column 0.
            # Simplified path encoding:
            #   For each match column i:
            #     if seq[col] is a gap → D state
            #     else → M state (and emissions counted)
            #   For insert columns between match i and match i+1:
            #     collect non-gap chars → I state i

            prev_state: Optional[str] = None  # 'M', 'I', 'D', or None (begin)

            # We iterate through columns in order, grouping inserts.
            mi = 0  # match index counter
            col_iter = iter(all_cols)
            # Build per-position classification
            classified: List[Tuple[str, int, Optional[str]]] = []
            # (class, match_index, symbol_or_None)
            for col in all_cols:
                ch = seq[col]
                if col in set(match_cols):
                    idx = match_cols.index(col)
                    if ch in alphabet_set:
                        classified.append(("M", idx, ch))
                    else:
                        classified.append(("D", idx, None))
                else:
                    # insert column — find which match index it precedes
                    # (the next match col after this one)
                    next_mi = None
                    for mc in match_cols:
                        if mc > col:
                            next_mi = match_cols.index(mc)
                            break
                    if next_mi is None:
                        next_mi = L - 1  # trailing inserts belong to last
                    if ch in alphabet_set:
                        classified.append(("I", next_mi, ch))
                    else:
                        # gap in insert column — skip
                        pass

            # Now walk classified list and count transitions + emissions
            first_state = True
            for cls, idx, sym in classified:
                state_label = f"{cls}{idx}"
                si = self._state_index[state_label]
                if first_state:
                    init_counts[si] += 1
                    first_state = False
                # emission
                if cls == "M" and sym is not None:
                    emit_counts_M[idx][self._sym_idx[sym]] += 1
                elif cls == "I" and sym is not None:
                    emit_counts_I[idx][self._sym_idx[sym]] += 1
                # transition from prev
                # (handled below in second pass)
                classified_with_si = classified  # keep ref

            # Second pass: count transitions
            for k in range(1, len(classified)):
                prev_label = f"{classified[k-1][0]}{classified[k-1][1]}"
                curr_label = f"{classified[k][0]}{classified[k][1]}"
                prev_si = self._state_index[prev_label]
                curr_si = self._state_index[curr_label]
                trans_counts[prev_si][curr_si] += 1

        # Normalise
        self.pi = self._norm(init_counts)
        # Transitions
        self.A = [self._norm(row) for row in trans_counts]
        # Emissions: M states emit, D states don't (uniform), I states emit
        self.B = [[0.0] * self.n_symbols for _ in range(self.n_states)]
        for i in range(L):
            mi = self._mi(i)
            ii = self._ii(i)
            di = self._di(i)
            self.B[mi] = self._norm(emit_counts_M[i])
            self.B[ii] = self._norm(emit_counts_I[i])
            # D states have no emission — set uniform so they don't break forward
            self.B[di] = [1.0 / self.n_symbols] * self.n_symbols
        self._log_A = None
        self._log_B = None
        self._log_pi = None

    @staticmethod
    def _norm(vec: Sequence[float]) -> List[float]:
        s = sum(vec)
        if s <= 0:
            n = len(vec)
            return [1.0 / n] * n if n else []
        return [v / s for v in vec]

    # ------------------------------------------------------------------
    # Log caches
    # ------------------------------------------------------------------
    @staticmethod
    def _safe_log(x: float) -> float:
        return math.log(x) if x > 0 else -math.inf

    @property
    def log_A(self) -> List[List[float]]:
        if self._log_A is None:
            self._log_A = [[self._safe_log(v) for v in row] for row in self.A]
        return self._log_A

    @property
    def log_B(self) -> List[List[float]]:
        if self._log_B is None:
            self._log_B = [[self._safe_log(v) for v in row] for row in self.B]
        return self._log_B

    @property
    def log_pi(self) -> List[float]:
        if self._log_pi is None:
            self._log_pi = [self._safe_log(v) for v in self.pi]
        return self._log_pi

    def reset_log_cache(self) -> None:
        self._log_A = None
        self._log_B = None
        self._log_pi = None

    # ------------------------------------------------------------------
    # Forward / Backward / Viterbi (reuse generic algorithms but on the
    # profile HMM's own matrices)
    # ------------------------------------------------------------------
    def _obs_to_indices(self, obs: Sequence[str]) -> List[int]:
        return [self._sym_idx[c] for c in obs]

    def forward(self, obs: Sequence[str]) -> Tuple[List[List[float]], List[float], float]:
        from .algorithms import forward as _fwd
        return _fwd(_ProfileWrapper(self), self._obs_to_indices(obs))

    def backward(self, obs: Sequence[str], scales: Optional[Sequence[float]] = None) -> List[List[float]]:
        from .algorithms import backward as _bwd
        return _bwd(_ProfileWrapper(self), self._obs_to_indices(obs), scales)

    def viterbi(self, obs: Sequence[str]) -> Tuple[List[int], float]:
        from .algorithms import viterbi as _vit
        return _vit(_ProfileWrapper(self), self._obs_to_indices(obs))

    def log_likelihood(self, obs: Sequence[str]) -> float:
        _, _, ll = self.forward(obs)
        return ll

    # ------------------------------------------------------------------
    # Log-odds scoring
    # ------------------------------------------------------------------
    def log_odds_score(self, obs: Sequence[str], bg_freqs: Optional[Sequence[float]] = None) -> float:
        """Compute the log-odds score of a sequence against the profile.

        ``bg_freqs`` is the background (null) emission distribution.  If
        ``None``, a uniform distribution over the alphabet is used.
        """
        if bg_freqs is None:
            bg = [1.0 / self.n_symbols] * self.n_symbols
        else:
            bg = list(bg_freqs)
        log_bg = [self._safe_log(p) for p in bg]
        ll_profile = self.log_likelihood(obs)
        log_bg_ll = sum(log_bg[self._sym_idx[c]] for c in obs)
        return ll_profile - log_bg_ll

    # ------------------------------------------------------------------
    # Match-column selection helper
    # ------------------------------------------------------------------
    @staticmethod
    def identify_match_columns(alignment: Sequence[str], threshold: float = 0.5) -> List[int]:
        """Identify match columns from an MSA.

        A column is a match column if the fraction of non-gap characters
        is >= ``threshold``.
        """
        if not alignment:
            return []
        n_cols = len(alignment[0])
        match_cols: List[int] = []
        for col in range(n_cols):
            non_gap = sum(1 for seq in alignment if seq[col] not in ("-", ".", "~"))
            if non_gap / len(alignment) >= threshold:
                match_cols.append(col)
        return match_cols

    def __repr__(self) -> str:
        return (f"ProfileHMM(alphabet={self.alphabet}, "
                f"n_matches={self.n_matches}, n_states={self.n_states})")


class _ProfileWrapper:
    """Adapter so that ``hmm.algorithms`` functions work on a ProfileHMM."""

    __slots__ = ("_ph",)

    def __init__(self, ph: ProfileHMM) -> None:
        self._ph = ph

    @property
    def n_states(self) -> int:
        return self._ph.n_states

    @property
    def n_symbols(self) -> int:
        return self._ph.n_symbols

    @property
    def A(self) -> List[List[float]]:
        return self._ph.A

    @property
    def B(self) -> List[List[float]]:
        return self._ph.B

    @property
    def pi(self) -> List[float]:
        return self._ph.pi

    @property
    def log_A(self) -> List[List[float]]:
        return self._ph.log_A

    @property
    def log_B(self) -> List[List[float]]:
        return self._ph.log_B

    @property
    def log_pi(self) -> List[float]:
        return self._ph.log_pi


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_profile_hmm(alignment: Sequence[str], alphabet: Sequence[str],
                      threshold: float = 0.5, pseudocount: float = 1.0) -> ProfileHMM:
    """Build a Profile HMM from a multiple sequence alignment.

    Parameters
    ----------
    alignment : list of str
        Sequences of equal length (the MSA).  Gap chars: ``-``, ``.``, ``~``.
    alphabet : list of str
        Valid characters (e.g. ``"ACGT"`` for DNA).
    threshold : float
        Fraction of non-gap residues required for a column to be a match column.
    pseudocount : float
        Additive smoothing for parameter estimation.
    """
    match_cols = ProfileHMM.identify_match_columns(alignment, threshold)
    ph = ProfileHMM(alphabet, match_cols, pseudocount=pseudocount)
    ph.estimate_from_alignment(alignment)
    return ph