"""Interval algebra and indexed temporal queries."""
from .model import Event, Relation
from .index import IntervalIndex

__all__ = ["Event", "Relation", "IntervalIndex"]
