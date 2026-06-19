"""Colored Petri nets (CPN): tokens carry color (data types).

Extends the basic P/T net model with typed tokens. Each place has a
color set (type), and arcs carry arc inscriptions (functions that
transform token values during firing). This enables modeling of
data-dependent concurrency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .net import PetriNet, Place, Transition, Arc


@dataclass
class ColorSet:
    """A color set defines the type of tokens a place can hold.

    A color set has a name and an optional list of allowed values.
    If ``values`` is None, any value of the given type is allowed.
    """

    name: str
    values: Optional[list[Any]] = None
    type_check: Optional[Callable[[Any], bool]] = None

    def contains(self, val: Any) -> bool:
        """Check if a value belongs to this color set."""
        if self.values is not None:
            return val in self.values
        if self.type_check is not None:
            return self.type_check(val)
        return True  # untyped: accept anything


# Common color sets
INT = ColorSet("int", type_check=lambda v: isinstance(v, int))
STRING = ColorSet("string", type_check=lambda v: isinstance(v, str))
BOOL = ColorSet("bool", type_check=lambda v: v is True or v is False)
UNIT = ColorSet("unit", values=[()])  # unit color — like uncolored


@dataclass
class ColoredToken:
    """A token with a color (data value)."""

    value: Any

    def __repr__(self) -> str:
        return f"●{self.value}"


class ColoredPlace:
    """A place that holds colored tokens.

    The initial marking is a list of token values.
    """

    def __init__(
        self,
        name: str,
        color_set: ColorSet = UNIT,
        initial: Optional[list[Any]] = None,
        capacity: Optional[int] = None,
    ) -> None:
        self.name = name
        self.color_set = color_set
        self.initial: list[Any] = list(initial) if initial else []
        self.capacity = capacity
        # Validate initial tokens
        for val in self.initial:
            if not color_set.contains(val):
                raise ValueError(
                    f"Place '{name}': initial token {val} not in color set '{color_set.name}'"
                )
        if capacity is not None and len(self.initial) > capacity:
            raise ValueError(
                f"Place '{name}': initial tokens exceed capacity {capacity}"
            )

    def __repr__(self) -> str:
        cap = "∞" if self.capacity is None else str(self.capacity)
        return f"ColoredPlace({self.name!r}, cs={self.color_set.name}, tokens={self.initial}, cap={cap})"


@dataclass
class ArcInscription:
    """An arc inscription: a function that transforms tokens during firing.

    For input arcs: ``consume`` selects which tokens to consume from the
    source place. It receives the current list of tokens and returns the
    list of tokens to consume.

    For output arcs: ``produce`` computes the tokens to add to the target
    place. It receives the consumed tokens and returns new tokens.

    The simplest inscriptions just consume/produce a single unit token.
    """

    consume: Callable[[list[Any]], list[Any]]
    produce: Callable[[list[Any]], list[Any]]
    variable: str = ""  # variable name for binding

    @classmethod
    def unit(cls) -> "ArcInscription":
        """Consume/produce a single unit token."""
        return cls(
            consume=lambda tokens: [()] if tokens else [],
            produce=lambda consumed: [()],
        )

    @classmethod
    def identity(cls, var: str = "x") -> "ArcInscription":
        """Pass through a single token (identity)."""
        def consume(tokens: list[Any]) -> list[Any]:
            return [tokens[0]] if tokens else []
        def produce(consumed: list[Any]) -> list[Any]:
            return consumed
        return cls(consume=consume, produce=produce, variable=var)

    @classmethod
    def constant(cls, value: Any) -> "ArcInscription":
        """Produce a constant value (for output arcs)."""
        return cls(
            consume=lambda tokens: [()] if tokens else [],
            produce=lambda consumed: [value],
        )

    @classmethod
    def transform(cls, fn: Callable[[Any], Any], var: str = "x") -> "ArcInscription":
        """Transform a token: consume one, produce a transformed version."""
        def consume(tokens: list[Any]) -> list[Any]:
            return [tokens[0]] if tokens else []
        def produce(consumed: list[Any]) -> list[Any]:
            return [fn(consumed[0])] if consumed else []
        return cls(consume=consume, produce=produce, variable=var)


class ColoredTransition:
    """A transition with a guard that can inspect bound variables."""

    def __init__(
        self,
        name: str,
        guard: Optional[Callable[[dict[str, Any]], bool]] = None,
    ) -> None:
        self.name = name
        self.guard = guard

    def check_guard(self, bindings: dict[str, Any]) -> bool:
        if self.guard is None:
            return True
        return bool(self.guard(bindings))


class ColoredPetriNet:
    """A Colored Petri Net (CPN).

    Places hold colored (typed) tokens. Transitions fire by consuming
    tokens matching arc inscriptions and producing new tokens.
    """

    def __init__(self, name: str = "cpn") -> None:
        self.name = name
        self._places: dict[str, ColoredPlace] = {}
        self._transitions: dict[str, ColoredTransition] = {}
        self._in_arcs: dict[str, list[tuple[str, ArcInscription]]] = {}  # transition -> [(place, inscr)]
        self._out_arcs: dict[str, list[tuple[str, ArcInscription]]] = {}

    def add_place(self, place: ColoredPlace) -> ColoredPlace:
        if place.name in self._places:
            raise ValueError(f"Duplicate place: {place.name}")
        self._places[place.name] = place
        return place

    def add_transition(self, t: ColoredTransition) -> ColoredTransition:
        if t.name in self._transitions:
            raise ValueError(f"Duplicate transition: {t.name}")
        self._transitions[t.name] = t
        self._in_arcs[t.name] = []
        self._out_arcs[t.name] = []
        return t

    def add_arc(
        self,
        place_name: str,
        transition_name: str,
        inscription: Optional[ArcInscription] = None,
        direction: str = "in",  # "in" = place->transition, "out" = transition->place
    ) -> None:
        """Add a colored arc.

        direction="in": place -> transition (consume)
        direction="out": transition -> place (produce)
        """
        if direction == "in":
            self._in_arcs[transition_name].append(
                (place_name, inscription or ArcInscription.identity())
            )
        else:
            self._out_arcs[transition_name].append(
                (place_name, inscription or ArcInscription.identity())
            )

    @property
    def places(self) -> dict[str, ColoredPlace]:
        return self._places

    @property
    def transitions(self) -> dict[str, ColoredTransition]:
        return self._transitions

    def initial_marking(self) -> dict[str, list[Any]]:
        return {p.name: list(p.initial) for p in self._places.values()}

    def is_enabled(
        self,
        transition_name: str,
        marking: dict[str, list[Any]],
    ) -> bool:
        """Check if a transition is enabled.

        A transition is enabled if every input arc's inscription can
        consume at least one token, and the guard (if any) is satisfied.
        """
        t = self._transitions[transition_name]
        bindings: dict[str, Any] = {}

        for place_name, inscr in self._in_arcs[transition_name]:
            tokens = marking.get(place_name, [])
            consumed = inscr.consume(list(tokens))
            if not consumed:
                return False
            if inscr.variable:
                bindings[inscr.variable] = consumed[0]

        if not t.check_guard(bindings):
            return False

        # Check output capacity
        for place_name, inscr in self._out_arcs[transition_name]:
            place = self._places[place_name]
            if place.capacity is not None:
                produced = inscr.produce([])
                current = len(marking.get(place_name, []))
                if current + len(produced) > place.capacity:
                    return False

        return True

    def fire(
        self,
        transition_name: str,
        marking: dict[str, list[Any]],
    ) -> dict[str, list[Any]]:
        """Fire a transition, returning a new marking."""
        if not self.is_enabled(transition_name, marking):
            raise RuntimeError(f"Transition '{transition_name}' not enabled")

        new_marking: dict[str, list[Any]] = {k: list(v) for k, v in marking.items()}
        consumed_tokens: dict[str, list[Any]] = {}

        # Consume
        for place_name, inscr in self._in_arcs[transition_name]:
            tokens = new_marking.get(place_name, [])
            consumed = inscr.consume(list(tokens))
            consumed_tokens[place_name] = consumed
            # Remove consumed tokens
            remaining = list(tokens)
            for ct in consumed:
                if ct in remaining:
                    remaining.remove(ct)
            new_marking[place_name] = remaining

        # Produce
        for place_name, inscr in self._out_arcs[transition_name]:
            # Collect consumed tokens from input arcs with matching variable
            consumed_for_produce = []
            for pn, ins in self._in_arcs[transition_name]:
                if ins.variable == inscr.variable:
                    consumed_for_produce = consumed_tokens.get(pn, [])
                    break
            produced = inscr.produce(consumed_for_produce)
            new_marking.setdefault(place_name, [])
            new_marking[place_name] = list(new_marking.get(place_name, [])) + produced

        return new_marking

    def enabled_transitions(self, marking: dict[str, list[Any]]) -> list[str]:
        return [t for t in self._transitions if self.is_enabled(t, marking)]

    def __repr__(self) -> str:
        return (
            f"ColoredPetriNet(name={self.name!r}, "
            f"places={len(self._places)}, transitions={len(self._transitions)})"
        )