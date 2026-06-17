"""Core signal and wire types for the circuit simulator."""

from __future__ import annotations
from enum import Enum, auto
from typing import Optional, List, Callable


class Signal(Enum):
    """Digital signal values with support for high-impedance and undefined states."""
    LOW = 0
    HIGH = 1
    UNDEFINED = auto()
    HIGH_IMPEDANCE = auto()  # Used for tri-state buffers

    def __invert__(self) -> Signal:
        """Logical NOT."""
        if self == Signal.LOW:
            return Signal.HIGH
        if self == Signal.HIGH:
            return Signal.LOW
        return Signal.UNDEFINED

    def __and__(self, other: Signal) -> Signal:
        """Logical AND."""
        if self == Signal.HIGH and other == Signal.HIGH:
            return Signal.HIGH
        if self == Signal.UNDEFINED or other == Signal.UNDEFINED:
            return Signal.UNDEFINED
        if self == Signal.HIGH_IMPEDANCE or other == Signal.HIGH_IMPEDANCE:
            return Signal.UNDEFINED
        return Signal.LOW

    def __or__(self, other: Signal) -> Signal:
        """Logical OR."""
        if self == Signal.HIGH or other == Signal.HIGH:
            return Signal.HIGH
        if self == Signal.UNDEFINED or other == Signal.UNDEFINED:
            return Signal.UNDEFINED
        if self == Signal.HIGH_IMPEDANCE or other == Signal.HIGH_IMPEDANCE:
            return Signal.UNDEFINED
        return Signal.LOW

    def __xor__(self, other: Signal) -> Signal:
        """Logical XOR."""
        if self == Signal.UNDEFINED or other == Signal.UNDEFINED:
            return Signal.UNDEFINED
        if self == Signal.HIGH_IMPEDANCE or other == Signal.HIGH_IMPEDANCE:
            return Signal.UNDEFINED
        if (self == Signal.HIGH) != (other == Signal.HIGH):
            return Signal.HIGH
        return Signal.LOW

    def to_int(self) -> int:
        """Convert to integer (0 or 1). Raises ValueError for undefined/high-impedance."""
        if self == Signal.LOW:
            return 0
        if self == Signal.HIGH:
            return 1
        raise ValueError(f"Cannot convert {self.name} to int")

    @classmethod
    def from_bool(cls, value: bool) -> Signal:
        """Create a Signal from a boolean."""
        return cls.HIGH if value else cls.LOW

    @classmethod
    def from_int(cls, value: int) -> Signal:
        """Create a Signal from an integer (0 or 1)."""
        if value == 0:
            return cls.LOW
        if value == 1:
            return cls.HIGH
        return cls.UNDEFINED


class Wire:
    """
    A wire connects component outputs to component inputs. It propagates signals
    with an optional propagation delay and supports multiple listeners.
    """

    def __init__(self, name: str, initial: Signal = Signal.UNDEFINED, delay_ns: int = 0):
        self.name = name
        self._signal = initial
        self._delay_ns = delay_ns
        self._listeners: List[Callable[[Signal, str], None]] = []
        self._history: List[tuple] = []  # (time_ns, signal)

    @property
    def signal(self) -> Signal:
        """Current signal value on this wire."""
        return self._signal

    @signal.setter
    def signal(self, value: Signal) -> None:
        """Set the signal value and notify listeners."""
        old = self._signal
        if old != value:
            self._signal = value
            for listener in self._listeners:
                listener(value, self.name)

    def connect(self, listener: Callable[[Signal, str], None]) -> None:
        """Connect a listener that will be called when the wire signal changes."""
        self._listeners.append(listener)

    def record(self, time_ns: int) -> None:
        """Record the current signal value at the given time for oscilloscope traces."""
        self._history.append((time_ns, self._signal))

    @property
    def history(self) -> List[tuple]:
        """Return the signal history as list of (time_ns, Signal) tuples."""
        return list(self._history)

    def clear_history(self) -> None:
        """Clear the signal history."""
        self._history.clear()

    def __repr__(self) -> str:
        return f"Wire({self.name!r}, {self._signal.name})"


class Bus:
    """
    A bus is a named collection of wires representing a multi-bit signal.
    Provides convenience methods for reading/writing integer values.
    """

    def __init__(self, name: str, width: int, initial: Signal = Signal.LOW):
        self.name = name
        self.width = width
        self.wires: List[Wire] = [
            Wire(f"{name}[{i}]", initial) for i in range(width)
        ]

    def write_int(self, value: int) -> None:
        """Write an integer value onto the bus wires (LSB first)."""
        for i, wire in enumerate(self.wires):
            bit = (value >> i) & 1
            wire.signal = Signal.from_int(bit)

    def read_int(self) -> int:
        """Read the bus wires as an integer (LSB first). Returns -1 if any wire is undefined."""
        result = 0
        for i, wire in enumerate(self.wires):
            if wire.signal == Signal.UNDEFINED or wire.signal == Signal.HIGH_IMPEDANCE:
                return -1
            if wire.signal == Signal.HIGH:
                result |= (1 << i)
        return result

    def __getitem__(self, index: int) -> Wire:
        return self.wires[index]

    def __len__(self) -> int:
        return self.width

    def __repr__(self) -> str:
        return f"Bus({self.name!r}, width={self.width})"