"""Tests for the visualization module."""

import pytest
from autograd_engine import Value
from autograd_engine.viz import to_dot, draw_dot, ascii_loss_chart
import tempfile
import os


class TestToDot:
    def test_basic(self):
        x = Value(2.0, label="x")
        y = x ** 2 + 1
        y.backward()
        dot = to_dot(y)
        assert "digraph autograd" in dot
        assert "data=" in dot

    def test_with_title(self):
        x = Value(2.0)
        y = x * 3
        dot = to_dot(y, title="test graph")
        assert 'label="test graph"' in dot

    def test_has_edges(self):
        x = Value(2.0)
        y = Value(3.0)
        z = x + y
        dot = to_dot(z)
        assert "->" in dot


class TestDrawDot:
    def test_writes_file(self):
        x = Value(2.0)
        y = x ** 2
        with tempfile.NamedTemporaryFile(suffix=".dot", delete=False) as f:
            path = f.name
        try:
            draw_dot(y, path)
            content = open(path).read()
            assert "digraph" in content
        finally:
            os.unlink(path)


class TestAsciiLossChart:
    def test_basic(self):
        history = [1.0, 0.8, 0.6, 0.4, 0.2, 0.1]
        chart = ascii_loss_chart(history)
        assert "loss" in chart
        assert "●" in chart

    def test_empty(self):
        chart = ascii_loss_chart([])
        assert "empty" in chart.lower()

    def test_single(self):
        chart = ascii_loss_chart([0.5])
        assert "0.5" in chart

    def test_custom_dimensions(self):
        history = [1.0, 0.5, 0.1]
        chart = ascii_loss_chart(history, width=30, height=10)
        assert "●" in chart