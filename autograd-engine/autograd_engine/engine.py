"""Reverse-mode automatic differentiation engine over scalar ``Value`` nodes.

Each ``Value`` holds a float ``data``, a float ``grad``, a reference to the
function that produced it (``_backward``) and its parents (``_prev``) so that a
topological sort can reconstruct the computation order needed for backprop.

The engine supports a rich set of operations:
    Arithmetic:  +, -, *, /, **, unary -
    Transcend.:  tanh, relu, exp, log, sigmoid
    Reductions:  (see ``ops`` module for sum/max over sequences)

Every op records a closure that propagates the output gradient to its inputs
via the chain rule.  ``Value.backward()`` walks the graph in reverse
topological order accumulating gradients.
"""

from __future__ import annotations

import math
from typing import Callable, Iterable, Iterator, List, Optional, Set


class Value:
    """A node in the autodiff computational graph.

    ``Value`` objects behave like Python floats for arithmetic and support a
    growing set of transcendental functions.  Every operation records its own
    local-derivative closure so that :meth:`backward` can walk the graph in
    reverse topological order and accumulate gradients via the chain rule.

    Gradients are *accumulated* (+=) so that a node used in multiple places in
    the graph receives the sum of all partial contributions — this is the
    correct behaviour for reverse-mode autodiff and means you can reuse
    sub-expressions freely.
    """

    __slots__ = ("data", "grad", "_backward", "_prev", "_op", "label")

    # ------------------------------------------------------------------ #
    # construction
    # ------------------------------------------------------------------ #
    def __init__(
        self,
        data: float,
        _children: Iterable["Value"] = (),
        _op: str = "",
        label: Optional[str] = None,
    ) -> None:
        if not isinstance(data, (int, float)):
            raise TypeError(
                f"Value data must be a number, got {type(data).__name__}"
            )
        self.data = float(data)
        self.grad = 0.0
        # closure that propagates gradients to parents; identity for leaves
        self._backward: Callable[[], None] = lambda: None
        self._prev: tuple["Value", ...] = tuple(_children)
        self._op = _op
        self.label = label

    # ------------------------------------------------------------------ #
    # arithmetic
    # ------------------------------------------------------------------ #
    def __add__(self, other: "Value | float") -> "Value":
        other = other if isinstance(other, Value) else Value(other)
        out = Value(self.data + other.data, (self, other), "+")

        def _backward() -> None:
            self.grad += out.grad
            other.grad += out.grad

        out._backward = _backward
        return out

    def __mul__(self, other: "Value | float") -> "Value":
        other = other if isinstance(other, Value) else Value(other)
        out = Value(self.data * other.data, (self, other), "*")

        def _backward() -> None:
            self.grad += other.data * out.grad
            other.grad += self.data * out.grad

        out._backward = _backward
        return out

    def __pow__(self, other: "Value | float | int") -> "Value":
        # Supports both constant and Value exponents.
        if isinstance(other, Value):
            # d/dx (x^y) = x^y * (y' * ln(x) + y * x'/x)
            # For x^y where both can vary:
            #   d/dx = y * x^(y-1)
            #   d/dy = x^y * ln(x)
            if self.data <= 0:
                raise ValueError(
                    "Value**Value requires base > 0 for stable gradient (ln)"
                )
            out = Value(self.data ** other.data, (self, other), f"**")

            def _backward() -> None:
                self.grad += (
                    other.data * self.data ** (other.data - 1)
                ) * out.grad
                other.grad += (out.data * math.log(self.data)) * out.grad

            out._backward = _backward
            return out
        # constant exponent
        if not isinstance(other, (int, float)):
            raise TypeError("Value**exponent requires a numeric or Value exponent")
        out = Value(self.data ** other, (self,), f"**{other}")

        def _backward() -> None:
            self.grad += (other * self.data ** (other - 1)) * out.grad

        out._backward = _backward
        return out

    # ------------------------------------------------------------------ #
    # transcendental / activation functions
    # ------------------------------------------------------------------ #
    def relu(self) -> "Value":
        out = Value(self.data if self.data > 0 else 0.0, (self,), "relu")

        def _backward() -> None:
            self.grad += (1.0 if out.data > 0 else 0.0) * out.grad

        out._backward = _backward
        return out

    def tanh(self) -> "Value":
        t = math.tanh(self.data)
        out = Value(t, (self,), "tanh")

        def _backward() -> None:
            self.grad += (1 - t * t) * out.grad

        out._backward = _backward
        return out

    def sigmoid(self) -> "Value":
        """Numerically-stable logistic sigmoid 1/(1+e^-x)."""
        # Use stable computation to avoid overflow in exp for large negatives
        if self.data >= 0:
            z = math.exp(-self.data)
            s = 1.0 / (1.0 + z)
        else:
            z = math.exp(self.data)
            s = z / (1.0 + z)
        out = Value(s, (self,), "sigmoid")

        def _backward() -> None:
            self.grad += (s * (1 - s)) * out.grad

        out._backward = _backward
        return out

    def exp(self) -> "Value":
        e = math.exp(self.data)
        out = Value(e, (self,), "exp")

        def _backward() -> None:
            self.grad += out.data * out.grad

        out._backward = _backward
        return out

    def log(self) -> "Value":
        if self.data <= 0:
            raise ValueError(f"log() requires positive data, got {self.data}")
        out = Value(math.log(self.data), (self,), "log")

        def _backward() -> None:
            self.grad += (1.0 / self.data) * out.grad

        out._backward = _backward
        return out

    # ------------------------------------------------------------------ #
    # sugar / reflected ops
    # ------------------------------------------------------------------ #
    def __neg__(self) -> "Value":
        return self * -1

    def __sub__(self, other: "Value | float") -> "Value":
        return self + (-other if isinstance(other, Value) else -other)

    def __radd__(self, other: "Value | float") -> "Value":
        return self + other

    def __rsub__(self, other: "Value | float") -> "Value":
        return (-self) + other

    def __rmul__(self, other: "Value | float") -> "Value":
        return self * other

    def __truediv__(self, other: "Value | float") -> "Value":
        if isinstance(other, Value):
            if other.data == 0:
                raise ZeroDivisionError("division by a Value whose data is 0")
        elif other == 0:
            raise ZeroDivisionError("division by zero")
        return self * (other ** -1)

    def __rtruediv__(self, other: "Value | float") -> "Value":
        return (self ** -1) * other

    def __rpow__(self, other: "Value | float") -> "Value":
        base = other if isinstance(other, Value) else Value(other)
        return base ** self

    # ------------------------------------------------------------------ #
    # backprop
    # ------------------------------------------------------------------ #
    def _build_topo(self, visited: Set[int], topo: List["Value"]) -> None:
        if id(self) not in visited:
            visited.add(id(self))
            for child in self._prev:
                child._build_topo(visited, topo)
            topo.append(self)

    def backward(self) -> None:
        """Run reverse-mode autodiff starting from this node (the loss).

        Builds a topological ordering of the entire subgraph, zeros all
        gradients, seeds this node with grad=1, then walks in reverse calling
        each node's ``_backward`` closure.
        """
        topo: List[Value] = []
        self._build_topo(set(), topo)
        # zero all grads in the graph first
        for node in topo:
            node.grad = 0.0
        # seed
        self.grad = 1.0
        for node in reversed(topo):
            node._backward()

    # ------------------------------------------------------------------ #
    # misc
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:
        return f"Value(data={self.data:.6f}, grad={self.grad:.6f})"

    def __float__(self) -> float:
        return self.data

    def __eq__(self, other: object) -> bool:  # type: ignore[override]
        if isinstance(other, Value):
            return self.data == other.data
        if isinstance(other, (int, float)):
            return self.data == other
        return NotImplemented

    def __hash__(self) -> int:
        return id(self)

    def __iter__(self) -> Iterator["Value"]:
        raise TypeError(f"'{type(self).__name__}' object is not iterable")