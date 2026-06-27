"""Tests for exporters: OBJ, STL, PNG, boundary extraction."""
import os, sys, struct, zlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from delaunay_voronoi.geometry import Point
from delaunay_voronoi.delaunay import DelaunayTriangulation
from delaunay_voronoi.exporters import (
    export_obj, save_obj, export_ascii_stl,
    export_png, render_png, save_png,
    extract_boundary_edges, extract_boundary_loops,
)
from delaunay_voronoi.lloyd import generate_poisson_seed


class TestObjExport:
    def test_basic_obj(self):
        pts = [Point(0, 0), Point(10, 0), Point(0, 10)]
        dt = DelaunayTriangulation.from_points(pts)
        obj = export_obj(dt)
        assert obj.startswith("#")
        assert "v " in obj
        assert "f " in obj

    def test_obj_vertex_count(self):
        pts = [Point(0, 0), Point(10, 0), Point(10, 10), Point(0, 10)]
        dt = DelaunayTriangulation.from_points(pts)
        obj = export_obj(dt)
        v_lines = [l for l in obj.split("\n") if l.startswith("v ")]
        assert len(v_lines) == 4

    def test_obj_face_count(self):
        pts = [Point(0, 0), Point(10, 0), Point(10, 10), Point(0, 10)]
        dt = DelaunayTriangulation.from_points(pts)
        obj = export_obj(dt)
        f_lines = [l for l in obj.split("\n") if l.startswith("f ")]
        assert len(f_lines) == 2

    def test_save_obj(self, tmp_path):
        pts = [Point(0, 0), Point(10, 0), Point(0, 10)]
        dt = DelaunayTriangulation.from_points(pts)
        path = str(tmp_path / "test.obj")
        save_obj(dt, path)
        assert os.path.exists(path)
        with open(path) as f:
            content = f.read()
        assert "v " in content


class TestStlExport:
    def test_basic_stl(self):
        pts = [Point(0, 0), Point(10, 0), Point(0, 10)]
        dt = DelaunayTriangulation.from_points(pts)
        stl = export_ascii_stl(dt)
        assert stl.startswith("solid")
        assert stl.endswith("endsolid delaunay_mesh\n")
        assert "facet" in stl
        assert "vertex" in stl

    def test_stl_facet_count(self):
        pts = [Point(0, 0), Point(10, 0), Point(10, 10), Point(0, 10)]
        dt = DelaunayTriangulation.from_points(pts)
        stl = export_ascii_stl(dt)
        assert stl.count("endfacet") == 2


class TestPngExport:
    def test_png_valid(self, tmp_path):
        pts = [Point(10, 10), Point(50, 40), Point(90, 10)]
        path = str(tmp_path / "test.png")
        save_png(100, 80, pts, path)
        assert os.path.exists(path)
        with open(path, "rb") as f:
            data = f.read()
        # PNG signature
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        # IHDR
        assert data[12:16] == b"IHDR"
        w, h = struct.unpack(">II", data[16:24])
        assert w == 100 and h == 80

    def test_png_empty_points(self, tmp_path):
        path = str(tmp_path / "empty.png")
        save_png(10, 10, [], path)
        assert os.path.exists(path)
        with open(path, "rb") as f:
            data = f.read()
        assert data[:8] == b"\x89PNG\r\n\x1a\n"

    def test_render_png_pixels(self):
        pts = [Point(10, 10), Point(50, 40), Point(90, 10)]
        pixels = render_png(100, 80, pts)
        assert len(pixels) == 100 * 80 * 3

    def test_export_png_bad_size(self, tmp_path):
        path = str(tmp_path / "bad.png")
        with pytest.raises(ValueError):
            export_png(10, 10, b"\x00" * 100, path)


class TestBoundary:
    def test_boundary_edges(self):
        pts = [Point(0, 0), Point(10, 0), Point(10, 10), Point(0, 10)]
        dt = DelaunayTriangulation.from_points(pts)
        edges = extract_boundary_edges(dt)
        # Square → 4 boundary edges
        assert len(edges) == 4

    def test_boundary_loops(self):
        pts = [Point(0, 0), Point(10, 0), Point(10, 10), Point(0, 10)]
        dt = DelaunayTriangulation.from_points(pts)
        loops = extract_boundary_loops(dt)
        assert len(loops) >= 1
        assert all(len(loop) >= 3 for loop in loops)

    def test_boundary_more_points(self):
        pts = generate_poisson_seed(15, (Point(0, 0), Point(100, 100)), seed=5)
        dt = DelaunayTriangulation.from_points(pts)
        edges = extract_boundary_edges(dt)
        loops = extract_boundary_loops(dt)
        assert len(edges) > 0
        assert len(loops) >= 1