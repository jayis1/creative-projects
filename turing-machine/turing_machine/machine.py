"""
turing_machine.machine
======================

Core Turing machine primitives: Tape, Transition, Program, TuringMachine,
and MultiTapeTM.

Design notes
------------
* Tapes are *infinite* in theory but finite in practice.  We represent each
  tape as a Python list of cells whose symbols are arbitrary hashable values
  (typically strings).  The list grows lazily: when the head moves past either
  end we extend the list with blank symbols.

* ``TMDirection`` is an ``Enum`` rather than bare integers so that the
  machine-definition parser and the debugger can pretty-print transitions.

* A machine runs until either:
    1. It enters an explicit halt state, **or**
    2. It has no applicable transition for the current (state, symbol) pair
       (an implicit reject), **or**
    3. ``max_steps`` is exceeded (safety valve to prevent infinite loops in
       interactive use).
"""

from __future__ import annotations

import enum
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Hashable, Iterable, Iterator, List, Optional, Sequence, Tuple, Union

# ---------------------------------------------------------------------------
# Direction
# ---------------------------------------------------------------------------

class TMDirection(enum.Enum):
    """Head movement directions for a transition."""
    LEFT = "L"
    RIGHT = "R"
    STAY = "S"

    @classmethod
    def parse(cls, value: Union[str, "TMDirection", int]) -> "TMDirection":
        """Parse a direction from a string, int, or enum value.

        Accepts 'L'/'R'/'S' (any case), -1/+1/0, or an existing enum.
        """
        if isinstance(value, cls):
            return value
        if isinstance(value, int):
            if value == -1:
                return cls.LEFT
            if value == 1:
                return cls.RIGHT
            if value == 0:
                return cls.STAY
            raise ValueError(f"invalid direction int: {value}")
        if isinstance(value, str):
            v = value.strip().upper()
            mapping = {"L": cls.LEFT, "R": cls.RIGHT, "S": cls.STAY,
                       "LEFT": cls.LEFT, "RIGHT": cls.RIGHT, "STAY": cls.STAY,
                       "<": cls.LEFT, ">": cls.RIGHT, "-": cls.STAY}
            if v in mapping:
                return mapping[v]
        raise ValueError(f"invalid direction: {value!r}")

    @property
    def delta(self) -> int:
        """Signed integer offset for the head movement."""
        return {TMDirection.LEFT: -1, TMDirection.RIGHT: 1, TMDirection.STAY: 0}[self]

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# Tape
# ---------------------------------------------------------------------------

class Tape:
    """A single Turing machine tape.

    The tape is a finite list that grows on demand when the head moves past
    either end.  The blank symbol is used for uninitialized cells.
    """

    __slots__ = ("_cells", "_head", "_blank")

    def __init__(self, blank: Hashable = "_", tape: Optional[Sequence[Hashable]] = None, head: int = 0):
        self._blank = blank
        # Ensure at least one cell exists so reads/writes always succeed
        if tape is not None and len(tape) > 0:
            self._cells: List[Hashable] = list(tape)
        else:
            self._cells: List[Hashable] = [blank]
        self._head = head

    # -- core operations ----------------------------------------------------

    def _ensure(self, index: int) -> None:
        """Ensure the internal list is large enough to include ``index``."""
        if index < 0:
            # Prepend blanks
            n = -index
            self._cells[0:0] = [self._blank] * n
            self._head += n
            index = 0
        if index >= len(self._cells):
            self._cells.extend([self._blank] * (index - len(self._cells) + 1))

    def read(self) -> Hashable:
        """Return the symbol under the head."""
        if 0 <= self._head < len(self._cells):
            return self._cells[self._head]
        return self._blank

    def write(self, symbol: Hashable) -> None:
        """Write ``symbol`` to the current cell."""
        self._ensure(self._head)
        self._cells[self._head] = symbol

    def move(self, direction: Union[TMDirection, str, int]) -> None:
        """Move the head by one step in ``direction``."""
        d = TMDirection.parse(direction).delta
        self._head += d
        if self._head < 0 or self._head >= len(self._cells):
            self._ensure(self._head)

    # -- query helpers ------------------------------------------------------

    @property
    def head(self) -> int:
        return self._head

    @head.setter
    def head(self, value: int) -> None:
        self._ensure(value)
        self._head = value

    @property
    def blank(self) -> Hashable:
        return self._blank

    def __len__(self) -> int:
        return len(self._cells)

    def __getitem__(self, index: int) -> Hashable:
        if 0 <= index < len(self._cells):
            return self._cells[index]
        return self._blank

    def __setitem__(self, index: int, value: Hashable) -> None:
        self._ensure(index)
        self._cells[index] = value

    def __iter__(self) -> Iterator[Hashable]:
        return iter(self._cells)

    def to_list(self, strip_blanks: bool = True) -> List[Hashable]:
        """Return tape contents as a list.

        If ``strip_blanks`` is True, trailing (and leading) blank symbols are
        removed, but at least one cell is always returned (the blank itself if
        the tape is entirely blank).
        """
        cells = list(self._cells) if self._cells else [self._blank]
        if strip_blanks:
            while len(cells) > 1 and cells[-1] == self._blank:
                cells.pop()
            while len(cells) > 1 and cells[0] == self._blank:
                cells.pop(0)
        return cells

    def copy(self) -> "Tape":
        """Return a deep copy of this tape (cells are shared references)."""
        return Tape(self._blank, self._cells, self._head)

    def render(self, window: Optional[Tuple[int, int]] = None, cell_width: int = 3) -> str:
        """Return a two-line ASCII rendering: the tape cells and the head marker.

        Parameters
        ----------
        window : (start, end) or None
            If given, show only cells in [start, end).  Otherwise show the
            non-blank portion of the tape.
        cell_width : int
            Width of each rendered cell.
        """
        if window is not None:
            start, end = window
            cells = [self[i] for i in range(start, end)]
            head_idx = self._head - start
        else:
            cells = self.to_list(strip_blanks=True)
            # Compensate for stripped leading blanks: find first non-blank
            first_nb = 0
            for i, c in enumerate(self._cells):
                if c != self._blank:
                    first_nb = i
                    break
            head_idx = self._head - first_nb
        w = cell_width
        row = ""
        head_row = ""
        for i, c in enumerate(cells):
            s = str(c)
            if len(s) > w:
                s = s[:w]
            cell = s.center(w)
            row += cell
            if i == head_idx:
                head_row += "^".center(w)
            else:
                head_row += " ".center(w)
        if not cells:
            row = " ".center(w)
            head_row = "^".center(w) if head_idx == 0 else " ".center(w)
        return row + "\n" + head_row

    def __repr__(self) -> str:
        return f"Tape(blank={self._blank!r}, head={self._head}, cells={self._cells!r})"

    def __str__(self) -> str:
        return self.render()


# ---------------------------------------------------------------------------
# Transition
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Transition:
    """A single transition rule: (state, read) -> (new_state, write, direction).

    For multi-tape machines, ``write`` and ``direction`` are tuples where each
    element corresponds to one tape.

    Positional argument order: ``Transition(state, read, write, direction, new_state)``
    """
    state: str               # current state (used as part of the lookup key)
    read: Hashable           # symbol to match under the head
    write: Hashable          # symbol(s) to write
    direction: Union[TMDirection, Tuple[TMDirection, ...]]  # head movement
    new_state: str = ""      # next state to enter

    def __post_init__(self):
        # Normalize direction(s)
        d = self.direction
        if isinstance(d, tuple):
            object.__setattr__(self, "direction", tuple(TMDirection.parse(x) for x in d))
        else:
            object.__setattr__(self, "direction", TMDirection.parse(d))
        # Ensure new_state defaults to state if empty
        if not self.new_state:
            object.__setattr__(self, "new_state", self.state)

    def applies_to(self, state: str, symbol: Hashable) -> bool:
        return self.state == state and self.read == symbol

    def __str__(self) -> str:
        return f"({self.state}, {self.read}) -> ({self.new_state}, {self.write}, {self.direction})"


# Legacy alias
TMRule = Transition


# ---------------------------------------------------------------------------
# Program
# ---------------------------------------------------------------------------

class Program:
    """A collection of transitions keyed by (state, symbol).

    This provides O(1) lookup of the applicable transition for a given
    (state, symbol) pair and supports wildcard symbols.
    """

    WILDCARD = "*"

    def __init__(self, transitions: Optional[Iterable[Transition]] = None):
        self._rules: Dict[Tuple[str, Hashable], Transition] = {}
        self._wildcards: List[Transition] = []
        if transitions:
            for t in transitions:
                self.add(t)

    def add(self, t: Transition) -> None:
        """Add a transition.  If ``t.read`` is the wildcard ``*``, it is added
        to the wildcard list and matched only when no specific rule applies."""
        if t.read == self.WILDCARD:
            self._wildcards.append(t)
        else:
            self._rules[(t.state, t.read)] = t

    def lookup(self, state: str, symbol: Hashable) -> Optional[Transition]:
        """Return the applicable transition, or None."""
        key = (state, symbol)
        if key in self._rules:
            return self._rules[key]
        for w in self._wildcards:
            if w.state == state:
                return w
        return None

    def __len__(self) -> int:
        return len(self._rules) + len(self._wildcards)

    def __iter__(self) -> Iterator[Transition]:
        return iter(list(self._rules.values()) + self._wildcards)

    def __contains__(self, key: Tuple[str, Hashable]) -> bool:
        state, symbol = key
        if (state, symbol) in self._rules:
            return True
        return any(w.state == state for w in self._wildcards)

    def states(self) -> List[str]:
        """Return all states referenced in the program (both current and next)."""
        s = set()
        for t in self:
            s.add(t.state)
            s.add(t.new_state)
        return sorted(s)

    def symbols(self) -> List[Hashable]:
        """Return all tape symbols referenced in the program."""
        syms = set()
        for t in self:
            syms.add(t.read)
            if isinstance(t.write, tuple):
                syms.update(t.write)
            else:
                syms.add(t.write)
        syms.discard(self.WILDCARD)
        return sorted(syms, key=str)

    def copy(self) -> "Program":
        return Program(self)


# ---------------------------------------------------------------------------
# Base Turing Machine
# ---------------------------------------------------------------------------

@dataclass
class TMStep:
    """A recorded step in a machine's execution history (for debugging)."""
    step: int
    state: str
    tapes: Tuple[Tape, ...]
    transition: Optional[Transition]

    def __str__(self) -> str:
        lines = [f"step {self.step}  state={self.state}"]
        for i, t in enumerate(self.tapes):
            lines.append(f"  tape {i}: {t.render()}")
        if self.transition:
            lines.append(f"  rule: {self.transition}")
        return "\n".join(lines)


class TuringMachine:
    """A single-tape Turing machine.

    Parameters
    ----------
    program : Program or iterable of Transition
        The transition function.
    initial_state : str
        The start state.
    tape : Tape or sequence or None
        Initial tape contents.  If a sequence is given, it becomes the tape.
    blank : Hashable
        The blank symbol (used only if ``tape`` is None).
    halt_states : set of str
        States that cause the machine to halt.  ``{'halt', 'accept', 'reject'}``
        by default.
    max_steps : int
        Safety limit on steps before the machine is considered to be looping.
    """

    def __init__(
        self,
        program: Union[Program, Iterable[Transition]],
        initial_state: str = "q0",
        tape: Union[Tape, Sequence[Hashable], None] = None,
        blank: Hashable = "_",
        halt_states: Optional[set] = None,
        max_steps: int = 1_000_000,
        num_tapes: int = 1,
    ):
        if isinstance(program, Program):
            self.program = program
        else:
            self.program = Program(program)

        self.initial_state = initial_state
        self.halt_states = halt_states if halt_states is not None else {"halt", "accept", "reject", "H", "HALT"}
        self.max_steps = max_steps
        self.num_tapes = num_tapes

        # Build tapes
        if num_tapes == 1:
            if tape is None:
                self.tapes: List[Tape] = [Tape(blank)]
            elif isinstance(tape, Tape):
                self.tapes = [tape]
            else:
                self.tapes = [Tape(blank, tape)]
        else:
            if tape is None:
                self.tapes = [Tape(blank) for _ in range(num_tapes)]
            elif isinstance(tape, Tape):
                self.tapes = [tape] + [Tape(blank) for _ in range(num_tapes - 1)]
            elif isinstance(tape, Sequence) and len(tape) > 0 and isinstance(tape[0], (list, tuple, Tape)):
                self.tapes = [Tape(blank, t) if not isinstance(t, Tape) else t for t in tape]
            else:
                # Single sequence applied to tape 0, rest blank
                self.tapes = [Tape(blank, tape)] + [Tape(blank) for _ in range(num_tapes - 1)]

        self.state = initial_state
        self.steps = 0
        self.halted = False
        self.history: List[TMStep] = []
        self.record_history = False

    # -- execution ----------------------------------------------------------

    def current_symbols(self) -> Tuple[Hashable, ...]:
        """Read the symbol under the head on every tape."""
        return tuple(t.read() for t in self.tapes)

    def _lookup(self) -> Optional[Transition]:
        symbols = self.current_symbols()
        if len(symbols) == 1:
            return self.program.lookup(self.state, symbols[0])
        # Multi-tape: try a composite key first, then wildcard
        key = (self.state, symbols)
        if key in self.program._rules:
            return self.program._rules[key]
        # Fall back to single-symbol rules for single-read transitions
        # (This supports programs that only look at one tape.)
        for w in self.program._wildcards:
            if w.state == self.state:
                return w
        return None

    def step(self) -> bool:
        """Execute one step.  Returns True if the machine can continue, False
        if it has halted (or exceeded ``max_steps``)."""
        if self.halted:
            return False
        if self.steps >= self.max_steps:
            self.halted = True
            return False

        symbols = self.current_symbols()
        t = self._lookup()
        if t is None:
            self.halted = True
            return False

        if self.record_history:
            self.history.append(TMStep(self.steps, self.state, tuple(tp.copy() for tp in self.tapes), t))

        # Apply transition: write symbols, then move heads, then change state
        if isinstance(t.write, tuple):
            for tape, sym in zip(self.tapes, t.write):
                tape.write(sym)
        else:
            self.tapes[0].write(t.write)
        if isinstance(t.direction, tuple):
            for tape, d in zip(self.tapes, t.direction):
                tape.move(d)
        else:
            self.tapes[0].move(t.direction)
        # FIX: set state to the NEW state, not the current state
        self.state = t.new_state

        self.steps += 1
        if self.state in self.halt_states:
            self.halted = True
            return False
        return True

    def run(self, record: bool = False, verbose: bool = False) -> str:
        """Run to completion.  Returns the final state name.

        If ``record`` is True, every step is stored in ``self.history``.
        If ``verbose`` is True, step information is printed to stderr.
        """
        self.record_history = record
        if verbose:
            print(f"start: state={self.state}", file=sys.stderr)
        while self.step():
            if verbose:
                print(self, file=sys.stderr)
        if verbose:
            print(f"halt: state={self.state} after {self.steps} steps", file=sys.stderr)
        return self.state

    # -- query -------------------------------------------------------------

    def tape(self, index: int = 0) -> Tape:
        return self.tapes[index]

    @property
    def result(self) -> List[Hashable]:
        """The contents of tape 0 with blanks stripped."""
        return self.tapes[0].to_list()

    def is_accepted(self) -> bool:
        """Return True if the machine halted in an accepting state.

        A machine is accepted if it halted in an explicit accept/halt state.
        An implicit reject (no transition found) is NOT accepted.
        """
        if not self.halted:
            return False
        # Explicit accept states
        if self.state in ("accept", "HALT", "halt", "H"):
            return True
        # Explicit reject states
        if self.state in ("reject",):
            return False
        # Implicit reject (halted without finding a transition) is NOT accepted
        return False

    def reset(self, tape: Union[Tape, Sequence[Hashable], None] = None) -> None:
        """Reset the machine to its initial state with optional new tape.

        For multi-tape machines, ``tape`` may be a list of sequences (one per
        tape) or a single sequence (applied to tape 0, rest reset to blank).
        If ``tape`` is None, all tapes are reset to blank.
        """
        self.state = self.initial_state
        self.steps = 0
        self.halted = False
        self.history = []
        blank = self.tapes[0].blank
        if tape is not None:
            if self.num_tapes > 1:
                # Multi-tape: tape may be a list of sequences
                if isinstance(tape, Tape):
                    self.tapes = [tape] + [Tape(blank) for _ in range(self.num_tapes - 1)]
                elif isinstance(tape, Sequence) and len(tape) > 0 and isinstance(tape[0], (list, tuple, Tape)):
                    self.tapes = [Tape(blank, t) if not isinstance(t, Tape) else t for t in tape]
                else:
                    self.tapes = [Tape(blank, tape)] + [Tape(blank) for _ in range(self.num_tapes - 1)]
            else:
                if isinstance(tape, Tape):
                    self.tapes = [tape]
                else:
                    self.tapes = [Tape(blank, tape)]
        else:
            self.tapes = [Tape(blank) for _ in range(self.num_tapes)]

    def __str__(self) -> str:
        lines = [f"TuringMachine(state={self.state!r}, steps={self.steps}, halted={self.halted})"]
        for i, t in enumerate(self.tapes):
            lines.append(f"  tape {i}:\n{t.render()}")
        return "\n".join(lines)

    __repr__ = __str__


# ---------------------------------------------------------------------------
# MultiTapeTM
# ---------------------------------------------------------------------------

class MultiTapeTM(TuringMachine):
    """A multi-tape Turing machine.

    Transitions for multi-tape machines use tuples for ``read``, ``write``,
    and ``direction``.  For example, a 2-tape transition::

        Transition("q0", ("0", "_"), ("q1", ("1", "0"), (R, S)))
    """

    def __init__(
        self,
        program: Union[Program, Iterable[Transition]],
        initial_state: str = "q0",
        tapes: Optional[Sequence[Union[Tape, Sequence[Hashable]]]] = None,
        blank: Hashable = "_",
        halt_states: Optional[set] = None,
        max_steps: int = 1_000_000,
        num_tapes: int = 2,
    ):
        # Determine number of tapes
        if tapes is not None:
            num_tapes = len(tapes)
        super().__init__(program, initial_state, None, blank, halt_states, max_steps, num_tapes)
        if tapes is not None:
            blank_sym = blank
            new_tapes = []
            for t in tapes:
                if isinstance(t, Tape):
                    new_tapes.append(t)
                else:
                    new_tapes.append(Tape(blank_sym, t))
            self.tapes = new_tapes


# Backward-compatible alias
Machine = TuringMachine