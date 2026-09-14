"""Validated interval arithmetic for bounding numerical uncertainty."""
from .core import Interval, interval_sum, interval_product

__all__ = ["Interval", "interval_sum", "interval_product"]
__version__ = "0.1.0"
