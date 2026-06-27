"""
crdt-engine: Conflict-free Replicated Data Types for Python.

A comprehensive library implementing both state-based (CvRDT) and
operation-based (CmRDT) CRDTs, vector clocks, a simulated network layer
with partition support, and Merkle-tree-based anti-entropy synchronisation.

Public modules
--------------
- ``vector_clock`` -- VectorClock with happens-before / concurrent detection
- ``counter``      -- G-Counter, PN-Counter, state + op based
- ``set``          -- G-Set, 2P-Set, LWW-Set, OR-Set, state + op based
- ``register``     -- LWW-Register, MV-Register
- ``sequence``     -- LWW-Element-Set sequence (insert/delete by UID)
- ``map``          -- OR-Map (add/remove tracking)
- ``network``      -- Simulated network with latency, loss, reordering, partitions
- ``sync``         -- Merkle tree anti-entropy + full-state sync
- ``cli``          -- Command-line interface
- ``config``       -- Configuration loading (JSON/YAML/TOML)

Typical usage::

    from crdt_engine import PNCounter, VectorClock

    a = PNCounter("A")
    b = PNCounter("B")
    a.increment(3)
    b.increment(5)
    a.merge(b.state())
    b.merge(a.state())
    assert a.value() == b.value() == 8
"""

from .vector_clock import VectorClock
from .counter import GCounter, PNCounter, OpGCounter, OpPNCounter
from .set import GSet, TwoPSet, LWWSet, ORSet
from .register import LWWRegister, MVRegister
from .sequence import SequenceCRDT
from .map import ORMap
from .network import Network, Node, Message
from .sync import MerkleTree, AntiEntropy
from .config import Config

__version__ = "1.0.0"
__all__ = [
    "VectorClock",
    "GCounter",
    "PNCounter",
    "OpGCounter",
    "OpPNCounter",
    "GSet",
    "TwoPSet",
    "LWWSet",
    "ORSet",
    "LWWRegister",
    "MVRegister",
    "SequenceCRDT",
    "ORMap",
    "Network",
    "Node",
    "Message",
    "MerkleTree",
    "AntiEntropy",
    "Config",
]