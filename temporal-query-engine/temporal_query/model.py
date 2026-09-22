"""Immutable temporal records and Allen interval relations."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class Relation(str, Enum):
    BEFORE = "before"
    AFTER = "after"
    MEETS = "meets"
    MET_BY = "met_by"
    OVERLAPS = "overlaps"
    OVERLAPPED_BY = "overlapped_by"
    STARTS = "starts"
    STARTED_BY = "started_by"
    DURING = "during"
    CONTAINS = "contains"
    FINISHES = "finishes"
    FINISHED_BY = "finished_by"
    EQUALS = "equals"

@dataclass(frozen=True, slots=True)
class Event:
    """A half-open interval [start, end), optionally labelled."""
    id: str
    start: float
    end: float
    label: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("event id must not be empty")
        if self.start >= self.end:
            raise ValueError("event start must be less than end")

    def relation_to(self, other: "Event") -> Relation:
        a, b, c, d = self.start, self.end, other.start, other.end
        if b < c: return Relation.BEFORE
        if b == c: return Relation.MEETS
        if a > d: return Relation.AFTER
        if a == d: return Relation.MET_BY
        if a == c and b == d: return Relation.EQUALS
        if a == c: return Relation.STARTS if b < d else Relation.STARTED_BY
        if b == d: return Relation.FINISHES if a > c else Relation.FINISHED_BY
        if c < a and b < d: return Relation.DURING
        if a < c and d < b: return Relation.CONTAINS
        if a < c: return Relation.OVERLAPS
        return Relation.OVERLAPPED_BY
