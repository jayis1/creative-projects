"""
turing_machine.debugger
=======================

Interactive step-through debugger for Turing machines.

Provides step-by-step execution, breakpoints, conditional breakpoints,
watch expressions, and execution tracing.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Set, Tuple

from .machine import Tape, TMDirection, Transition, TuringMachine, TMStep


@dataclass
class Breakpoint:
    """A breakpoint on a specific state."""
    state: str
    condition: Optional[Callable[[TuringMachine], bool]] = None

    def matches(self, tm: TuringMachine) -> bool:
        if self.state != "*" and tm.state != self.state:
            return False
        if self.condition is not None:
            return self.condition(tm)
        return True


class Debugger:
    """Step-through debugger for a :class:`TuringMachine`.

    Usage::

        dbg = Debugger(tm)
        dbg.add_breakpoint("s1")
        dbg.run()  # runs until breakpoint or halt
    """

    def __init__(self, tm: TuringMachine):
        self.tm = tm
        self.breakpoints: List[Breakpoint] = []
        self.watch_states: Set[str] = set()
        self.trace: List[TMStep] = []
        self.recording = True
        self._stopped = False

    def add_breakpoint(self, state: str, condition: Optional[Callable] = None) -> None:
        """Add a breakpoint on a state (use '*' for any state)."""
        self.breakpoints.append(Breakpoint(state, condition))

    def remove_breakpoint(self, state: str) -> None:
        """Remove all breakpoints on the given state."""
        self.breakpoints = [bp for bp in self.breakpoints if bp.state != state]

    def clear_breakpoints(self) -> None:
        self.breakpoints = []

    def watch(self, state: str) -> None:
        """Watch a state (print when entered)."""
        self.watch_states.add(state)

    def _check_breakpoints(self) -> bool:
        for bp in self.breakpoints:
            if bp.matches(self.tm):
                return True
        return False

    def step(self) -> bool:
        """Execute one step. Returns True if the machine can continue."""
        if self.tm.halted:
            return False
        if self.tm.state in self.watch_states:
            print(f"  [watch] entered state {self.tm.state}", file=sys.stderr)
        result = self.tm.step()
        if self.recording and self.tm.history:
            self.trace.append(self.tm.history[-1])
        return result

    def run(self, max_steps: int = 1_000_000) -> str:
        """Run until a breakpoint is hit or the machine halts."""
        steps = 0
        while steps < max_steps:
            if self._check_breakpoints() and steps > 0:
                print(f"  [breakpoint] state={self.tm.state}, step={self.tm.steps}", file=sys.stderr)
                self._stopped = True
                return self.tm.state
            if not self.step():
                self._stopped = False
                return self.tm.state
            steps += 1
        self._stopped = False
        return self.tm.state

    def continue_run(self) -> str:
        """Continue from a stopped state."""
        self._stopped = False
        return self.run()

    def status(self) -> str:
        """Return a status string."""
        lines = [
            f"Debugger status:",
            f"  state: {self.tm.state}",
            f"  steps: {self.tm.steps}",
            f"  halted: {self.tm.halted}",
            f"  stopped: {self._stopped}",
            f"  breakpoints: {len(self.breakpoints)}",
        ]
        for i, t in enumerate(self.tm.tapes):
            lines.append(f"  tape {i}: {t.render()}")
        return "\n".join(lines)

    def print_trace(self, last_n: int = 20) -> None:
        """Print the last N trace entries."""
        entries = self.trace[-last_n:] if last_n > 0 else self.trace
        for entry in entries:
            print(entry, file=sys.stderr)

    def reset(self) -> None:
        """Reset the machine and clear the trace."""
        self.tm.reset()
        self.trace = []
        self._stopped = False