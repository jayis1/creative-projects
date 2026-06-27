"""Tests for mesh quality metrics."""
import os, sys, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from delaunay_voronoi.geometry import Point
from delaunay_voronoi.delaunay import DelaunayTriangulation
from delaunay_voronoi.convex_hull import convex_hull
from delaunay_voronoi.metrics import compute_mesh_report
from delaunay_voronoi.lloyd import generate_poisson_seed


class TestMeshReport:
    def test_basic_report(self):
        pts = generate_poisson_seed(20, (Point(0, 0), Point(200, 200)), seed=1)
        dt = DelaunayTriangulation.from_points(pts)
        hull = convex_hull(pts)
        report = compute_mesh_report(dt, hull_vertices=len(hull))
        assert report.num_points == 20
        assert report.num_triangles > 0
        assert report.num_edges > 0
        assert report.num_hull_vertices == len(hull)

    def test_angle_stats(self):
        pts = [Point(0, 0), Point(10, 0), Point(0, 10)]
        dt = DelaunayTriangulation.from_points(pts)
        report = compute_mesh_report(dt)
        # Right triangle: 90°, 45°, 45°
        assert 44 < report.angle_stats.min_deg < 46
        assert 89 < report.angle_stats.max_deg < 91
        assert report.angle_stats.mean_deg > 0

    def test_area_stats(self):
        pts = [Point(0, 0), Point(10, 0), Point(0, 10)]
        dt = DelaunayTriangulation.from_points(pts)
        report = compute_mesh_report(dt)
        assert abs(report.area_stats.total - 50.0) < 1e-6
        assert report.area_stats.min > 0

    def test_edge_stats(self):
        pts = [Point(0, 0), Point(10, 0), Point(0, 10)]
        dt = DelaunayTriangulation.from_points(pts)
        report = compute_mesh_report(dt)
        assert report.edge_stats.count > 0
        assert report.edge_stats.min > 0

    def test_quality_measures(self):
        pts = [Point(0, 0), Point(10, 0), Point(5, 8.66)]
        dt = DelaunayTriangulation.from_points(pts)
        report = compute_mesh_report(dt)
        # Equilateral triangle → radius ratio close to 1
        assert report.min_radius_ratio > 0.9
        assert report.min_aspect_ratio > 0.9

    def test_to_json(self):
        pts = generate_poisson_seed(10, (Point(0, 0), Point(100, 100)), seed=2)
        dt = DelaunayTriangulation.from_points(pts)
        report = compute_mesh_report(dt)
        j = report.to_json()
        import json
        data = json.loads(j)
        assert "num_points" in data
        assert "angle_stats" in data
        assert "area_stats" in data

    def test_to_text(self):
        pts = generate_poisson_seed(5, (Point(0, 0), Point(50, 50)), seed=3)
        dt = DelaunayTriangulation.from_points(pts)
        report = compute_mesh_report(dt)
        text = report.to_text()
        assert "MESH QUALITY REPORT" in text
        assert "ANGLE STATISTICS" in text
        assert "AREA STATISTICS" in text
        assert "QUALITY MEASURES" in text

    def test_to_dict(self):
        pts = generate_poisson_seed(5, (Point(0, 0), Point(50, 50)), seed=3)
        dt = DelaunayTriangulation.from_points(pts)
        report = compute_mesh_report(dt)
        d = report.to_dict()
        assert isinstance(d, dict)
        assert d["num_points"] == 5

    def test_histograms(self):
        pts = generate_poisson_seed(30, (Point(0, 0), Point(200, 200)), seed=4)
        dt = DelaunayTriangulation.from_points(pts)
        report = compute_mesh_report(dt)
        assert len(report.angle_histogram) > 0
        assert len(report.area_histogram) > 0
        # Total count in histogram should equal num triangles
        assert sum(report.angle_histogram.values()) == report.num_triangles

    def test_empty_mesh(self):
        """Zero triangles — should not crash."""
        pts = [Point(0, 0), Point(1, 0), Point(2, 0)]  # collinear
        dt = DelaunayTriangulation.from_points(pts)
        report = compute_mesh_report(dt)
        assert report.num_triangles == 0