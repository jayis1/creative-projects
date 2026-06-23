"""Environment / scope chain for the Scheme interpreter."""

from __future__ import annotations

from typing import Any, Optional, Dict


class Environment:
    """A lexical environment with parent chain for variable lookup."""

    __slots__ = ("vars", "parent")

    def __init__(self, parent: Optional["Environment"] = None, init: Optional[Dict[str, Any]] = None):
        self.vars: Dict[str, Any] = dict(init) if init else {}
        self.parent = parent

    def lookup(self, name: str) -> Any:
        env = self
        while env is not None:
            if name in env.vars:
                return env.vars[name]
            env = env.parent
        raise NameError(f"Unbound variable: {name}")

    def set(self, name: str, value: Any) -> bool:
        """Set an existing variable (set!). Returns True if found."""
        env = self
        while env is not None:
            if name in env.vars:
                env.vars[name] = value
                return True
            env = env.parent
        raise NameError(f"Unbound variable: {name}")

    def define(self, name: str, value: Any) -> None:
        """Define a new variable in this environment."""
        self.vars[name] = value

    def child(self, init: Optional[Dict[str, Any]] = None) -> "Environment":
        return Environment(parent=self, init=init)