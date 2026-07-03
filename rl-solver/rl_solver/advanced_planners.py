"""Advanced dynamic-programming and planning algorithms.

Includes:
* Linear-programming optimal value solver (pure-Python Simplex)
* Real-Time Dynamic Programming (RTDP) — asynchronous value iteration
  guided by on-policy trials
* Prioritized Sweeping — prioritized asynchronous backups via a priority
  queue keyed on Bellman error magnitude
* Gauss-Seidel value iteration — in-place (asynchronous) sweeps that
  often converge in fewer iterations than synchronous VI

All planners return ``(V, pi, info)`` consistent with the core
:mod:`rl_solver.planners` interface.
"""
from __future__ import annotations

import heapq
import math
import random
import time
from typing import Any, Dict, List, Optional, Tuple

from .mdp import MDP
from .planners import Policy, greedy_policy


# ====================================================================== #
# Linear-programming optimal value solver
# ====================================================================== #
def _simplex_minimize(
    c: List[float],
    A: List[List[float]],
    b: List[float],
) -> Optional[List[float]]:
    """Solve ``minimize c·x  s.t.  A x ≤ b, x ≥ 0`` via Simplex.

    Returns the optimal vertex, or *None* if unbounded/infeasible.
    Handles negative right-hand sides via the Big-M method.
    """
    m = len(b)
    n = len(c)
    BIG_M = 1e6

    n_slack = m
    n_artif = 0
    artif_rows: List[int] = []
    for i in range(m):
        if b[i] < -1e-12:
            n_artif += 1
            artif_rows.append(i)

    total_cols = n + n_slack + n_artif
    tableau: List[List[float]] = []
    artif_col_start = n + n_slack
    artif_idx = 0
    basis: List[int] = []

    for i in range(m):
        row = [0.0] * (total_cols + 1)
        if b[i] >= -1e-12:
            for j in range(n):
                row[j] = A[i][j]
            row[n + i] = 1.0
            row[-1] = b[i]
            basis.append(n + i)
        else:
            for j in range(n):
                row[j] = -A[i][j]
            row[n + i] = -1.0
            ac = artif_col_start + artif_idx
            row[ac] = 1.0
            row[-1] = -b[i]
            basis.append(ac)
            artif_idx += 1
        tableau.append(row)

    # Objective: minimize c·x + M * sum(artificials)
    obj = [0.0] * (total_cols + 1)
    for j in range(n):
        obj[j] = c[j]
    for k in range(n_artif):
        obj[artif_col_start + k] = BIG_M
    tableau.append(obj)

    # Reduce objective: subtract M * artificial rows
    for idx in range(n_artif):
        ac = artif_col_start + idx
        for i in range(m):
            if basis[i] == ac:
                factor = obj[ac]
                for j in range(len(obj)):
                    obj[j] -= factor * tableau[i][j]
                break

    for _iteration in range(5000):
        obj_row = tableau[-1]
        # For minimization: entering = most negative reduced cost
        entering = -1
        best = -1e-9
        for j in range(total_cols):
            if j >= artif_col_start:
                continue
            if obj_row[j] < best:
                best = obj_row[j]
                entering = j
        if entering == -1:
            break
        leaving = -1
        min_ratio = math.inf
        for i in range(m):
            if tableau[i][entering] > 1e-12:
                ratio = tableau[i][-1] / tableau[i][entering]
                if ratio < min_ratio - 1e-12:
                    min_ratio = ratio
                    leaving = i
        if leaving == -1:
            return None
        pv = tableau[leaving][entering]
        for j in range(len(tableau[leaving])):
            tableau[leaving][j] /= pv
        for i in range(m + 1):
            if i == leaving:
                continue
            factor = tableau[i][entering]
            if abs(factor) < 1e-15:
                continue
            for j in range(len(tableau[i])):
                tableau[i][j] -= factor * tableau[leaving][j]
        basis[leaving] = entering

    for idx in range(n_artif):
        ac = artif_col_start + idx
        for i in range(m):
            if basis[i] == ac and tableau[i][-1] > 1e-6:
                return None

    x = [0.0] * total_cols
    for i in range(m):
        x[basis[i]] = tableau[i][-1]
    return x[:n]


def linear_programming_solve(
    mdp: MDP,
    timeout: Optional[float] = None,
) -> Tuple[Dict[Any, float], Policy, Dict[str, Any]]:
    """Solve an MDP via linear programming.

    Minimise ``sum_s V(s)`` subject to:
        V(s) ≥ Σ_s' P(s'|s,a) [R + γ V(s')]   for all s, a

    Since the simplex requires non-negative variables but V(s) can be
    negative, we shift each value by a constant ``L`` (a known lower
    bound on V*) so that ``V(s) + L ≥ 0``.  We use
    ``L = R_min / (1−γ)`` (the worst-case discounted return).
    """
    t0 = time.perf_counter()
    idx = {s: i for i, s in enumerate(mdp.states)}
    n = len(mdp.states)
    # Compute lower bound L: worst possible discounted return
    r_min = 0.0
    for s in mdp.states:
        for a in mdp.available_actions(s):
            for ns, p, r in mdp.transitions.get(s, {}).get(a, []):
                if r is not None:
                    r_min = min(r_min, r)
    L = abs(r_min) / max(1e-9, 1.0 - mdp.gamma) if r_min < 0 else 0.0
    # Now w_s = V(s) + L >= 0, and we minimise sum w_s (= sum V + n*L)
    # Constraint: V(s) >= R + gamma * sum P V(ns)
    # =>  w(s) - L >= R + gamma * sum P (w(ns) - L)
    # =>  w(s) >= R + L + gamma * sum P w(ns) - gamma * L
    # =>  w(s) - gamma * sum P w(ns) >= R + L(1 - gamma * sum P)
    # Since sum P = 1: w(s) - gamma * sum P w(ns) >= R + L(1 - gamma)
    # Convert to <=: -w(s) + gamma * sum P w(ns) <= -(R + L(1-gamma))
    A: List[List[float]] = []
    b: List[float] = []
    bound = L * (1.0 - mdp.gamma)
    # Add terminal state constraints: V(terminal) = 0, i.e., w(terminal) = L
    for s in mdp.states:
        if mdp.is_terminal(s):
            si = idx[s]
            row = [0.0] * n
            row[si] = -1.0
            A.append(row)
            b.append(-L)
    for s in mdp.states:
        si = idx[s]
        acts = mdp.available_actions(s)
        if not acts:
            continue
        for a in acts:
            row = [0.0] * n
            row[si] = -1.0
            for ns, p, r in mdp.transitions.get(s, {}).get(a, []):
                row[idx[ns]] += mdp.gamma * p
            A.append(row)
            exp_r = sum(p * (r if r is not None else 0.0)
                        for ns, p, r in mdp.transitions.get(s, {}).get(a, []))
            b.append(-(exp_r + bound))
    c = [1.0] * n  # minimize sum w_s
    x = _simplex_minimize(c, A, b)
    elapsed = time.perf_counter() - t0
    if x is None:
        raise RuntimeError("LP for MDP is unbounded or infeasible")
    V = {s: x[idx[s]] - L for s in mdp.states}
    pi = greedy_policy(mdp, V)
    info = {"method": "linear_programming", "time": elapsed,
            "converged": True, "iterations": len(A)}
    return V, pi, info


# ====================================================================== #
# Gauss-Seidel (in-place) value iteration
# ====================================================================== #
def gauss_seidel_value_iteration(
    mdp: MDP,
    theta: float = 1e-8,
    max_iter: int = 100000,
) -> Tuple[Dict[Any, float], Policy, Dict[str, Any]]:
    """Asynchronous (in-place / Gauss-Seidel) value iteration.

    Updates each state's value *in place*, so later states in the same
    sweep already see updated values of earlier states.  Typically
    converges in fewer sweeps than synchronous value iteration.
    """
    V = {s: 0.0 for s in mdp.states}
    t0 = time.perf_counter()
    iters = 0
    for iters in range(1, max_iter + 1):
        delta = 0.0
        for s in mdp.states:
            acts = mdp.available_actions(s)
            if not acts:
                continue
            v_old = V[s]
            best = -math.inf
            for a in acts:
                q = 0.0
                for ns, p, r in mdp.transitions.get(s, {}).get(a, []):
                    q += p * ((r if r is not None else 0.0) + mdp.gamma * V[ns])
                if q > best:
                    best = q
            V[s] = best
            delta = max(delta, abs(best - v_old))
        if delta < theta:
            break
    elapsed = time.perf_counter() - t0
    pi = greedy_policy(mdp, V)
    info = {"iterations": iters, "time": elapsed, "converged": iters < max_iter,
            "method": "gauss_seidel"}
    return V, pi, info


# ====================================================================== #
# Prioritized Sweeping
# ====================================================================== #
def prioritized_sweeping(
    mdp: MDP,
    theta: float = 1e-8,
    max_sweeps: int = 100000,
) -> Tuple[Dict[Any, float], Policy, Dict[str, Any]]:
    """Prioritized sweeping value iteration.

    Maintains a priority queue of states whose Bellman error exceeds a
    threshold, processing the highest-priority state first.  Uses a
    *predecessor map* so that updating one state enqueues all states
    whose transitions depend on it.
    """
    # Build predecessor map: state -> set of (pred_state) that can reach it
    preds: Dict[Any, set] = {s: set() for s in mdp.states}
    for s in mdp.states:
        for a in mdp.available_actions(s):
            for ns, p, r in mdp.transitions.get(s, {}).get(a, []):
                preds[ns].add(s)

    V = {s: 0.0 for s in mdp.states}
    t0 = time.perf_counter()

    def bellman_error(s: Any) -> float:
        acts = mdp.available_actions(s)
        if not acts:
            return 0.0
        best = -math.inf
        for a in acts:
            q = 0.0
            for ns, p, r in mdp.transitions.get(s, {}).get(a, []):
                q += p * ((r if r is not None else 0.0) + mdp.gamma * V[ns])
            if q > best:
                best = q
        return abs(best - V[s])

    # Initial: enqueue all non-terminal states
    pq: List[Tuple[float, int, Any]] = []
    counter = 0
    for s in mdp.states:
        err = bellman_error(s)
        if err > theta:
            heapq.heappush(pq, (-err, counter, s))
            counter += 1

    sweeps = 0
    updates = 0
    while pq and sweeps < max_sweeps:
        # Process a batch (full sweep-ish)
        batch = min(len(pq), max(1, len(mdp.states) // 4))
        for _ in range(batch):
            if not pq:
                break
            neg_err, _, s = heapq.heappop(pq)
            err = -neg_err
            if err < theta:
                continue
            acts = mdp.available_actions(s)
            if not acts:
                continue
            best = -math.inf
            for a in acts:
                q = 0.0
                for ns, p, r in mdp.transitions.get(s, {}).get(a, []):
                    q += p * ((r if r is not None else 0.0) + mdp.gamma * V[ns])
                if q > best:
                    best = q
            V[s] = best
            updates += 1
            # Enqueue predecessors
            for ps in preds.get(s, set()):
                e = bellman_error(ps)
                if e > theta:
                    heapq.heappush(pq, (-e, counter, ps))
                    counter += 1
        sweeps += 1

    elapsed = time.perf_counter() - t0
    pi = greedy_policy(mdp, V)
    info = {"iterations": sweeps, "updates": updates, "time": elapsed,
            "converged": not pq, "method": "prioritized_sweeping"}
    return V, pi, info


# ====================================================================== #
# Real-Time Dynamic Programming (RTDP)
# ====================================================================== #
def rtdp(
    mdp: MDP,
    n_trials: int = 1000,
    max_steps: int = 1000,
    theta: float = 1e-6,
    init_v: Optional[float] = None,
    seed: Optional[int] = None,
) -> Tuple[Dict[Any, float], Policy, Dict[str, Any]]:
    """Real-Time Dynamic Programming.

    Runs repeated simulated trials from the start state.  At each visited
    state the agent takes the greedy action w.r.t. current V and performs
    a Bellman backup *in place*.  Only states visited during trials are
    updated, making RTDP efficient for large MDPs with sparse relevant
    regions.  Converges to V* for stochastic shortest-path problems.

    Parameters
    ----------
    init_v : optional initial value (heuristic admissible bound, e.g. 0).
    """
    rng = random.Random(seed)
    V = {s: (init_v if init_v is not None else 0.0) for s in mdp.states}
    t0 = time.perf_counter()
    total_updates = 0
    converged_trial = False

    def backup(s: Any) -> float:
        acts = mdp.available_actions(s)
        if not acts:
            return 0.0
        best = -math.inf
        for a in acts:
            q = 0.0
            for ns, p, r in mdp.transitions.get(s, {}).get(a, []):
                q += p * ((r if r is not None else 0.0) + mdp.gamma * V[ns])
            if q > best:
                best = q
        return best

    trial = 0
    for trial in range(n_trials):
        state = mdp.start_state
        delta_trial = 0.0
        for _ in range(max_steps):
            if mdp.is_terminal(state):
                break
            v_old = V[state]
            new_v = backup(state)
            delta_trial = max(delta_trial, abs(new_v - v_old))
            V[state] = new_v
            total_updates += 1
            # Choose greedy action (with small randomness to break ties)
            acts = mdp.available_actions(state)
            if not acts:
                break
            best_a = acts[0]
            best_q = -math.inf
            for a in acts:
                q = 0.0
                for ns, p, r in mdp.transitions.get(state, {}).get(a, []):
                    q += p * ((r if r is not None else 0.0) + mdp.gamma * V[ns])
                if q > best_q + 1e-12:
                    best_q = q
                    best_a = a
            # Sample next state
            state, _ = mdp.step(state, best_a, rng=rng)
        if delta_trial < theta:
            converged_trial = True
            break

    elapsed = time.perf_counter() - t0
    pi = greedy_policy(mdp, V)
    info = {"method": "rtdp", "trials": trial + 1, "updates": total_updates,
            "time": elapsed, "converged": converged_trial}
    return V, pi, info


__all__ = [
    "linear_programming_solve",
    "gauss_seidel_value_iteration",
    "prioritized_sweeping",
    "rtdp",
]