"""Tests for the spatial hash grid module."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from delaunay_voronoi.geometry import Point
from delaunay_voronoi.spatial_hash import (
    SpatialHashGrid, nearest_neighbor_grid, deduplicate_points,
)


class TestSpatialHashGrid:
    def test_empty(self):
        grid = SpatialHashGrid(cell_size=10)
        assert len(grid) == 0
        assert grid.nearest(Point(5, 5)) is None

    def test_insert_and_len(self):
        grid = SpatialHashGrid(cell_size=10)
        grid.insert(Point(1, 2))
        grid.insert(Point(5, 5))
        assert len(grid) == 2

    def test_invalid_cell_size(self):
        with pytest.raises(ValueError):
            SpatialHashGrid(cell_size=0)
        with pytest.raises(ValueError):
            SpatialHashGrid(cell_size=-1)

    def test_from_points_auto_cell(self):
        pts = [Point(0, 0), Point(10, 10), Point(20, 20)]
        grid = SpatialHashGrid.from_points(pts)
        assert len(grid) == 3
        assert grid.cell_size > 0

    def test_from_points_empty(self):
        grid = SpatialHashGrid.from_points([])
        assert len(grid) == 0

    def test_nearest_basic(self):
        pts = [Point(0, 0), Point(10, 0), Point(0, 10), Point(10, 10)]
        grid = SpatialHashGrid.from_points(pts, cell_size=5)
        nn = grid.nearest(Point(9, 9))
        assert nn == Point(10, 10)

    def test_nearest_exact(self):
        pts = [Point(0, 0), Point(100, 0), Point(0, 100)]
        grid = SpatialHashGrid.from_points(pts, cell_size=10)
        assert grid.nearest(Point(1, 1)) == Point(0, 0)
        assert grid.nearest(Point(99, 1)) == Point(100, 0)

    def test_nearest_large_set(self):
        import random
        rng = random.Random(42)
        pts = [Point(rng.uniform(0, 1000), rng.uniform(0, 1000)) for _ in range(200)]
        grid = SpatialHashGrid.from_points(pts, cell_size=30)
        query = Point(500, 500)
        nn_grid = grid.nearest(query)
        # Brute force
        nn_brute = min(pts, key=lambda p: p.distance_to(query))
        assert nn_grid == nn_brute

    def test_points_in_radius(self):
        pts = [Point(0, 0), Point(5, 5), Point(10, 10), Point(50, 50)]
        grid = SpatialHashGrid.from_points(pts, cell_size=10)
        near = grid.points_in_radius(Point(5, 5), radius=10)
        assert Point(0, 0) in near
        assert Point(5, 5) in near
        assert Point(10, 10) in near
        assert Point(50, 50) not in near

    def test_num_cells(self):
        pts = [Point(0, 0), Point(100, 100)]
        grid = SpatialHashGrid.from_points(pts, cell_size=10)
        assert grid.num_cells == 2


class TestDeduplicate:
    def test_no_duplicates(self):
        pts = [Point(0, 0), Point(10, 10), Point(20, 20)]
        result = deduplicate_points(pts, tolerance=0.1)
        assert len(result) == 3

    def test_with_duplicates(self):
        pts = [Point(0, 0), Point(0.001, 0.001), Point(10, 10)]
        result = deduplicate_points(pts, tolerance=0.1)
        assert len(result) == 2

    def test_empty(self):
        assert deduplicate_points([]) == []

    def test_all_same(self):
        pts = [Point(5, 5), Point(5, 5), Point(5, 5)]
        result = deduplicate_points(pts, tolerance=0.01)
        assert len(result) == 1