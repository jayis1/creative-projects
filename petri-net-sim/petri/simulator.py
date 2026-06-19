"""Simulator: token game over a PetriNet."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Iterator, Optional

from .net import PetriNet, FiringError


@dataclass
class FiringRecord:
    """One step of a simulation trace."""

    step: int
    marking_before: dict[str, int]
    transition: str
    marking_after: dict[str, int]

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "marking_before": self.marking_before,
            "transition": self.transition,
            "marking_after": self.marking_after,
        }


@dataclass
class SimulationResult:
    """The result of a simulation run."""

    trace: list[FiringRecord] = field(default_factory=list)
    final_marking: dict[str, int] = field(default_factory=dict)
    deadlocked: bool = False
    steps_fired: int = 0

    def to_dict(self) -> dict:
        return {
            "trace": [r.to_dict() for r in self.trace],
            "final_marking": self.final_marking,
            "deadlocked": self.deadlocked,
            "steps_fired": self.steps_fired,
        }


class Simulator:
    """Execute the token game on a PetriNet.

    Modes
    -----
    - ``random_walk``: pick a random enabled transition each step.
    - ``single_step``: fire one specified transition.
    - ``maximal_step``: fire a maximal set of non-conflicting transitions simultaneously.
    """

    def __init__(self, net: PetriNet, seed: Optional[int] = None) -> None:
        self.net = net
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------
    # Single transition
    # ------------------------------------------------------------------
    def step(self, marking: dict[str, int], transition_name: str) -> dict[str, int]:
        """Fire one transition, returning a new marking."""
        return self.net.fire(transition_name, marking)

    # ------------------------------------------------------------------
    # Random walk
    # ------------------------------------------------------------------
    def random_walk(
        self,
        max_steps: int = 1000,
        marking: Optional[dict[str, int]] = None,
    ) -> SimulationResult:
        """Fire random enabled transitions until deadlock or ``max_steps``."""
        current = dict(marking) if marking is not None else self.net.initial_marking()
        result = SimulationResult()
        for i in range(max_steps):
            enabled = self.net.enabled_transitions(current)
            if not enabled:
                result.deadlocked = True
                break
            choice = self._rng.choice(enabled)
            new_marking = self.net.fire(choice, current)
            result.trace.append(
                FiringRecord(
                    step=i,
                    marking_before=dict(current),
                    transition=choice,
                    marking_after=dict(new_marking),
                )
            )
            current = new_marking
            result.steps_fired += 1
        result.final_marking = dict(current)
        return result

    # ------------------------------------------------------------------
    # Fixed sequence
    # ------------------------------------------------------------------
    def run_sequence(
        self,
        sequence: list[str],
        marking: Optional[dict[str, int]] = None,
        strict: bool = True,
    ) -> SimulationResult:
        """Fire a specific sequence of transitions.

        If ``strict`` is True, raise ``FiringError`` on a disabled transition.
        Otherwise stop early and mark as deadlocked.
        """
        current = dict(marking) if marking is not None else self.net.initial_marking()
        result = SimulationResult()
        for i, t_name in enumerate(sequence):
            if not self.net.is_enabled(t_name, current):
                if strict:
                    raise FiringError(
                        f"Transition '{t_name}' not enabled at step {i}"
                    )
                result.deadlocked = True
                break
            new_marking = self.net.fire(t_name, current)
            result.trace.append(
                FiringRecord(
                    step=i,
                    marking_before=dict(current),
                    transition=t_name,
                    marking_after=dict(new_marking),
                )
            )
            current = new_marking
            result.steps_fired += 1
        result.final_marking = dict(current)
        return result

    # ------------------------------------------------------------------
    # Maximal step (fire all non-conflicting enabled transitions at once)
    # ------------------------------------------------------------------
    def maximal_step(self, marking: dict[str, int]) -> dict[str, int]:
        """Fire a maximal set of concurrent transitions.

        Greedily fires enabled transitions whose input places don't overlap
        with already-fired ones in this step. This is an approximation of
        step semantics — it fires transitions until no more can fire concurrently.
        """
        current = dict(marking)
        consumed_places: set[str] = set()
        fired_any = True
        while fired_any:
            fired_any = False
            for t_name in self.net.transitions:
                if not self.net.is_enabled(t_name, current):
                    continue
                # check no input overlap with already-fired transitions in this step
                preset = self.net.preset(t_name)
                if preset & consumed_places:
                    continue
                # fire it
                self.net.fire_inplace(t_name, current)
                consumed_places |= preset
                consumed_places |= self.net.postset(t_name)
                fired_any = True
        return current

    # ------------------------------------------------------------------
    # Fire until a target marking is reached or steps exhausted
    # ------------------------------------------------------------------
    def fire_until(
        self,
        target: dict[str, int],
        max_steps: int = 10000,
        marking: Optional[dict[str, int]] = None,
    ) -> Optional[list[str]]:
        """Random-walk until ``target`` is reached. Returns the firing sequence or None."""
        current = dict(marking) if marking is not None else self.net.initial_marking()
        sequence: list[str] = []
        for _ in range(max_steps):
            if all(current.get(k, 0) == v for k, v in target.items()):
                return sequence
            enabled = self.net.enabled_transitions(current)
            if not enabled:
                return None
            choice = self._rng.choice(enabled)
            current = self.net.fire(choice, current)
            sequence.append(choice)
        return None

    # ------------------------------------------------------------------
    # Iterator protocol for step-by-step simulation
    # ------------------------------------------------------------------
    def iter_random(self, marking: Optional[dict[str, int]] = None) -> Iterator[FiringRecord]:
        """Infinite iterator that yields FiringRecords. Stops at deadlock via StopIteration."""
        current = dict(marking) if marking is not None else self.net.initial_marking()
        i = 0
        while True:
            enabled = self.net.enabled_transitions(current)
            if not enabled:
                return
            choice = self._rng.choice(enabled)
            new_marking = self.net.fire(choice, current)
            yield FiringRecord(
                step=i,
                marking_before=dict(current),
                transition=choice,
                marking_after=dict(new_marking),
            )
            current = new_marking
            i += 1