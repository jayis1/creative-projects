"""
turing_machine.analysis
=======================

Halting analysis and machine inspection utilities.

Provides reachability analysis, dead-state detection, tape statistics,
and step-count estimation.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Hashable, List, Optional, Set, Tuple

from .machine import Program, Tape, TMDirection, Transition, TuringMachine


def reachable_states(program: Program, initial_state: str) -> Set[str]:
    """Return the set of states reachable from ``initial_state``.

    Uses BFS over the state graph defined by transitions.
    """
    graph: Dict[str, List[str]] = defaultdict(list)
    for t in program:
        graph[t.state].append(t.new_state)
    visited: Set[str] = set()
    queue = [initial_state]
    while queue:
        s = queue.pop(0)
        if s in visited:
            continue
        visited.add(s)
        for nxt in graph.get(s, []):
            if nxt not in visited:
                queue.append(nxt)
    return visited


def dead_states(program: Program, initial_state: str, halt_states: Set[str]) -> Set[str]:
    """Return states that are reachable but can never reach a halt state.

    A state is "dead" if it is reachable from the initial state but no path
    from it leads to any halt state.
    """
    # Build reverse graph: new_state -> [states that transition to it]
    # Actually we need forward reachability to halt from each state
    graph: Dict[str, List[str]] = defaultdict(list)
    for t in program:
        graph[t.state].append(t.new_state)

    # For each reachable state, check if a halt state is reachable from it
    reach = reachable_states(program, initial_state)
    can_halt: Set[str] = set()

    def reaches_halt(state: str, visited: Set[str]) -> bool:
        if state in halt_states:
            return True
        if state in visited:
            return False
        visited.add(state)
        for nxt in graph.get(state, []):
            if reaches_halt(nxt, visited):
                return True
        return False

    for s in reach:
        if reaches_halt(s, set()):
            can_halt.add(s)

    return reach - can_halt


def unused_states(program: Program, initial_state: str) -> Set[str]:
    """Return states defined in the program but never reachable from initial."""
    all_states = set(program.states())
    reach = reachable_states(program, initial_state)
    return all_states - reach


def state_transition_count(program: Program) -> Dict[str, int]:
    """Return a mapping from state to the number of transitions out of it."""
    counts: Dict[str, int] = defaultdict(int)
    for t in program:
        counts[t.state] += 1
    return dict(counts)


def tape_statistics(tape: Tape) -> Dict[str, Any]:
    """Return statistics about a tape's contents."""
    cells = tape.to_list(strip_blanks=False)
    from collections import Counter
    symbol_counts = Counter(str(c) for c in cells)
    non_blank = sum(1 for c in cells if c != tape.blank)
    return {
        "length": len(cells),
        "non_blank_count": non_blank,
        "head_position": tape.head,
        "symbol_counts": dict(symbol_counts),
        "unique_symbols": len(symbol_counts),
    }


def estimate_steps(tm: TuringMachine, sample_size: int = 1000) -> Optional[float]:
    """Estimate the average steps before halting by sampling.

    Runs the machine up to ``sample_size`` steps and extrapolates.
    Returns None if the machine halts before ``sample_size``.
    """
    if tm.halted:
        return float(tm.steps)
    original_max = tm.max_steps
    tm.max_steps = sample_size
    tm.run()
    tm.max_steps = original_max
    if tm.halted:
        return float(tm.steps)
    return None  # didn't halt within sample


def analyze_machine(tm: TuringMachine) -> Dict[str, Any]:
    """Return a comprehensive analysis of a Turing machine."""
    prog = tm.program
    reach = reachable_states(prog, tm.initial_state)
    dead = dead_states(prog, tm.initial_state, tm.halt_states)
    unused = unused_states(prog, tm.initial_state)
    counts = state_transition_count(prog)
    return {
        "initial_state": tm.initial_state,
        "current_state": tm.state,
        "halt_states": sorted(tm.halt_states),
        "reachable_states": sorted(reach),
        "dead_states": sorted(dead),
        "unused_states": sorted(unused),
        "total_states": len(prog.states()),
        "total_transitions": len(prog),
        "transitions_per_state": counts,
        "num_tapes": tm.num_tapes,
        "steps_executed": tm.steps,
        "halted": tm.halted,
    }