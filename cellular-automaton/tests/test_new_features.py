"""Tests for RLE file loading/saving and GIF export."""

import os
import tempfile

import pytest
import numpy as np

from cellular_automaton import (
    CellularAutomaton, GameOfLifeRule, get_pattern,
    load_rle_file, save_rle_file, parse_rle,
    render_gif, render_multistate_gif,
    WireworldRule,
)


class TestRleFileLoader:
    def test_load_rle_file(self):
        """Load a standard RLE file."""
        rle_content = """#C This is a glider
x = 3, y = 3, rule = B3/S23
bo$2bo$3o!
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".rle", delete=False) as f:
            f.write(rle_content)
            path = f.name
        try:
            pat = load_rle_file(path)
            # Glider = [(1,0), (2,1), (0,2), (1,2), (2,2)]
            assert len(pat) == 5
            assert (1, 0) in pat
            assert (2, 1) in pat
            assert (0, 2) in pat
            assert (1, 2) in pat
            assert (2, 2) in pat
        finally:
            os.unlink(path)

    def test_load_rle_file_with_comments(self):
        """RLE files with multiple comment lines should parse."""
        rle_content = """#N Glider
#C A common spaceship
#C Discovered by Richard Guy
x = 3, y = 3
bo$2bo$3o!
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".rle", delete=False) as f:
            f.write(rle_content)
            path = f.name
        try:
            pat = load_rle_file(path)
            assert len(pat) == 5
        finally:
            os.unlink(path)

    def test_load_rle_multiline_body(self):
        """RLE body can be split across multiple lines."""
        rle_content = """x = 5, y = 3
bo3b$
2bo2b$
3o3b!
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".rle", delete=False) as f:
            f.write(rle_content)
            path = f.name
        try:
            pat = load_rle_file(path)
            assert len(pat) == 5
        finally:
            os.unlink(path)

    def test_save_and_reload_rle(self):
        """Save a pattern to RLE and load it back."""
        glider = get_pattern("glider")
        with tempfile.NamedTemporaryFile(suffix=".rle", delete=False) as f:
            path = f.name
        try:
            save_rle_file(glider, path)
            pat = load_rle_file(path)
            assert len(pat) == len(glider)
            # The pattern should be the same (after normalising origin).
            assert set(pat) == set(glider)
        finally:
            os.unlink(path)

    def test_save_empty_pattern(self):
        with tempfile.NamedTemporaryFile(suffix=".rle", delete=False) as f:
            path = f.name
        try:
            save_rle_file([], path)
            pat = load_rle_file(path)
            assert len(pat) == 0
        finally:
            os.unlink(path)

    def test_save_blinker(self):
        blinker = get_pattern("blinker")
        with tempfile.NamedTemporaryFile(suffix=".rle", delete=False) as f:
            path = f.name
        try:
            save_rle_file(blinker, path)
            with open(path) as f:
                content = f.read()
            assert "x = 3" in content
            assert "y = 1" in content
            pat = load_rle_file(path)
            assert len(pat) == 3
        finally:
            os.unlink(path)


class TestGifExport:
    def test_render_gif(self):
        """Render a simple CA as a GIF."""
        ca = CellularAutomaton(GameOfLifeRule(), width=10, height=10)
        ca.randomize(0.3, seed=42)
        with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as f:
            path = f.name
        try:
            render_gif(ca, path, steps=5, cell_size=2, duration=50)
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0
            # Check it's a GIF (starts with GIF8).
            with open(path, "rb") as f:
                header = f.read(4)
            assert header == b"GIF8"
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_render_multistate_gif(self):
        """Render a Wireworld CA as a coloured GIF."""
        ca = CellularAutomaton(WireworldRule(), width=10, height=5)
        # Lay down a conductor wire.
        for x in range(1, 9):
            ca.set_cell(x, 2, 3)
        ca.set_cell(2, 2, 1)  # electron head
        ca.set_cell(1, 2, 2)  # electron tail
        with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as f:
            path = f.name
        try:
            render_multistate_gif(ca, path, steps=5, cell_size=2, duration=50)
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0
            with open(path, "rb") as f:
                header = f.read(4)
            assert header == b"GIF8"
        finally:
            if os.path.exists(path):
                os.unlink(path)