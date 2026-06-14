"""
Additional problem generators for CSP Solver.

Includes:
- Job Shop Scheduling
- Knight's Tour
- Graph from edge list (generic)
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .csp import CSP, Variable, Constraint


# ─── Job Shop Scheduling ──────────────────────────────────────────

def job_shop_csp(
    jobs: Dict[str, Tuple[int, str]],
    resources: Optional[Dict[str, int]] = None,
) -> CSP:
    """Create a CSP for a job shop scheduling problem.

    Each job has a start time variable, a duration, and an assigned resource.
    Jobs using the same resource cannot overlap.

    Args:
        jobs: Dict mapping job name to (duration, resource_id).
            E.g., {"J1": (3, "R1"), "J2": (2, "R1"), "J3": (4, "R2")}
        resources: Optional dict mapping resource_id to max capacity.
            If None, each resource has capacity 1.

    Returns:
        A CSP whose solution maps each job to its start time.

    Raises:
        ValueError: If jobs dict is empty.
    """
    if not jobs:
        raise ValueError("At least one job is required")

    csp = CSP()

    # Calculate max time horizon
    max_duration_sum = sum(dur for dur, _ in jobs.values())
    max_single = max(dur for dur, _ in jobs.values())
    horizon = max_duration_sum + max_single

    # Variables: start time for each job
    for job_name, (duration, resource) in jobs.items():
        csp.add_variable(Variable(f"start_{job_name}", domain=set(range(horizon))))

    # No-overlap constraints for jobs sharing the same resource
    job_list = sorted(jobs.keys())
    for i in range(len(job_list)):
        for j in range(i + 1, len(job_list)):
            j1, j2 = job_list[i], job_list[j]
            dur1, res1 = jobs[j1]
            dur2, res2 = jobs[j2]

            # Only constrain jobs on the same resource
            if res1 == res2:
                # Either j1 finishes before j2 starts, or vice versa
                # start_j1 + dur1 <= start_j2 OR start_j2 + dur2 <= start_j1
                csp.add_constraint(Constraint(
                    (f"start_{j1}", f"start_{j2}"),
                    lambda a, s1=f"start_{j1}", s2=f"start_{j2}",
                         d1=dur1, d2=dur2: a[s1] + d1 <= a[s2] or a[s2] + d2 <= a[s1],
                    pair_check=lambda x, y, d1=dur1, d2=dur2: x + d1 <= y or y + d2 <= x,
                    name=f"no_overlap_{j1}_{j2}",
                ))

    return csp


def format_schedule(
    assignment: Dict[str, int],
    jobs: Dict[str, Tuple[int, str]],
) -> str:
    """Format a job shop schedule.

    Args:
        assignment: Solution assignment mapping start_* variables to times.
        jobs: Dict mapping job name to (duration, resource_id).

    Returns:
        Formatted string representation of the schedule.
    """
    # Determine time range
    max_time = 0
    for job_name, (duration, _) in jobs.items():
        end_time = assignment.get(f"start_{job_name}", 0) + duration
        max_time = max(max_time, end_time)

    lines = []
    lines.append("  Job Schedule:")
    lines.append("  " + "=" * 50)

    # Sort by start time
    schedule = []
    for job_name, (duration, resource) in jobs.items():
        start = assignment.get(f"start_{job_name}", 0)
        schedule.append((start, job_name, duration, resource))

    schedule.sort()

    for start, job_name, duration, resource in schedule:
        bar = "█" * duration
        padding = " " * start
        lines.append(f"  {job_name:>6} [{resource:>3}] {padding}{bar}  t={start}..{start + duration}")

    lines.append("  " + "-" * 50)

    # Resource utilization
    resources_used: Dict[str, List] = {}
    for job_name, (duration, resource) in jobs.items():
        if resource not in resources_used:
            resources_used[resource] = []
        start = assignment.get(f"start_{job_name}", 0)
        resources_used[resource].append((start, start + duration, job_name))

    lines.append("  Resource utilization:")
    for res, intervals in sorted(resources_used.items()):
        lines.append(f"    {res}: {len(intervals)} job(s)")

    return "\n".join(lines)


# ─── Knight's Tour ────────────────────────────────────────────────

def knights_tour_csp(n: int = 5, m: Optional[int] = None) -> CSP:
    """Create a CSP for the Knight's Tour problem on an n×m board.

    A Knight's Tour is a sequence of moves by a knight that visits
    every square exactly once.

    Args:
        n: Board width (default 5).
        m: Board height (default same as n).

    Returns:
        A CSP whose solution maps each cell to a move number (0..n*m-1).

    Raises:
        ValueError: If board is too small (minimum 1×1).
    """
    if m is None:
        m = n
    if n < 1 or m < 1:
        raise ValueError("Board dimensions must be at least 1")

    total = n * m

    csp = CSP()

    # Variables: one per cell, domain is move number (0 to total-1)
    for i in range(n):
        for j in range(m):
            csp.add_variable(Variable(f"K{i}_{j}", domain=set(range(total))))

    # Knight move offsets
    knight_moves = [
        (2, 1), (2, -1), (-2, 1), (-2, -1),
        (1, 2), (1, -2), (-1, 2), (-1, -2),
    ]

    # All-different: each move number used exactly once
    cells = [f"K{i}_{j}" for i in range(n) for j in range(m)]
    for i in range(len(cells)):
        for j in range(i + 1, len(cells)):
            csp.add_constraint(Constraint(
                (cells[i], cells[j]),
                lambda a, c1=cells[i], c2=cells[j]: a[c1] != a[c2],
                pair_check=lambda x, y: x != y,
                name=f"diff_{cells[i]}_{cells[j]}",
            ))

    # Consecutive move constraint: consecutive moves must be a knight's move apart
    for i in range(n):
        for j in range(m):
            reachable = []
            for di, dj in knight_moves:
                ni, nj = i + di, j + dj
                if 0 <= ni < n and 0 <= nj < m:
                    reachable.append((ni, nj))

            for ni, nj in reachable:
                # If cell (i,j) has move k, then cell (ni,nj) must have
                # either move k-1 or move k+1 (or some other move, but
                # the constraint is: consecutive move numbers are knight-adjacent)
                # We enforce: for any two cells, if their move numbers differ by 1,
                # they must be a knight's move apart.
                # This is complex as an n-ary constraint, so we simplify:
                # For each cell and each possible move number k>0, the cell
                # at move k-1 must be a knight neighbor.
                # We model this as: for each pair of cells that are NOT knight-adjacent,
                # they cannot have consecutive move numbers.
                pass

    # Simpler approach: for non-knight-adjacent cells, they cannot have consecutive moves
    for idx_a in range(len(cells)):
        ci, cj = idx_a // m, idx_a % m
        # Compute which cells ARE knight-adjacent to (ci, cj)
        knight_adj = set()
        for di, dj in knight_moves:
            ni, nj = ci + di, cj + dj
            if 0 <= ni < n and 0 <= nj < m:
                knight_adj.add(f"K{ni}_{nj}")

        for idx_b in range(idx_a + 1, len(cells)):
            cell_b = cells[idx_b]
            if cell_b not in knight_adj:
                # These cells are NOT knight-adjacent, so their move numbers
                # cannot be consecutive (differ by 1)
                csp.add_constraint(Constraint(
                    (cells[idx_a], cell_b),
                    lambda a, c1=cells[idx_a], c2=cell_b: abs(a[c1] - a[c2]) != 1,
                    name=f"nonadj_{cells[idx_a]}_{cell_b}",
                ))

    return csp


# ─── Generic Graph from Edge List ──────────────────────────────────

def graph_csp_from_edges(
    edges: List[Tuple[str, str]],
    domain_size: int,
    constraint_type: str = "not_equal",
) -> CSP:
    """Create a generic CSP from an edge list.

    Useful for custom graph coloring or other graph-based CSPs.

    Args:
        edges: List of (node1, node2) pairs.
        domain_size: Size of each variable's domain (values 0..domain_size-1).
        constraint_type: Type of constraint between connected nodes.
            'not_equal': adjacent nodes must have different values (graph coloring).
            'less_than': adjacent nodes must satisfy node1 < node2.

    Returns:
        A CSP whose solution maps each node to a value.

    Raises:
        ValueError: If domain_size < 1.
    """
    if domain_size < 1:
        raise ValueError("domain_size must be at least 1")

    csp = CSP()
    domain = set(range(domain_size))

    # Collect all nodes
    nodes = set()
    for a, b in edges:
        nodes.add(a)
        nodes.add(b)

    # Create variables
    for node in sorted(nodes):
        csp.add_variable(Variable(node, domain=domain))

    # Add constraints
    for a, b in edges:
        if constraint_type == "not_equal":
            csp.add_constraint(Constraint(
                (a, b),
                lambda assign, na=a, nb=b: assign[na] != assign[nb],
                pair_check=lambda x, y: x != y,
                name=f"{a}≠{b}",
            ))
        elif constraint_type == "less_than":
            csp.add_constraint(Constraint(
                (a, b),
                lambda assign, na=a, nb=b: assign[na] < assign[nb],
                pair_check=lambda x, y: x < y,
                name=f"{a}<{b}",
            ))
        else:
            raise ValueError(f"Unknown constraint type: {constraint_type}")

    return csp