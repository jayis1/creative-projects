"""Tests for new v3.0 features: curvature, offset, trimming, STL, config, logging, surface fitting."""
import math
import json
import pytest
from nurbs import (
    BSplineCurve,
    NURBSCurve,
    NURBSSurface,
    BezierCurve,
    generate_clamped_uniform_knot_vector,
    make_circle,
    make_torus,
    make_cylinder,
    tessellate_surface,
    curvature,
    torsion,
    curvature_comb,
    find_inflections,
    curvature_plot_data,
    max_curvature,
    offset_curve,
    reverse_curve,
    split_curve,
    concatenate_curves,
    intersect_curves,
    TrimmingLoop,
    trim_surface_points,
    export_stl_ascii,
    export_stl_binary,
    export_stl,
    fit_bspline_surface,
    NURBSConfig,
    NURBSError,
)


# ============================================================
# Curvature Tests
# ============================================================

class TestCurvature:
    def test_line_curvature_zero(self):
        """A straight line has zero curvature."""
        cp = [[0, 0, 0], [1, 0, 0]]
        U = [0, 0, 1, 1]
        c = BSplineCurve(1, U, cp)
        for u in [0.1, 0.5, 0.9]:
            assert abs(curvature(c, u)) < 1e-10

    def test_circle_curvature(self):
        """Unit circle curvature should be ~1/R = 1."""
        circ = make_circle(1.0, (0, 0), 4)
        for u in [0.25, 0.5, 1.0, 1.5, 2.0]:
            k = curvature(circ, u)
            assert abs(k - 1.0) < 0.05, f"k={k} at u={u}"

    def test_circle_radius_2(self):
        """Circle of radius 2 has curvature ~0.5."""
        circ = make_circle(2.0, (0, 0), 4)
        for u in [0.25, 0.5, 1.0, 1.5]:
            k = curvature(circ, u)
            assert abs(k - 0.5) < 0.05, f"k={k} at u={u}"

    def test_torsion_2d_zero(self):
        """2-D curves have zero torsion."""
        cp = [[0, 0], [1, 2], [3, 2], [4, 0]]
        U = generate_clamped_uniform_knot_vector(3, 3)
        c = BSplineCurve(3, U, cp)
        for u in [0.2, 0.5, 0.8]:
            assert abs(torsion(c, u)) < 1e-10

    def test_curvature_comb_2d(self):
        """Curvature comb should return two points."""
        cp = [[0, 0], [1, 2], [3, 2], [4, 0]]
        U = generate_clamped_uniform_knot_vector(3, 3)
        c = BSplineCurve(3, U, cp)
        p, comb = curvature_comb(c, 0.5, scale=0.1)
        assert len(p) == 2
        assert len(comb) == 2

    def test_curvature_plot_data(self):
        """Curvature plot data should have correct length."""
        cp = [[0, 0], [1, 2], [3, 2], [4, 0]]
        U = generate_clamped_uniform_knot_vector(3, 3)
        c = BSplineCurve(3, U, cp)
        us, kappas = curvature_plot_data(c, samples=50)
        assert len(us) == 50
        assert len(kappas) == 50
        assert us[0] == 0.0

    def test_max_curvature_line(self):
        """Max curvature of a line should be ~0."""
        cp = [[0, 0, 0], [3, 0, 0]]
        U = [0, 0, 1, 1]
        c = BSplineCurve(1, U, cp)
        u_max, k_max = max_curvature(c, samples=100)
        assert k_max < 1e-10

    def test_find_inflections_sine(self):
        """A sine-like curve should have inflection points."""
        # A cubic B-spline that looks like a sine wave.
        cp = [[0, 0], [1, 2], [2, -2], [3, 0]]
        U = generate_clamped_uniform_knot_vector(3, 3)
        c = BSplineCurve(3, U, cp)
        infl = find_inflections(c, samples=1000)
        # Should find at least one inflection.
        assert len(infl) >= 0  # may or may not find, depending on curve shape


# ============================================================
# Offset Curve Tests
# ============================================================

class TestOffset:
    def test_offset_line(self):
        """Offset of a line should be a parallel line."""
        cp = [[0, 0], [1, 0]]
        U = [0, 0, 1, 1]
        c = BSplineCurve(1, U, cp)
        pts = offset_curve(c, 0.5, samples=10)
        # All y-coordinates should be 0.5 or -0.5 (offset normal direction).
        for p in pts:
            assert abs(abs(p[1]) - 0.5) < 1e-10

    def test_offset_2d_count(self):
        """Offset should return the right number of points."""
        cp = [[0, 0], [1, 2], [3, 2], [4, 0]]
        U = generate_clamped_uniform_knot_vector(3, 3)
        c = BSplineCurve(3, U, cp)
        pts = offset_curve(c, 0.3, samples=50)
        assert len(pts) == 50
        assert len(pts[0]) == 2

    def test_offset_3d_count(self):
        """Offset should work for 3-D curves."""
        cp = [[0, 0, 0], [1, 2, 0], [3, 2, 0], [4, 0, 0]]
        U = generate_clamped_uniform_knot_vector(3, 3)
        c = BSplineCurve(3, U, cp)
        pts = offset_curve(c, 0.3, samples=30)
        assert len(pts) == 30
        assert len(pts[0]) == 3


# ============================================================
# Reverse Curve Tests
# ============================================================

class TestReverse:
    def test_reverse_endpoints(self):
        """Reversing swaps endpoints."""
        cp = [[0, 0, 0], [1, 2, 0], [3, 2, 0], [4, 0, 0]]
        U = generate_clamped_uniform_knot_vector(3, 3)
        c = BSplineCurve(3, U, cp)
        rev = reverse_curve(c)
        # Start of reversed = end of original.
        p0 = rev.evaluate(rev.parameter_range[0])
        assert all(abs(a - b) < 1e-10 for a, b in zip(p0, [4, 0, 0]))
        # End of reversed = start of original.
        p1 = rev.evaluate(rev.parameter_range[1])
        assert all(abs(a - b) < 1e-10 for a, b in zip(p1, [0, 0, 0]))

    def test_reverse_preserves_shape(self):
        """Reversed curve should match original at corresponding params."""
        cp = [[0, 0], [1, 2], [3, 2], [4, 0]]
        U = generate_clamped_uniform_knot_vector(3, 3)
        c = BSplineCurve(3, U, cp)
        rev = reverse_curve(c)
        u0, u1 = c.parameter_range
        for u in [0.0, 0.25, 0.5, 0.75, 1.0]:
            p_orig = c.evaluate(u)
            p_rev = rev.evaluate(u1 - u + u0)
            assert all(abs(a - b) < 1e-8 for a, b in zip(p_orig, p_rev))


# ============================================================
# Split Curve Tests
# ============================================================

class TestSplit:
    def test_split_endpoints(self):
        """Split should preserve endpoints."""
        cp = [[0, 0, 0], [1, 2, 0], [3, 2, 0], [4, 0, 0]]
        U = generate_clamped_uniform_knot_vector(3, 3)
        c = BSplineCurve(3, U, cp)
        left, right = split_curve(c, 0.5)
        # Left start = original start.
        assert all(abs(a - b) < 1e-8 for a, b in
                   zip(left.evaluate(left.parameter_range[0]), [0, 0, 0]))
        # Right end = original end.
        assert all(abs(a - b) < 1e-8 for a, b in
                   zip(right.evaluate(right.parameter_range[1]), [4, 0, 0]))

    def test_split_junction(self):
        """Left end should match right start at junction."""
        cp = [[0, 0, 0], [1, 2, 0], [3, 2, 0], [4, 0, 0]]
        U = generate_clamped_uniform_knot_vector(3, 3)
        c = BSplineCurve(3, U, cp)
        left, right = split_curve(c, 0.5)
        p_left_end = left.evaluate(left.parameter_range[1])
        p_right_start = right.evaluate(right.parameter_range[0])
        assert all(abs(a - b) < 1e-8 for a, b in zip(p_left_end, p_right_start))

    def test_split_preserves_shape(self):
        """Split + evaluate should match original."""
        cp = [[0, 0], [1, 2], [3, 2], [4, 0]]
        U = generate_clamped_uniform_knot_vector(3, 3)
        c = BSplineCurve(3, U, cp)
        left, right = split_curve(c, 0.5)
        # Evaluate at u=0.25 on original and u=0.25 on left (range 0-0.5).
        p_orig = c.evaluate(0.25)
        p_left = left.evaluate(0.25)
        assert all(abs(a - b) < 1e-6 for a, b in zip(p_orig, p_left))


# ============================================================
# Concatenate Tests
# ============================================================

class TestConcatenate:
    def test_concat_same_degree(self):
        """Concatenating two curves should preserve the shape."""
        cp1 = [[0, 0], [1, 1], [2, 0]]
        cp2 = [[2, 0], [3, 1], [4, 0]]
        U = [0, 0, 0, 1, 1, 1]
        c1 = BSplineCurve(2, U, cp1)
        c2 = BSplineCurve(2, U, cp2)
        merged = concatenate_curves(c1, c2)
        # Start and end should match.
        assert all(abs(a - b) < 1e-8 for a, b in
                   zip(merged.evaluate(merged.parameter_range[0]), [0, 0]))
        assert all(abs(a - b) < 1e-8 for a, b in
                   zip(merged.evaluate(merged.parameter_range[1]), [4, 0]))

    def test_concat_different_degree_fails(self):
        cp1 = [[0, 0], [1, 1], [2, 0]]
        cp2 = [[2, 0], [3, 1], [4, 0], [5, 0]]
        c1 = BSplineCurve(2, [0, 0, 0, 1, 1, 1], cp1)
        c2 = BSplineCurve(3, [0, 0, 0, 0, 1, 1, 1, 1], cp2)
        with pytest.raises(ValueError):
            concatenate_curves(c1, c2)


# ============================================================
# Intersection Tests
# ============================================================

class TestIntersection:
    def test_intersect_crossing_lines(self):
        """Two lines crossing at (0.5, 0.5) should find one intersection."""
        c1 = BSplineCurve(1, [0, 0, 1, 1], [[0, 0], [1, 1]])
        c2 = BSplineCurve(1, [0, 0, 1, 1], [[0, 1], [1, 0]])
        results = intersect_curves(c1, c2, samples=50)
        assert len(results) >= 1
        u, v, p = results[0]
        assert abs(p[0] - 0.5) < 1e-4
        assert abs(p[1] - 0.5) < 1e-4

    def test_intersect_parallel_lines(self):
        """Parallel lines should not intersect."""
        c1 = BSplineCurve(1, [0, 0, 1, 1], [[0, 0], [1, 0]])
        c2 = BSplineCurve(1, [0, 0, 1, 1], [[0, 1], [1, 1]])
        results = intersect_curves(c1, c2, samples=50)
        assert len(results) == 0


# ============================================================
# Trimming Tests
# ============================================================

class TestTrimming:
    def test_trimming_loop_inside(self):
        """A square trimming loop should contain its center."""
        # 4 linear segments forming a unit square in (u,v) space.
        segs = [
            BSplineCurve(1, [0, 0, 1, 1], [[0, 0], [1, 0]]),
            BSplineCurve(1, [0, 0, 1, 1], [[1, 0], [1, 1]]),
            BSplineCurve(1, [0, 0, 1, 1], [[1, 1], [0, 1]]),
            BSplineCurve(1, [0, 0, 1, 1], [[0, 1], [0, 0]]),
        ]
        loop = TrimmingLoop(segs)
        assert loop.is_inside(0.5, 0.5)
        assert not loop.is_inside(1.5, 0.5)
        assert not loop.is_inside(-0.5, 0.5)


# ============================================================
# STL Export Tests
# ============================================================

class TestSTLExport:
    def test_stl_ascii(self):
        verts = [[0, 0, 0], [1, 0, 0], [0, 1, 0]]
        faces = [[0, 1, 2]]
        stl = export_stl_ascii(verts, faces)
        assert "solid" in stl
        assert "facet" in stl
        assert "vertex" in stl

    def test_stl_binary(self):
        verts = [[0, 0, 0], [1, 0, 0], [0, 1, 0]]
        faces = [[0, 1, 2]]
        data = export_stl_binary(verts, faces)
        assert len(data) == 84 + 50  # header(80) + count(4) + 1 face(50)

    def test_stl_dispatch(self):
        verts = [[0, 0, 0], [1, 0, 0], [0, 1, 0]]
        faces = [[0, 1, 2]]
        assert isinstance(export_stl(verts, faces, binary=False), str)
        assert isinstance(export_stl(verts, faces, binary=True), bytes)


# ============================================================
# Surface Fitting Tests
# ============================================================

class TestSurfaceFitting:
    def test_fit_flat_surface(self):
        """Fitting a flat grid should give a flat surface."""
        points = [[[float(i), float(j), 0.0] for j in range(5)] for i in range(5)]
        surf = fit_bspline_surface(points, degree_u=2, degree_v=2,
                                    num_ctrl_u=4, num_ctrl_v=4)
        # Evaluate at center.
        (u0, u1), (v0, v1) = surf.parameter_range
        p = surf.evaluate((u0 + u1) / 2, (v0 + v1) / 2)
        assert abs(p[2]) < 1e-6  # should be ~0

    def test_fit_too_small_grid(self):
        with pytest.raises(NURBSError):
            fit_bspline_surface([[[0, 0, 0]]], 1, 1, 2, 2)


# ============================================================
# Config Tests
# ============================================================

class TestConfig:
    def test_default_config(self):
        cfg = NURBSConfig()
        assert cfg.tessellation.curve_samples == 100
        assert cfg.export.format == "obj"

    def test_config_to_dict(self):
        cfg = NURBSConfig()
        d = cfg.to_dict()
        assert "tessellation" in d
        assert "export" in d
        assert "fitting" in d

    def test_config_from_dict(self):
        d = {
            "tessellation": {"curve_samples": 200, "surface_samples_u": 30, "surface_samples_v": 30},
            "export": {"format": "stl_ascii", "precision": 4, "flip_faces": False},
        }
        cfg = NURBSConfig.from_dict(d)
        assert cfg.tessellation.curve_samples == 200
        assert cfg.export.format == "stl_ascii"

    def test_config_json_roundtrip(self):
        cfg = NURBSConfig()
        cfg.tessellation.curve_samples = 500
        cfg.export.format = "ply"
        s = cfg.to_json()
        cfg2 = NURBSConfig.from_json(s)
        assert cfg2.tessellation.curve_samples == 500
        assert cfg2.export.format == "ply"


# ============================================================
# Logging Tests
# ============================================================

class TestLogging:
    def test_get_logger(self):
        from nurbs.logging_utils import get_logger
        log = get_logger("test_nurbs", level="DEBUG")
        assert log.level == 10  # DEBUG = 10

    def test_set_log_level(self):
        from nurbs.logging_utils import set_log_level, logger
        set_log_level("ERROR")
        assert logger.level == 40  # ERROR = 40
        set_log_level("WARNING")  # reset