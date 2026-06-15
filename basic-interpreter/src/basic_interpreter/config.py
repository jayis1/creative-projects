"""Configuration for the BASIC interpreter."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class InterpreterConfig:
    """Configuration options for the BASIC interpreter.

    Attributes:
        max_iterations: Maximum number of iterations before raising
            a BasicRuntimeError. Prevents infinite loops.
            Default: 10,000,000.
        zone_width: Column width for PRINT comma (,) zones.
            Default: 14 (standard BASIC).
        trace: Whether to print line numbers during execution.
            Default: False.
        random_seed: Optional seed for the RND function.
            If None, uses Python's default random seed.
            Default: None.
    """

    max_iterations: int = 10_000_000
    zone_width: int = 14
    trace: bool = False
    random_seed: int | None = None