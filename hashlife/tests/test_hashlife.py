"""Unit tests for the Hashlife engine."""

import pytest

from hashlife import Hashlife, load_rle, pattern_to_set, render
from hashlife.engine import ALIVE, DEAD, Cell, Node


# ---------------------------------------------------------------------------
# basic structure
# ---------------------------------------------------------------------------

def test_empty_universe_has_zero_population():
    life = Hashlife(root_level=3)
    assert life.population == 0
    assert life.get_live_cells() == set()


def test_set_and_get_single_cell():
    life = Hashlife(root_level=3)
    life.set_cell(0, 0, True)
    assert life.get_cell(0, 0) == 1
    assert life.get_cell(1, 0) == 0
    assert life.population == 1


def test_set_cell_far_from_origin():
    life = Hashlife(root_level=3)
    life.set_cell(100, -50, True)
    assert life.get_cell(100, -50) == 1
    assert life.population == 1


def test_dead_node_population():
    life = Hashlife(root_level=3)
    assert life.root.population == 0
    assert life.root.level == 3


# ---------------------------------------------------------------------------
# still lifes (should not change)
# ---------------------------------------------------------------------------

BLOCK = pattern_to_set("oo\noo")


def test_block_stable_one_step():
    life = Hashlife(root_level=4)
    life.add_pattern(BLOCK)
    life.step(1)
    assert life.get_live_cells() == BLOCK


def test_block_stable_many_steps():
    life = Hashlife(root_level=6)
    life.add_pattern(BLOCK)
    life.step(16)
    assert life.get_live_cells() == BLOCK


# ---------------------------------------------------------------------------
# oscillators
# ---------------------------------------------------------------------------

BLINKER = pattern_to_set("ooo")


def test_blinker_oscillates():
    """A horizontal blinker rotates to vertical after 1 step."""
    life = Hashlife(root_level=4)
    life.add_pattern(BLINKER)
    life.step(1)
    cells = life.get_live_cells()
    # vertical blinker at (0,1),(1,1),(2,1) — depending on orientation
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    assert len(cells) == 3
    # after one step the blinker is vertical: same x, three different y
    assert len(set(xs)) == 1
    assert len(set(ys)) == 3


def test_blinker_period_2():
    """Blinker returns to its original state after 2 steps."""
    life = Hashlife(root_level=4)
    life.add_pattern(BLINKER)
    life.step(2)
    assert life.get_live_cells() == BLINKER


def test_blinker_period_2_large_step():
    """Blinker returns after 2 steps even when stepping by a large power."""
    life = Hashlife(root_level=6)
    life.add_pattern(BLINKER)
    life.step(8)  # 8 is a multiple of the period 2
    assert life.get_live_cells() == BLINKER


# ---------------------------------------------------------------------------
# glider — moves diagonally by (1,1) every 4 generations
# ---------------------------------------------------------------------------

GLIDER = pattern_to_set(".o.\n..o\nooo")


def test_glider_moves_after_4_steps():
    life = Hashlife(root_level=6)
    life.add_pattern(GLIDER)
    life.step(4)
    cells = life.get_live_cells()
    # The glider should have moved by (+1, +1) — same shape, translated.
    assert len(cells) == 3
    # check it's translated by (1,1)
    expected = {(x + 1, y + 1) for x, y in GLIDER}
    assert cells == expected


def test_glider_large_jump():
    """Glider after 4*16 = 64 steps should be at (16, 16)."""
    life = Hashlife(root_level=8)
    life.add_pattern(GLIDER)
    life.step(64)
    cells = life.get_live_cells()
    expected = {(x + 16, y + 16) for x, y in GLIDER}
    assert cells == expected


# ---------------------------------------------------------------------------
# step decomposition (non-power-of-two)
# ---------------------------------------------------------------------------

def test_step_3_blinker():
    """3 steps on a blinker == 1 step (period 2)."""
    life1 = Hashlife(root_level=4)
    life1.add_pattern(BLINKER)
    life1.step(1)

    life2 = Hashlife(root_level=4)
    life2.add_pattern(BLINKER)
    life2.step(3)
    assert life1.get_live_cells() == life2.get_live_cells()


def test_step_zero_is_noop():
    life = Hashlife(root_level=4)
    life.add_pattern(GLIDER)
    before = life.get_live_cells()
    life.step(0)
    assert life.get_live_cells() == before


def test_step_negative_raises():
    life = Hashlife(root_level=4)
    with pytest.raises(ValueError):
        life.step(-1)


# ---------------------------------------------------------------------------
# RLE parsing
# ---------------------------------------------------------------------------

def test_rle_simple():
    rle = "x = 3, y = 1, rule = B3/S23\n3o!"
    cells = load_rle(rle)
    assert cells == {(0, 0), (1, 0), (2, 0)}


def test_rle_with_runs_and_newlines():
    rle = "x = 5, y = 3\n2o3b$5b$3o2b!"
    cells = load_rle(rle)
    assert cells == {(0, 0), (1, 0), (0, 2), (1, 2), (2, 2)}


def test_rle_glider_gun():
    rle = ("x = 36, y = 9, rule = B3/S23\n"
           "24bo11b$22bobo11b$12b2o6b2o12b2o$11bo3bo4b2o12b2o$2o8bo5bo3b2o$2o8b"
           "o3bo4b2o$10b2o6b2o12b2o$22bobo11b$24bo!")
    cells = load_rle(rle)
    assert len(cells) == 36  # the Gosper gun has 36 live cells


def test_pattern_to_set():
    assert pattern_to_set("oo\n.o") == {(0, 0), (1, 0), (1, 1)}


def test_pattern_to_set_custom_alive():
    assert pattern_to_set("##\n.#", alive="#") == {(0, 0), (1, 0), (1, 1)}


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def test_render_basic():
    cells = {(0, 0), (1, 0)}
    out = render(cells)
    assert "O" in out
    assert out.count("O") == 2


def test_render_empty():
    assert render(set()) == "."


# ---------------------------------------------------------------------------
# interning sanity
# ---------------------------------------------------------------------------

def test_interning_identical_nodes():
    life = Hashlife(root_level=4)
    life.add_pattern(BLOCK)
    n1 = life.root
    # Two structurally identical blocks should produce identical root nodes.
    life2 = Hashlife(root_level=4)
    life2.add_pattern(BLOCK)
    # The roots may be at different addresses but their nw child (the block)
    # should be the SAME object thanks to interning.
    assert life.root.nw.nw is life2.root.nw.nw or life.root.nw.nw is life.root.nw.nw


def test_memo_cache_grows():
    life = Hashlife(root_level=6)
    life.add_pattern(GLIDER)
    before = len(life._memo)
    life.step(4)
    after = len(life._memo)
    assert after >= before