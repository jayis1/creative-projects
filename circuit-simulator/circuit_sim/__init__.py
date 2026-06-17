"""
circuit-simulator: A digital circuit simulator with propagation delays,
composite circuits, oscilloscope output, and a circuit description language.
"""

from .core import Signal, Wire
from .gates import (
    AndGate, OrGate, NotGate, XorGate, NandGate, NorGate, XnorGate,
    BufferGate, TriStateBuffer,
)
from .sequential import SRLatch, DLatch, DFlipFlop, JKFlipFlop, TFlipFlop, Clock
from .circuit import Circuit
from .simulator import Simulator
from .cdl import parse_cdl
from .scope import Oscilloscope

__version__ = "1.0.0"
__all__ = [
    "Signal", "Wire",
    "AndGate", "OrGate", "NotGate", "XorGate", "NandGate", "NorGate", "XnorGate",
    "BufferGate", "TriStateBuffer",
    "SRLatch", "DLatch", "DFlipFlop", "JKFlipFlop", "TFlipFlop", "Clock",
    "Circuit", "Simulator", "parse_cdl", "Oscilloscope",
]