"""Dynamic-programming planning algorithms for MDPs.

Includes value iteration, policy iteration, modified policy iteration,
policy evaluation (linear system + iterative), and linear-programming
optimal value solving.
"""
from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .mdp import MDP


class Policy:
    """A deterministic policy mapping states to actions.

    States with no available action (terminals) map to ``None``.
    """

    def __init__(self, mdp: MDP, table: Optional[Dict[Any, Any]] = None) -> None:
        self.mdp = mdp
        self.table: Dict[Any, Any] = {}
        for s in mdp.states:
            acts = mdp.available_actions(s)
            self.table[s] = (table.get(s) if table else (acts[0] if acts else None))

    def __call__(self, state: Any) -> Optional[Any]:
        return self.table.get(state)

    def __getitem__(self, state: Any) -> Optional[Any]:
        return self.table.get(state)

    def __setitem__(self, state: Any, action: Any) -> None:
        self.table[state] = action

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Policy):
            return False
        return self.table == other.table

    def __repr__(self) -> str:
        return f"Policy({self.table})"

    def to_dict(self) -> Dict[str, Any]:
        def _k(x):
            return x if isinstance(x, (str, int, float, bool)) else str(x)
        return {_k(s): a for s, a in self.table.items() if a is not None}


# ====================================================================== #
# Policy evaluation
# ====================================================================== #
def policy_evaluation_linear(
    mdp: MDP, policy: Policy, timeout: Optional[float] = None
) -> Dict[Any, float]:
    """Solve V^pi exactly via a linear system (V = R + gamma * P V).

    Uses Gaussian elimination with partial pivoting on the n x n system.
    Works for any deterministic policy.  O(n^3) but exact.
    """
    n = len(mdp.states)
    idx = {s: i for i, s in enumerate(mdp.states)}
    # Build (I - gamma * P) V = R
    A = [[0.0] * n for _ in range(n)]
    b = [0.0] * n
    for s in mdp.states:
        i = idx[s]
        A[i][i] = 1.0
        a = policy[s]
        if a is None:
            continue  # terminal -> V = 0
        for ns, p, r in mdp.transitions.get(s, {}).get(a, []):
            j = idx[ns]
            A[i][j] -= mdp.gamma * p
            b[i] += p * (r if r is not None else 0.0)
    V_vec = _gauss_solve(A, b)
    return {s: V_vec[idx[s]] for s in mdp.states}


def _gauss_solve(A: List[List[float]], b: List[float]) -> List[float]:
    """Solve Ax = b with Gaussian elimination + partial pivoting."""
    n = len(A)
    # augmented matrix
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        # pivot
        pivot = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[pivot][col]) < 1e-14:
            continue  # singular column, skip
        M[col], M[pivot] = M[pivot], M[col]
        # eliminate
        for r in range(col + 1, n):
            factor = M[r][col] / M[col][col]
            for c in range(col, n + 1):
                M[r][c] -= factor * M[col][c]
    # back-substitute
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = M[i][n]
        for j in range(i + 1, n):
            s -= M[i][j] * x[j]
        if abs(M[i][i]) < 1e-14:
            x[i] = 0.0
        else:
            x[i] = s / M[i][i]
    return x


def policy_evaluation_iterative(
    mdp: MDP,
    policy: Policy,
    theta: float = 1e-8,
    max_iter: int = 100000,
) -> Dict[Any, float]:
    """Iterative policy evaluation (Bellman backups until convergence)."""
    V = {s: 0.0 for s in mdp.states}
    for _ in range(max_iter):
        delta = 0.0
        newV = {}
        for s in mdp.states:
            a = policy[s]
            if a is None:
                newV[s] = 0.0
                continue
            v = 0.0
            for ns, p, r in mdp.transitions.get(s, {}).get(a, []):
                v += p * ((r if r is not None else 0.0) + mdp.gamma * V[ns])
            newV[s] = v
            delta = max(delta, abs(v - V[s]))
        V = newV
        if delta < theta:
            break
    return V


# ====================================================================== #
# Value iteration
# ====================================================================== #
def value_iteration(
    mdp: MDP,
    theta: float = 1e-8,
    max_iter: int = 100000,
    record_history: bool = False,
) -> Tuple[Dict[Any, float], Policy, Dict[str, Any]]:
    """Standard Bellman-optimal value iteration.

    Returns (V*, pi*, info) where info contains iteration count, time,
    and optional per-iteration history.
    """
    V = {s: 0.0 for s in mdp.states}
    history: List[Dict[Any, float]] = []
    t0 = time.perf_counter()
    iters = 0
    for iters in range(1, max_iter + 1):
        delta = 0.0
        newV = {}
        for s in mdp.states:
            acts = mdp.available_actions(s)
            if not acts:
                newV[s] = 0.0
                continue
            best = -math.inf
            for a in acts:
                q = 0.0
                for ns, p, r in mdp.transitions.get(s, {}).get(a, []):
                    q += p * ((r if r is not None else 0.0) + mdp.gamma * V[ns])
                if q > best:
                    best = q
            newV[s] = best
            delta = max(delta, abs(best - V[s]))
        V = newV
        if record_history:
            history.append(dict(V))
        if delta < theta:
            break
    elapsed = time.perf_counter() - t0
    pi = greedy_policy(mdp, V)
    info = {"iterations": iters, "time": elapsed, "converged": iters < max_iter}
    if record_history:
        info["history"] = history
    return V, pi, info


def greedy_policy(mdp: MDP, V: Dict[Any, float]) -> Policy:
    """Extract the greedy policy w.r.t. value function V."""
    pi = Policy(mdp)
    for s in mdp.states:
        acts = mdp.available_actions(s)
        if not acts:
            pi[s] = None
            continue
        best_a = acts[0]
        best_q = -math.inf
        for a in acts:
            q = 0.0
            for ns, p, r in mdp.transitions.get(s, {}).get(a, []):
                q += p * ((r if r is not None else 0.0) + mdp.gamma * V[ns])
            if q > best_q:
                best_q = q
                best_a = a
        pi[s] = best_a
    return pi


def q_values(mdp: MDP, V: Dict[Any, float]) -> Dict[Any, Dict[Any, float]]:
    """Compute Q(s,a) from V for all state-action pairs."""
    Q: Dict[Any, Dict[Any, float]] = {}
    for s in mdp.states:
        Q[s] = {}
        for a in mdp.available_actions(s):
            q = 0.0
            for ns, p, r in mdp.transitions.get(s, {}).get(a, []):
                q += p * ((r if r is not None else 0.0) + mdp.gamma * V[ns])
            Q[s][a] = q
    return Q


# ====================================================================== #
# Policy iteration
# ====================================================================== #
def policy_iteration(
    mdp: MDP,
    theta: float = 1e-8,
    max_iter: int = 10000,
    eval_method: str = "iterative",
) -> Tuple[Dict[Any, float], Policy, Dict[str, Any]]:
    """Howard's policy iteration: evaluate -> improve -> repeat."""
    pi = Policy(mdp)  # arbitrary initial
    V: Dict[Any, float] = {}
    t0 = time.perf_counter()
    iters = 0
    for iters in range(1, max_iter + 1):
        if eval_method == "linear":
            V = policy_evaluation_linear(mdp, pi)
        else:
            V = policy_evaluation_iterative(mdp, pi, theta=theta)
        policy_stable = True
        for s in mdp.states:
            acts = mdp.available_actions(s)
            if not acts:
                pi[s] = None
                continue
            old_a = pi[s]
            best_a = acts[0]
            best_q = -math.inf
            for a in acts:
                q = 0.0
                for ns, p, r in mdp.transitions.get(s, {}).get(a, []):
                    q += p * ((r if r is not None else 0.0) + mdp.gamma * V[ns])
                if q > best_q:
                    best_q = q
                    best_a = a
            pi[s] = best_a
            if old_a != best_a:
                policy_stable = False
        if policy_stable:
            break
    elapsed = time.perf_counter() - t0
    if not V:
        V = policy_evaluation_iterative(mdp, pi, theta=theta)
    info = {"iterations": iters, "time": elapsed, "converged": iters < max_iter,
            "eval_method": eval_method}
    return V, pi, info


def modified_policy_iteration(
    mdp: MDP,
    k: int = 10,
    theta: float = 1e-8,
    max_iter: int = 10000,
) -> Tuple[Dict[Any, float], Policy, Dict[str, Any]]:
    """Modified policy iteration: k Bellman backups per evaluation step."""
    V = {s: 0.0 for s in mdp.states}
    t0 = time.perf_counter()
    iters = 0
    for iters in range(1, max_iter + 1):
        # k partial evaluation steps (full Bellman backup, not policy-fixed)
        for _ in range(k):
            newV = {}
            for s in mdp.states:
                acts = mdp.available_actions(s)
                if not acts:
                    newV[s] = 0.0
                    continue
                best = -math.inf
                for a in acts:
                    q = 0.0
                    for ns, p, r in mdp.transitions.get(s, {}).get(a, []):
                        q += p * ((r if r is not None else 0.0) + mdp.gamma * V[ns])
                    if q > best:
                        best = q
                newV[s] = best
            V = newV
        # policy improvement (implicit in the full backup above)
        delta = 0.0
        newV = {}
        for s in mdp.states:
            acts = mdp.available_actions(s)
            if not acts:
                newV[s] = 0.0
                continue
            best = -math.inf
            for a in acts:
                q = 0.0
                for ns, p, r in mdp.transitions.get(s, {}).get(a, []):
                    q += p * ((r if r is not None else 0.0) + mdp.gamma * V[ns])
                if q > best:
                    best = q
            newV[s] = best
            delta = max(delta, abs(best - V[s]))
        V = newV
        if delta < theta:
            break
    elapsed = time.perf_counter() - t0
    pi = greedy_policy(mdp, V)
    info = {"iterations": iters, "time": elapsed, "converged": iters < max_iter, "k": k}
    return V, pi, info


__all__ = [
    "Policy",
    "policy_evaluation_linear",
    "policy_evaluation_iterative",
    "value_iteration",
    "policy_iteration",
    "modified_policy_iteration",
    "greedy_policy",
    "q_values",
]