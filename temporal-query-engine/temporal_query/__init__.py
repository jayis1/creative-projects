"""Interval algebra and indexed temporal queries."""
from .model import Event, Relation
from .index import IntervalIndex
from .config import load_events

__all__ = ["Event", "Relation", "IntervalIndex", "load_events"]
