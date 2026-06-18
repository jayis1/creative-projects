"""
turing_machine.composition
==========================

Compose Turing machines into pipelines and conditional branches.

This module provides a high-level API for chaining machines together:

* :class:`Pipeline` — run machines sequentially, feeding the output of
  one into the input of the next.
* :class:`Conditional` — run one of several machines depending on a
  predicate over the tape.
* :class:`Loop` — repeatedly run a machine until a condition is met.
* :func:`compose` – convenience function for building pipelines.

Example
-------

::

    from turing_machine.machines import binary_incrementer
    from turing_machine.composition import Pipeline

    pipe = Pipeline()
    pipe.add(binary_incrementer(), "s0", "halt", "_")
    pipe.add(binary_incrementer(), "s0", "halt", "_")
    result = pipe.run(["1", "0", "1"])  # increment twice
    # result == ['1', '1', '1', '1']  (101 → 102 → 103 → 110... wait, actually binary)
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Hashable, List, Optional, Sequence, Tuple

from .machine import Program, Tape, TMDirection, Transition, TuringMachine

logger = logging.getLogger(__name__)


class Pipeline:
    """A sequence of machines that run one after another.

    The output tape of machine *i* becomes the input tape of machine *i+1*.
    Each machine in the pipeline is described by:

    * ``program`` — the :class:`Program` to run
    * ``initial_state`` — the start state
    * ``halt_state`` — a single halt state (or the first of a set)
    * ``blank`` — the blank symbol
    """

    def __init__(self, blank: Hashable = "_", max_steps: int = 1_000_000):
        self.blank = blank
        self.max_steps = max_steps
        self.stages: List[Dict[str, Any]] = []
        self.results: List[Dict[str, Any]] = []

    def add(
        self,
        program: Program,
        initial_state: str = "s0",
        halt_state: str = "halt",
        blank: Optional[Hashable] = None,
        name: str = "",
    ) -> "Pipeline":
        """Add a stage to the pipeline. Returns self for chaining."""
        self.stages.append({
            "program": program,
            "initial_state": initial_state,
            "halt_states": {halt_state} if isinstance(halt_state, str) else set(halt_state),
            "blank": blank or self.blank,
            "name": name or f"stage_{len(self.stages)}",
        })
        return self

    def run(self, input_tape: Sequence[Hashable], verbose: bool = False) -> List[Hashable]:
        """Run the full pipeline. Returns the final tape contents."""
        tape = list(input_tape)
        self.results = []

        for i, stage in enumerate(self.stages):
            name = stage["name"]
            logger.info("Pipeline stage %d (%s): input=%s", i, name, tape)

            tm = TuringMachine(
                stage["program"],
                initial_state=stage["initial_state"],
                tape=list(tape),
                blank=stage["blank"],
                halt_states=stage["halt_states"],
                max_steps=self.max_steps,
            )
            tm.run(verbose=verbose)

            tape = tm.tapes[0].to_list()
            self.results.append({
                "name": name,
                "final_state": tm.state,
                "steps": tm.steps,
                "halted": tm.halted,
                "tape": list(tape),
            })
            logger.info("Pipeline stage %d (%s): output=%s, steps=%d", i, name, tape, tm.steps)

        return tape

    def summary(self) -> str:
        """Return a human-readable summary of the pipeline execution."""
        lines = ["Pipeline summary:"]
        for r in self.results:
            lines.append(
                f"  {r['name']}: state={r['final_state']}, "
                f"steps={r['steps']}, halted={r['halted']}, "
                f"tape={''.join(str(c) for c in r['tape'])}"
            )
        return "\n".join(lines)


class Conditional:
    """Run one of several machines depending on a predicate.

    The predicate receives the input tape (as a list) and returns the
    index of the machine to run.
    """

    def __init__(self, blank: Hashable = "_", max_steps: int = 1_000_000):
        self.blank = blank
        self.max_steps = max_steps
        self.branches: List[Dict[str, Any]] = []
        self.predicate: Optional[Callable[[List[Hashable]], int]] = None

    def set_predicate(self, pred: Callable[[List[Hashable]], int]) -> "Conditional":
        """Set the branching predicate."""
        self.predicate = pred
        return self

    def add_branch(
        self,
        program: Program,
        initial_state: str = "s0",
        halt_state: str = "halt",
        blank: Optional[Hashable] = None,
        name: str = "",
    ) -> "Conditional":
        """Add a branch machine."""
        self.branches.append({
            "program": program,
            "initial_state": initial_state,
            "halt_states": {halt_state} if isinstance(halt_state, str) else set(halt_state),
            "blank": blank or self.blank,
            "name": name or f"branch_{len(self.branches)}",
        })
        return self

    def run(self, input_tape: Sequence[Hashable], verbose: bool = False) -> List[Hashable]:
        """Evaluate the predicate and run the selected branch."""
        if self.predicate is None:
            raise ValueError("no predicate set")
        if not self.branches:
            raise ValueError("no branches defined")

        tape = list(input_tape)
        idx = self.predicate(tape)
        if idx < 0 or idx >= len(self.branches):
            raise ValueError(f"predicate returned invalid index {idx}")

        branch = self.branches[idx]
        logger.info("Conditional: selected branch %d (%s)", idx, branch["name"])

        tm = TuringMachine(
            branch["program"],
            initial_state=branch["initial_state"],
            tape=tape,
            blank=branch["blank"],
            halt_states=branch["halt_states"],
            max_steps=self.max_steps,
        )
        tm.run(verbose=verbose)
        return tm.tapes[0].to_list()


class Loop:
    """Repeatedly run a machine until a condition is met.

    The condition function receives the current tape and step count, and
    returns True to continue looping, False to stop.
    """

    def __init__(self, blank: Hashable = "_", max_steps: int = 1_000_000):
        self.blank = blank
        self.max_steps = max_steps
        self.program: Optional[Program] = None
        self.initial_state = "s0"
        self.halt_states: set = {"halt"}
        self.condition: Optional[Callable[[List[Hashable], int], bool]] = None
        self.max_iterations = 1000

    def set_machine(
        self,
        program: Program,
        initial_state: str = "s0",
        halt_state: str = "halt",
        blank: Optional[Hashable] = None,
    ) -> "Loop":
        self.program = program
        self.initial_state = initial_state
        self.halt_states = {halt_state} if isinstance(halt_state, str) else set(halt_state)
        self.blank = blank or self.blank
        return self

    def set_condition(self, cond: Callable[[List[Hashable], int], bool]) -> "Loop":
        """Set the loop condition. Loop continues while cond returns True."""
        self.condition = cond
        return self

    def run(self, input_tape: Sequence[Hashable], verbose: bool = False) -> List[Hashable]:
        if self.program is None:
            raise ValueError("no machine set")
        if self.condition is None:
            raise ValueError("no condition set")

        tape = list(input_tape)
        iteration = 0

        while self.condition(tape, iteration):
            if iteration >= self.max_iterations:
                logger.warning("Loop: max iterations (%d) reached", self.max_iterations)
                break

            logger.info("Loop iteration %d: input=%s", iteration, tape)
            tm = TuringMachine(
                self.program,
                initial_state=self.initial_state,
                tape=list(tape),
                blank=self.blank,
                halt_states=self.halt_states,
                max_steps=self.max_steps,
            )
            tm.run(verbose=verbose)
            tape = tm.tapes[0].to_list()
            iteration += 1

        logger.info("Loop completed after %d iterations", iteration)
        return tape


def compose(*machines: Tuple[Program, str, str]) -> Pipeline:
    """Quickly compose machines into a pipeline.

    Each argument is a tuple of ``(program, initial_state, halt_state)``.
    """
    pipe = Pipeline()
    for prog, init, halt in machines:
        pipe.add(prog, init, halt)
    return pipe