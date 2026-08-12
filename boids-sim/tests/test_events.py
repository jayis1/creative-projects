"""Tests for the EventBus."""

import pytest
from boids.events import EventBus


class TestEventBusBasic:
    def test_subscribe_and_emit(self):
        bus = EventBus()
        calls = []
        bus.on("test", lambda x: calls.append(x))
        bus.emit("test", 42)
        assert calls == [42]

    def test_multiple_listeners(self):
        bus = EventBus()
        calls_a = []
        calls_b = []
        bus.on("event", lambda x: calls_a.append(x))
        bus.on("event", lambda x: calls_b.append(x))
        bus.emit("event", "hello")
        assert calls_a == ["hello"]
        assert calls_b == ["hello"]

    def test_no_listeners(self):
        bus = EventBus()
        bus.emit("nobody", 1)  # should not crash

    def test_unsubscribe(self):
        bus = EventBus()
        calls = []
        def cb(x):
            calls.append(x)
        bus.on("test", cb)
        bus.off("test", cb)
        bus.emit("test", 1)
        assert calls == []

    def test_off_nonexistent(self):
        bus = EventBus()
        bus.off("test", lambda x: None)  # should not crash

    def test_off_not_subscribed(self):
        bus = EventBus()
        bus.on("test", lambda x: None)
        bus.off("test", lambda x: None)  # different lambda, should not crash
        # Original listener still subscribed
        assert bus.listener_count("test") == 1


class TestEventBusErrorHandling:
    def test_exception_in_listener_caught(self):
        bus = EventBus()
        def bad(x):
            raise RuntimeError("boom")
        bus.on("test", bad)
        # Should not raise
        bus.emit("test", 1)

    def test_multiple_listeners_one_fails(self):
        bus = EventBus()
        calls = []
        def good(x):
            calls.append(x)
        def bad(x):
            raise RuntimeError("fail")
        bus.on("event", bad)
        bus.on("event", good)
        bus.emit("event", 42)
        assert 42 in calls  # good listener still called

    def test_custom_error_handler(self):
        bus = EventBus()
        errors = []
        bus.set_error_handler(lambda exc: errors.append(exc))
        def bad(x):
            raise ValueError("test error")
        bus.on("test", bad)
        bus.emit("test", 1)
        assert len(errors) == 1
        assert isinstance(errors[0], ValueError)

    def test_non_callable_callback(self):
        bus = EventBus()
        with pytest.raises(TypeError):
            bus.on("test", "not a function")


class TestEventBusUtilities:
    def test_listener_count(self):
        bus = EventBus()
        assert bus.listener_count("event") == 0
        bus.on("event", lambda x: None)
        bus.on("event", lambda x: None)
        assert bus.listener_count("event") == 2

    def test_clear(self):
        bus = EventBus()
        bus.on("test", lambda x: None)
        bus.clear()
        assert bus.listener_count("test") == 0