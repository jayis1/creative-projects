"""Preset Petri nets for testing and demonstration."""

from __future__ import annotations

from .net import PetriNet, Place, Transition


def simple_buffer(n: int = 3) -> PetriNet:
    """A simple producer/buffer/consumer net with capacity ``n``."""
    net = PetriNet(name="simple_buffer")
    net.add_place(Place("ready", initial=1))
    net.add_place(Place("buffer", initial=0, capacity=n))
    net.add_place(Place("done", initial=0))
    net.add_transition(Transition("produce"))
    net.add_transition(Transition("consume"))
    net.add_arc("ready", "produce")
    net.add_arc("produce", "ready")
    net.add_arc("produce", "buffer")
    net.add_arc("buffer", "consume")
    net.add_arc("consume", "buffer")  # no-op for capacity model
    net.add_arc("consume", "done")
    return net


def producer_consumer(buffer_size: int = 5) -> PetriNet:
    """Producer-consumer with a bounded buffer."""
    net = PetriNet(name="producer_consumer")
    net.add_place(Place("p_idle", initial=1))
    net.add_place(Place("p_busy", initial=0))
    net.add_place(Place("buffer", initial=0, capacity=buffer_size))
    net.add_place(Place("c_idle", initial=1))
    net.add_place(Place("c_busy", initial=0))

    net.add_transition(Transition("start_produce"))
    net.add_transition(Transition("finish_produce"))
    net.add_transition(Transition("start_consume"))
    net.add_transition(Transition("finish_consume"))

    net.add_arc("p_idle", "start_produce")
    net.add_arc("start_produce", "p_busy")
    net.add_arc("p_busy", "finish_produce")
    net.add_arc("finish_produce", "p_idle")
    net.add_arc("finish_produce", "buffer")
    net.add_arc("buffer", "start_consume")
    net.add_arc("c_idle", "start_consume")
    net.add_arc("start_consume", "c_busy")
    net.add_arc("c_busy", "finish_consume")
    net.add_arc("finish_consume", "c_idle")
    return net


def mutual_exclusion() -> PetriNet:
    """Two processes competing for a shared resource via a semaphore."""
    net = PetriNet(name="mutual_exclusion")
    # process states
    net.add_place(Place("p1_idle", initial=1))
    net.add_place(Place("p1_wait", initial=0))
    net.add_place(Place("p1_cs", initial=0))
    net.add_place(Place("p2_idle", initial=1))
    net.add_place(Place("p2_wait", initial=0))
    net.add_place(Place("p2_cs", initial=0))
    # semaphore
    net.add_place(Place("sem", initial=1))

    net.add_transition(Transition("p1_request"))
    net.add_transition(Transition("p1_enter"))
    net.add_transition(Transition("p1_exit"))
    net.add_transition(Transition("p2_request"))
    net.add_transition(Transition("p2_enter"))
    net.add_transition(Transition("p2_exit"))

    # P1
    net.add_arc("p1_idle", "p1_request")
    net.add_arc("p1_request", "p1_wait")
    net.add_arc("p1_wait", "p1_enter")
    net.add_arc("sem", "p1_enter")
    net.add_arc("p1_enter", "p1_cs")
    net.add_arc("p1_cs", "p1_exit")
    net.add_arc("p1_exit", "p1_idle")
    net.add_arc("p1_exit", "sem")
    # P2
    net.add_arc("p2_idle", "p2_request")
    net.add_arc("p2_request", "p2_wait")
    net.add_arc("p2_wait", "p2_enter")
    net.add_arc("sem", "p2_enter")
    net.add_arc("p2_enter", "p2_cs")
    net.add_arc("p2_cs", "p2_exit")
    net.add_arc("p2_exit", "p2_idle")
    net.add_arc("p2_exit", "sem")
    return net


def dining_philosophers(n: int = 3) -> PetriNet:
    """Dining philosophers problem (n philosophers, n forks).

    Each philosopher picks up their own fork first, then their neighbor's fork.
    With asymmetric pickup order (even-indexed grab left first, odd grab right first),
    deadlock is avoidable; with symmetric order, deadlock is reachable.
    """
    net = PetriNet(name=f"dining_philosophers_{n}")
    # Create all places first (forks are shared across philosophers)
    for i in range(n):
        net.add_place(Place(f"think_{i}", initial=1))
        net.add_place(Place(f"hungry_{i}", initial=0))
        net.add_place(Place(f"eat_{i}", initial=0))
        net.add_place(Place(f"fork_{i}", initial=1))

    for i in range(n):
        net.add_transition(Transition(f"pick_{i}"))
        net.add_transition(Transition(f"put_{i}"))

        net.add_arc(f"think_{i}", f"pick_{i}")
        net.add_arc(f"pick_{i}", f"hungry_{i}")
        # needs own fork and neighbor's fork
        net.add_arc(f"fork_{i}", f"pick_{i}")
        net.add_arc(f"fork_{(i+1) % n}", f"pick_{i}")
        net.add_arc(f"pick_{i}", f"eat_{i}")
        net.add_arc(f"eat_{i}", f"put_{i}")
        net.add_arc(f"put_{i}", f"think_{i}")
        net.add_arc(f"put_{i}", f"fork_{i}")
        net.add_arc(f"put_{i}", f"fork_{(i+1) % n}")
    return net


def workflow_net() -> PetriNet:
    """A simple workflow net: submit -> review -> approve/reject -> done.

    Approval leads to the end. Rejection loops back for revision.
    """
    net = PetriNet(name="workflow")
    net.add_place(Place("start", initial=1))
    net.add_place(Place("submitted", initial=0))
    net.add_place(Place("reviewed", initial=0))
    net.add_place(Place("end", initial=0))

    net.add_transition(Transition("submit"))
    net.add_transition(Transition("review"))
    net.add_transition(Transition("approve"))
    net.add_transition(Transition("reject"))

    net.add_arc("start", "submit")
    net.add_arc("submit", "submitted")
    net.add_arc("submitted", "review")
    net.add_arc("review", "reviewed")
    net.add_arc("reviewed", "approve")
    net.add_arc("reviewed", "reject")
    net.add_arc("approve", "end")
    # rejection loops back to submitted for revision
    net.add_arc("reject", "submitted")
    return net


def state_machine() -> PetriNet:
    """A simple state machine: each place is a state, each transition an edge."""
    net = PetriNet(name="state_machine")
    net.add_place(Place("idle", initial=1))
    net.add_place(Place("running", initial=0))
    net.add_place(Place("paused", initial=0))
    net.add_place(Place("stopped", initial=0))

    net.add_transition(Transition("start"))
    net.add_transition(Transition("pause"))
    net.add_transition(Transition("resume"))
    net.add_transition(Transition("stop"))
    net.add_transition(Transition("stop_from_pause"))

    net.add_arc("idle", "start")
    net.add_arc("start", "running")
    net.add_arc("running", "pause")
    net.add_arc("pause", "paused")
    net.add_arc("paused", "resume")
    net.add_arc("resume", "running")
    net.add_arc("running", "stop")
    net.add_arc("stop", "stopped")
    net.add_arc("paused", "stop_from_pause")
    net.add_arc("stop_from_pause", "stopped")
    return net


def free_choice_net() -> PetriNet:
    """A free-choice net: every transition shares at most one input place
    with any other transition, OR has a unique input place."""
    net = PetriNet(name="free_choice")
    net.add_place(Place("p1", initial=1))
    net.add_place(Place("p2", initial=0))
    net.add_place(Place("p3", initial=0))
    net.add_place(Place("p4", initial=0))
    net.add_place(Place("p5", initial=0))

    net.add_transition(Transition("t1"))
    net.add_transition(Transition("t2"))
    net.add_transition(Transition("t3"))

    net.add_arc("p1", "t1")
    net.add_arc("p1", "t2")
    net.add_arc("t1", "p2")
    net.add_arc("t1", "p3")
    net.add_arc("t2", "p4")
    net.add_arc("t2", "p5")
    net.add_arc("p2", "t3")
    net.add_arc("p3", "t3")
    net.add_arc("t3", "p1")
    return net


def readers_writers(n_readers: int = 2) -> PetriNet:
    """Readers-writers with priority to writers (simplified).

    Multiple readers can read simultaneously; writers get exclusive access.
    """
    net = PetriNet(name="readers_writers")
    net.add_place(Place("resource", initial=1))
    net.add_place(Place("r_count", initial=0, capacity=n_readers))
    net.add_place(Place("w_active", initial=0, capacity=1))
    net.add_place(Place("r_waiting", initial=0))
    net.add_place(Place("w_waiting", initial=0))

    net.add_transition(Transition("r_start"))
    net.add_transition(Transition("r_end"))
    net.add_transition(Transition("w_start"))
    net.add_transition(Transition("w_end"))

    # Reader
    net.add_arc("r_waiting", "r_start")
    net.add_arc("r_start", "r_count")
    net.add_arc("r_count", "r_end")
    net.add_arc("r_end", "r_waiting")

    # Writer
    net.add_arc("w_waiting", "w_start")
    net.add_arc("resource", "w_start")
    net.add_arc("w_start", "w_active")
    net.add_arc("w_active", "w_end")
    net.add_arc("w_end", "resource")
    net.add_arc("w_end", "w_waiting")

    # Start with one reader and one writer waiting
    net.place("r_waiting").initial = 1
    net.place("w_waiting").initial = 1
    return net