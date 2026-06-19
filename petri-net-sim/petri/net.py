"""Core Petri net model: Place, Transition, Arc, PetriNet."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable, Iterator, Optional


class ValidationError(ValueError):
    """Raised when a net is structurally or semantically invalid."""


class FiringError(RuntimeError):
    """Raised when a transition cannot fire (not enabled)."""


@dataclass
class Place:
    """A place holding tokens.

    Parameters
    ----------
    name : str
        Human-readable identifier.
    initial : int
        Initial token count (>= 0).
    capacity : int | None
        Maximum tokens allowed. ``None`` means unbounded.
    """

    name: str
    initial: int = 0
    capacity: Optional[int] = None

    def __post_init__(self) -> None:
        if self.initial < 0:
            raise ValidationError(f"Place '{self.name}': initial tokens must be >= 0")
        if self.capacity is not None and self.initial > self.capacity:
            raise ValidationError(
                f"Place '{self.name}': initial {self.initial} exceeds capacity {self.capacity}"
            )

    def __repr__(self) -> str:
        cap = "∞" if self.capacity is None else str(self.capacity)
        return f"Place({self.name!r}, initial={self.initial}, capacity={cap})"

    def __hash__(self) -> int:
        return id(self)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Place):
            return self.name == other.name
        if isinstance(other, str):
            return self.name == other
        return NotImplemented

    def to_dict(self) -> dict:
        return {"name": self.name, "initial": self.initial, "capacity": self.capacity}

    @classmethod
    def from_dict(cls, d: dict) -> "Place":
        return cls(name=d["name"], initial=d.get("initial", 0), capacity=d.get("capacity"))


@dataclass
class Arc:
    """A weighted directed arc from a node (Place/Transition) to another."""

    source: str
    target: str
    weight: int = 1

    def __post_init__(self) -> None:
        if self.weight <= 0:
            raise ValidationError(f"Arc {self.source}->{self.target}: weight must be >= 1")

    def to_dict(self) -> dict:
        return {"source": self.source, "target": self.target, "weight": self.weight}


@dataclass
class Transition:
    """A transition with optional guard function.

    The guard receives the current marking dict {place_name: tokens}
    and returns ``True`` if the transition may fire.
    """

    name: str
    guard: Optional[Callable[[dict[str, int]], bool]] = None
    label: str = ""

    def __hash__(self) -> int:
        return id(self)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Transition):
            return self.name == other.name
        if isinstance(other, str):
            return self.name == other.name
        return NotImplemented

    def __repr__(self) -> str:
        return f"Transition({self.name!r})"

    def check_guard(self, marking: dict[str, int]) -> bool:
        if self.guard is None:
            return True
        return bool(self.guard(marking))

    def to_dict(self) -> dict:
        return {"name": self.name, "label": self.label}

    @classmethod
    def from_dict(cls, d: dict) -> "Transition":
        return cls(name=d["name"], label=d.get("label", ""))


class PetriNet:
    """A Place/Transition (P/T) net.

    Arcs connect Places to Transitions and vice versa.
    Each arc has an integer weight (multiplicity).
    """

    def __init__(self, name: str = "net") -> None:
        self.name = name
        self._places: dict[str, Place] = {}
        self._transitions: dict[str, Transition] = {}
        # adjacency
        self._in_arcs: dict[str, list[Arc]] = {}   # transition -> incoming arcs (from places)
        self._out_arcs: dict[str, list[Arc]] = {}   # transition -> outgoing arcs (to places)
        self._place_in: dict[str, list[Arc]] = {}    # place -> incoming arcs (from transitions)
        self._place_out: dict[str, list[Arc]] = {}  # place -> outgoing arcs (to transitions)

    # ------------------------------------------------------------------
    # Building
    # ------------------------------------------------------------------
    def add_place(self, place: Place) -> Place:
        if place.name in self._places:
            raise ValidationError(f"Duplicate place name: {place.name}")
        if place.name in self._transitions:
            raise ValidationError(f"Name '{place.name}' already used as a transition")
        self._places[place.name] = place
        self._place_in[place.name] = []
        self._place_out[place.name] = []
        return place

    def add_transition(self, t: Transition) -> Transition:
        if t.name in self._transitions:
            raise ValidationError(f"Duplicate transition name: {t.name}")
        if t.name in self._places:
            raise ValidationError(f"Name '{t.name}' already used as a place")
        self._transitions[t.name] = t
        self._in_arcs[t.name] = []
        self._out_arcs[t.name] = []
        return t

    def add_arc(self, source: str, target: str, weight: int = 1) -> Arc:
        """Add a weighted arc between a place and a transition (either direction)."""
        if weight <= 0:
            raise ValidationError("Arc weight must be >= 1")
        if source in self._places and target in self._transitions:
            arc = Arc(source=source, target=target, weight=weight)
            self._place_out[source].append(arc)
            self._in_arcs[target].append(arc)
            return arc
        elif source in self._transitions and target in self._places:
            arc = Arc(source=source, target=target, weight=weight)
            self._out_arcs[source].append(arc)
            self._place_in[target].append(arc)
            return arc
        else:
            raise ValidationError(
                f"Arc {source}->{target}: must connect a place to a transition (or vice versa)"
            )

    def place(self, name: str) -> Place:
        if name not in self._places:
            raise KeyError(f"No such place: {name}")
        return self._places[name]

    def transition(self, name: str) -> Transition:
        if name not in self._transitions:
            raise KeyError(f"No such transition: {name}")
        return self._transitions[name]

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def places(self) -> dict[str, Place]:
        return self._places

    @property
    def transitions(self) -> dict[str, Transition]:
        return self._transitions

    def initial_marking(self) -> dict[str, int]:
        return {p.name: p.initial for p in self._places.values()}

    def input_arcs(self, transition_name: str) -> list[Arc]:
        """Arcs from places INTO this transition (preconditions)."""
        return self._in_arcs.get(transition_name, [])

    def output_arcs(self, transition_name: str) -> list[Arc]:
        """Arcs from this transition to places (postconditions)."""
        return self._out_arcs.get(transition_name, [])

    def preset(self, transition_name: str) -> set[str]:
        """Places that feed INTO this transition."""
        return {a.source for a in self._in_arcs.get(transition_name, [])}

    def postset(self, transition_name: str) -> set[str]:
        """Places fed BY this transition."""
        return {a.target for a in self._out_arcs.get(transition_name, [])}

    def place_preset(self, place_name: str) -> set[str]:
        """Transitions that feed INTO this place."""
        return {a.source for a in self._place_in.get(place_name, [])}

    def place_postset(self, place_name: str) -> set[str]:
        """Transitions that consume FROM this place."""
        return {a.target for a in self._place_out.get(place_name, [])}

    # ------------------------------------------------------------------
    # Firing semantics
    # ------------------------------------------------------------------
    def is_enabled(self, transition_name: str, marking: dict[str, int]) -> bool:
        """Check whether ``transition_name`` is enabled in ``marking``.

        A transition is enabled iff:
        1. Every input place has at least ``arc.weight`` tokens.
        2. Firing would not exceed any place's capacity.
        3. The guard (if any) returns True.
        """
        if transition_name not in self._transitions:
            raise KeyError(f"No such transition: {transition_name}")
        t = self._transitions[transition_name]
        if not t.check_guard(marking):
            return False
        for arc in self._in_arcs[transition_name]:
            if marking.get(arc.source, 0) < arc.weight:
                return False
        # capacity check for output places
        for arc in self._out_arcs[transition_name]:
            place = self._places[arc.target]
            if place.capacity is not None:
                produced = arc.weight
                consumed = 0
                # net change = produced - consumed
                # a place could be both input and output
                for ia in self._in_arcs[transition_name]:
                    if ia.source == arc.target:
                        consumed += ia.weight
                new_tokens = marking.get(arc.target, 0) + produced - consumed
                if new_tokens > place.capacity:
                    return False
        return True

    def enabled_transitions(self, marking: dict[str, int]) -> list[str]:
        return [t for t in self._transitions if self.is_enabled(t, marking)]

    def fire(self, transition_name: str, marking: dict[str, int]) -> dict[str, int]:
        """Fire ``transition_name`` and return a NEW marking dict.

        Raises ``FiringError`` if the transition is not enabled.
        The input ``marking`` is not modified.
        """
        if not self.is_enabled(transition_name, marking):
            raise FiringError(f"Transition '{transition_name}' is not enabled")
        new_marking = dict(marking)
        for arc in self._in_arcs[transition_name]:
            new_marking[arc.source] -= arc.weight
        for arc in self._out_arcs[transition_name]:
            new_marking[arc.target] = new_marking.get(arc.target, 0) + arc.weight
        return new_marking

    def fire_inplace(self, transition_name: str, marking: dict[str, int]) -> None:
        """Fire in-place: mutate ``marking`` directly (no copy)."""
        if not self.is_enabled(transition_name, marking):
            raise FiringError(f"Transition '{transition_name}' is not enabled")
        for arc in self._in_arcs[transition_name]:
            marking[arc.source] -= arc.weight
        for arc in self._out_arcs[transition_name]:
            marking[arc.target] = marking.get(arc.target, 0) + arc.weight

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self) -> list[str]:
        """Check structural validity. Returns list of warning strings (empty if OK)."""
        warnings: list[str] = []
        for t_name in self._transitions:
            if not self._in_arcs[t_name] and not self._out_arcs[t_name]:
                warnings.append(f"Transition '{t_name}' has no arcs (isolated)")
        for p_name in self._places:
            if not self._place_in[p_name] and not self._place_out[p_name]:
                warnings.append(f"Place '{p_name}' has no arcs (isolated)")
        # check all arc endpoints exist
        for arc_list in self._in_arcs.values():
            for a in arc_list:
                if a.source not in self._places:
                    warnings.append(f"Arc {a.source}->{a.target}: source place missing")
        for arc_list in self._out_arcs.values():
            for a in arc_list:
                if a.target not in self._places:
                    warnings.append(f"Arc {a.source}->{a.target}: target place missing")
        return warnings

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "places": [p.to_dict() for p in self._places.values()],
            "transitions": [t.to_dict() for t in self._transitions.values()],
            "arcs": (
                [a.to_dict() for arcs in self._in_arcs.values() for a in arcs]
                + [a.to_dict() for arcs in self._out_arcs.values() for a in arcs]
            ),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, d: dict) -> "PetriNet":
        net = cls(name=d.get("name", "net"))
        for pd in d.get("places", []):
            net.add_place(Place.from_dict(pd))
        for td in d.get("transitions", []):
            net.add_transition(Transition.from_dict(td))
        seen = set()
        for ad in d.get("arcs", []):
            key = (ad["source"], ad["target"])
            if key in seen:
                continue
            seen.add(key)
            net.add_arc(ad["source"], ad["target"], ad.get("weight", 1))
        return net

    @classmethod
    def from_json(cls, s: str) -> "PetriNet":
        return cls.from_dict(json.loads(s))

    def __repr__(self) -> str:
        return (
            f"PetriNet(name={self.name!r}, "
            f"places={len(self._places)}, "
            f"transitions={len(self._transitions)})"
        )