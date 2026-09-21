import json
import pytest
from vector_clock_sim import Trace, TraceError, load_json


def test_local_and_send_have_monotonic_clocks():
    t = Trace(("a", "b"))
    t.record([("a", "local"), ("a", "send", "b")])
    assert [e.vector for e in t.events] == [(1, 0), (2, 0)]
    assert t.events[0].lamport < t.events[1].lamport


def test_receive_merges_sender_clock():
    t = Trace(("a", "b"))
    t.record([("a", "send", "b"), ("b", "receive", "a")])
    assert t.events[-1].vector == (1, 1)
    assert t.happens_before(*t.events)


def test_concurrency_and_round_trip():
    t = Trace(("a", "b"))
    t.record([("a", "local"), ("b", "local")])
    assert len(t.concurrent_pairs()) == 1
    loaded = load_json(t.to_json())
    assert loaded.events == t.events


def test_rejects_bad_process_and_kind():
    with pytest.raises(TraceError):
        Trace(())
    with pytest.raises(TraceError):
        Trace(("a",)).record([("x", "local")])
    with pytest.raises(TraceError):
        Trace(("a",)).record([("a", "send")])


def test_invalid_json():
    with pytest.raises(TraceError):
        load_json("[]")
