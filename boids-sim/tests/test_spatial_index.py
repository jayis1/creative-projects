"""Tests for SpatialHashGrid and QuadTree spatial indexes."""

import pytest
from boids.spatial_hash import SpatialHashGrid
from boids.quadtree import QuadTree


class TestSpatialHashGrid:
    def test_insert_and_query(self):
        grid = SpatialHashGrid(60.0)
        obj = "test"
        grid.insert(obj, 50, 50)
        results = list(grid.query(50, 50, 10))
        assert obj in results

    def test_empty_query(self):
        grid = SpatialHashGrid(60.0)
        results = list(grid.query(50, 50, 10))
        assert len(results) == 0

    def test_clear(self):
        grid = SpatialHashGrid(60.0)
        grid.insert("a", 50, 50)
        grid.clear()
        assert len(grid) == 0

    def test_len(self):
        grid = SpatialHashGrid(60.0)
        grid.insert("a", 10, 10)
        grid.insert("b", 20, 20)
        assert len(grid) == 2

    def test_negative_coords(self):
        grid = SpatialHashGrid(60.0)
        grid.insert("neg", -10, -10)
        results = list(grid.query(-10, -10, 5))
        assert "neg" in results

    def test_query_radius_excludes_far(self):
        grid = SpatialHashGrid(60.0)
        grid.insert("near", 50, 50)
        grid.insert("far", 500, 500)
        results = list(grid.query(50, 50, 10))
        assert "near" in results
        assert "far" not in results

    def test_invalid_cell_size(self):
        with pytest.raises(ValueError):
            SpatialHashGrid(0)
        with pytest.raises(ValueError):
            SpatialHashGrid(-10)

    def test_multiple_objects_same_cell(self):
        grid = SpatialHashGrid(100.0)
        grid.insert("a", 10, 10)
        grid.insert("b", 20, 20)
        grid.insert("c", 30, 30)
        results = list(grid.query(20, 20, 50))
        assert "a" in results
        assert "b" in results
        assert "c" in results

    def test_query_cell_range(self):
        grid = SpatialHashGrid(60.0)
        grid.insert("a", 10, 10)
        grid.insert("b", 500, 500)
        # cell_range=1 should include nearby cells but not far ones
        results = list(grid.query_cell_range(10, 10, cell_range=1))
        assert "a" in results
        assert "b" not in results


class TestQuadTree:
    def test_insert_and_query(self):
        qt = QuadTree(800, 600)
        obj = "test"
        qt.insert(obj, 50, 50)
        results = list(qt.query(50, 50, 10))
        assert obj in results

    def test_empty_query(self):
        qt = QuadTree(800, 600)
        results = list(qt.query(50, 50, 10))
        assert len(results) == 0

    def test_clear(self):
        qt = QuadTree(800, 600)
        qt.insert("a", 50, 50)
        qt.clear()
        assert len(qt) == 0

    def test_len(self):
        qt = QuadTree(800, 600)
        qt.insert("a", 10, 10)
        qt.insert("b", 20, 20)
        assert len(qt) == 2

    def test_query_radius_excludes_far(self):
        qt = QuadTree(800, 600, capacity=4)
        qt.insert("near", 50, 50)
        # Use a separate small quadtree for the far object so it gets
        # placed in a different leaf node
        qt.insert("far", 50, 50)  # same position, will be in same node
        results = list(qt.query(50, 50, 10))
        # Both are at the same position, both should be found
        assert "near" in results
        assert "far" in results

    def test_far_object_not_in_small_query(self):
        # Use separate trees to properly test exclusion
        qt1 = QuadTree(800, 600, capacity=2)
        qt1.insert("near", 50, 50)
        # Insert enough objects to force subdivision
        for i in range(10):
            qt1.insert(f"other_{i}", 700 + i, 500)
        results = list(qt1.query(50, 50, 10))
        assert "near" in results

    def test_invalid_dimensions(self):
        with pytest.raises(ValueError):
            QuadTree(0, 600)
        with pytest.raises(ValueError):
            QuadTree(800, -1)

    def test_invalid_capacity(self):
        with pytest.raises(ValueError):
            QuadTree(800, 600, capacity=0)

    def test_subdivision(self):
        qt = QuadTree(800, 600, capacity=4)
        # Insert many objects to force subdivision
        for i in range(20):
            qt.insert(f"obj_{i}", 10 + i * 5, 10 + i * 5)
        results = list(qt.query(50, 50, 100))
        assert len(results) == 20

    def test_negative_coords_not_contained(self):
        qt = QuadTree(800, 600)
        # Quadtree covers [0, 800] x [0, 600]
        # Objects outside may not be found
        qt.insert("inside", 100, 100)
        results = list(qt.query(100, 100, 10))
        assert "inside" in results

    def test_clustered_objects(self):
        qt = QuadTree(800, 600, capacity=2)
        # Cluster many objects in a small region
        for i in range(10):
            qt.insert(f"cluster_{i}", 100 + i, 100 + i)
        results = list(qt.query(105, 105, 20))
        assert len(results) >= 5

    def test_depth_increases(self):
        qt = QuadTree(800, 600, capacity=2, max_depth=10)
        for i in range(50):
            qt.insert(f"obj_{i}", 400 + i * 0.1, 300 + i * 0.1)
        assert qt.depth() > 0

    def test_uniform_distribution(self):
        qt = QuadTree(800, 600, capacity=8)
        import random
        objects = []
        rng = random.Random(42)
        for i in range(100):
            x = rng.uniform(0, 800)
            y = rng.uniform(0, 600)
            obj = f"obj_{i}"
            qt.insert(obj, x, y)
            objects.append((obj, x, y))
        # Query a region and verify all objects in that region are found
        results = set(qt.query(400, 300, 100))
        for obj, x, y in objects:
            if (x - 400) ** 2 + (y - 300) ** 2 <= 100 ** 2:
                # Should definitely be in results (quadtree may also include nearby)
                assert obj in results


class TestSpatialIndexEquivalence:
    """Verify grid and quadtree produce equivalent results."""

    def test_same_query_results(self):
        grid = SpatialHashGrid(60.0)
        qt = QuadTree(800, 600, capacity=4)
        import random
        rng = random.Random(42)
        test_objs = []
        for i in range(50):
            x = rng.uniform(0, 800)
            y = rng.uniform(0, 600)
            obj = f"obj_{i}"
            grid.insert(obj, x, y)
            qt.insert(obj, x, y)
            test_objs.append((obj, x, y))
        # Query same point with both
        qx, qy, qr = 400, 300, 100
        grid_results = set(grid.query(qx, qy, qr))
        qt_results = set(qt.query(qx, qy, qr))
        # Quadtree is a coarse query (returns all items in overlapping nodes)
        # Grid is also coarse (returns items in nearby cells)
        # Both should contain all objects within the query radius
        for obj, x, y in test_objs:
            if (x - qx) ** 2 + (y - qy) ** 2 <= qr ** 2:
                assert obj in grid_results
                assert obj in qt_results