"""Comprehensive test suite for the NURBS toolkit."""
import math
import pytest
from nurbs import (
    BSplineBasis,
    BSplineCurve,
    NURBSCurve,
    NURBSSurface,
    BezierCurve,
    bezier_to_bspline,
    find_span,
    basis_functions,
    basis_functions_derivatives,
    knot_insert,
    knot_remove,
    degree_elevate,
    decompose_bezier_segments,
    generate_uniform_knot_vector,
    generate_clamped_uniform_knot_vector,
    validate_knot_vector,
    tessellate_curve,
    tessellate_surface,
    export_obj,
    export_ply_ascii,
    fit_bspline_curve,
    project_point,
    arc_length,
    reparameterize_arc_length,
    make_circle,
    make_sphere_patch,
    make_torus,
    make_cylinder,
    make_cone,
    curve_to_svg,
    surface_to_svg_wireframe,
    curve_to_dict,
    curve_from_dict,
    curve_to_json,
    curve_from_json,
    surface_to_dict,
    surface_from_dict,
    surface_to_json,
    surface_from_json,
    NURBSError,
    InvalidKnotVector,
    InvalidControlPoint,
    InvalidWeight,
    SingularMatrix,
)


# ============================================================
# Knot Vector Tests
# ============================================================

class TestKnotVector:
    def test_uniform_length(self):
        kv = generate_uniform_knot_vector(5, 3)
        assert len(kv) == 5 + 3 + 2

    def test_clamped_length(self):
        kv = generate_clamped_uniform_knot_vector(5, 3)
        assert len(kv) == 5 + 3 + 2

    def test_clamped_endpoints(self):
        kv = generate_clamped_uniform_knot_vector(5, 3)
        assert kv[0] == 0.0
        assert kv[-1] == 3.0  # n - p + 1 = 5 - 3 + 1 = 3
        # First p+1 values should be 0.
        assert all(x == 0.0 for x in kv[:4])
        # Last p+1 values should be the max.
        assert all(x == 3.0 for x in kv[-4:])

    def test_clamped_bezier(self):
        # Bezier with n=p should have only 0 and 1 as knots.
        kv = generate_clamped_uniform_knot_vector(3, 3)
        assert kv == [0, 0, 0, 0, 1, 1, 1, 1]

    def test_validate_non_decreasing(self):
        with pytest.raises(ValueError):
            validate_knot_vector([0, 1, 0.5, 2], 1, 1)

    def test_validate_wrong_length(self):
        with pytest.raises(ValueError):
            validate_knot_vector([0, 0, 1, 1], 3, 2)

    def test_validate_multiplicity(self):
        # Multiplicity > p+1 should fail.
        with pytest.raises(ValueError):
            validate_knot_vector([0, 0, 0, 0, 0, 1, 1, 1, 1], 3, 2)

    def test_negative_n(self):
        with pytest.raises(ValueError):
            generate_clamped_uniform_knot_vector(-1, 2)

    def test_n_less_than_p(self):
        with pytest.raises(ValueError):
            generate_clamped_uniform_knot_vector(1, 3)


# ============================================================
# Basis Function Tests
# ============================================================

class TestBasisFunctions:
    def test_partition_of_unity(self):
        """Non-zero basis functions at any u sum to 1."""
        p = 3
        U = generate_clamped_uniform_knot_vector(6, p)
        n = 6
        basis = BSplineBasis(p, U)
        for t in [0.0, 0.1, 0.5, 1.0, 1.5, 2.5, 3.0]:
            vals = basis.evaluate_all(t)
            assert abs(sum(vals) - 1.0) < 1e-10, f"sum={sum(vals)} at u={t}"

    def test_endpoint_clamped(self):
        """At u=0 for clamped, only N_0 should be 1."""
        p = 2
        U = generate_clamped_uniform_knot_vector(4, p)
        basis = BSplineBasis(p, U)
        vals = basis.evaluate_all(0.0)
        assert abs(vals[0] - 1.0) < 1e-10
        for i in range(1, len(vals)):
            assert abs(vals[i]) < 1e-10

    def test_find_span_end(self):
        U = [0, 0, 0, 1, 2, 3, 3, 3]
        # n = 4, p = 2; at u=3 (end), span should be n=4.
        assert find_span(4, 2, 3.0, U) == 4

    def test_find_span_start(self):
        U = [0, 0, 0, 1, 2, 3, 3, 3]
        assert find_span(4, 2, 0.0, U) == 2  # p=2

    def test_find_span_mid(self):
        U = [0, 0, 0, 1, 2, 3, 3, 3]
        assert find_span(4, 2, 1.5, U) == 3

    def test_basis_nonneg(self):
        p = 3
        U = generate_clamped_uniform_knot_vector(5, p)
        basis = BSplineBasis(p, U)
        for t in [0.01, 0.5, 1.5, 2.0]:
            vals = basis.evaluate_all(t)
            for v in vals:
                assert v >= -1e-10


# ============================================================
# B-spline Curve Tests
# ============================================================

class TestBSplineCurve:
    def test_bezier_endpoint_interpolation(self):
        """Clamped B-spline with n=p is a Bezier curve."""
        cp = [[0, 0], [1, 2], [3, 2], [4, 0]]
        U = generate_clamped_uniform_knot_vector(3, 3)
        c = BSplineCurve(3, U, cp)
        assert c.evaluate(0.0) == [0.0, 0.0]
        assert c.evaluate(1.0) == [4.0, 0.0]

    def test_derivative_line(self):
        """Derivative of a degree-1 (linear) curve is constant."""
        cp = [[0, 0], [1, 1]]
        U = [0, 0, 1, 1]
        c = BSplineCurve(1, U, cp)
        d = c.derivative(0.5, 1)
        assert abs(d[0] - 1.0) < 1e-10
        assert abs(d[1] - 1.0) < 1e-10

    def test_derivative_zero_at_endpoint_bezier(self):
        """2nd derivative of a linear curve is zero."""
        cp = [[0, 0], [1, 1]]
        U = [0, 0, 1, 1]
        c = BSplineCurve(1, U, cp)
        d2 = c.derivative(0.5, 2)
        assert all(abs(x) < 1e-10 for x in d2)

    def test_too_few_control_points(self):
        with pytest.raises(ValueError):
            BSplineCurve(3, [0, 0, 0, 0, 1, 1, 1, 1], [[0, 0], [1, 1]])

    def test_parameter_range(self):
        cp = [[0, 0], [1, 1], [2, 0]]
        U = [0, 0, 0, 1, 1, 1]
        c = BSplineCurve(2, U, cp)
        assert c.parameter_range == (0.0, 1.0)

    def test_tangent_unit(self):
        cp = [[0, 0, 0], [1, 1, 0], [2, 0, 0]]
        U = [0, 0, 0, 1, 1, 1]
        c = BSplineCurve(2, U, cp)
        t = c.tangent(0.5)
        assert abs(math.sqrt(sum(x * x for x in t)) - 1.0) < 1e-10


# ============================================================
# NURBS Curve Tests
# ============================================================

class TestNURBSCurve:
    def test_quarter_circle(self):
        """NURBS quarter circle should have exact radius 1."""
        cps = [[1, 0, 0], [1, 1, 0], [0, 1, 0]]
        w = [1.0, 1.0 / math.sqrt(2), 1.0]
        U = [0, 0, 0, 1, 1, 1]
        nc = NURBSCurve(2, U, cps, w)
        for u in [0.0, 0.25, 0.5, 0.75, 1.0]:
            p = nc.evaluate(u)
            r = math.hypot(p[0], p[1])
            assert abs(r - 1.0) < 1e-6, f"radius={r} at u={u}"

    def test_nurbs_equals_bspline_when_weights_equal(self):
        """With all weights=1, NURBS == B-spline."""
        cp = [[0, 0, 0], [1, 2, 0], [3, 2, 0], [4, 0, 0]]
        U = generate_clamped_uniform_knot_vector(3, 3)
        bs = BSplineCurve(3, U, cp)
        nc = NURBSCurve(3, U, cp)
        for u in [0.0, 0.3, 0.7, 1.0]:
            pb = bs.evaluate(u)
            pn = nc.evaluate(u)
            assert all(abs(a - b) < 1e-10 for a, b in zip(pb, pn))

    def test_negative_weight(self):
        cps = [[0, 0], [1, 1], [2, 0]]
        with pytest.raises((InvalidWeight, ValueError)):
            NURBSCurve(2, [0, 0, 0, 1, 1, 1], cps, [1.0, -1.0, 1.0])

    def test_weight_count_mismatch(self):
        cps = [[0, 0], [1, 1], [2, 0]]
        with pytest.raises((InvalidWeight, ValueError)):
            NURBSCurve(2, [0, 0, 0, 1, 1, 1], cps, [1.0, 1.0])

    def test_inconsistent_dim(self):
        cps = [[0, 0], [1, 1, 1], [2, 0]]
        with pytest.raises((InvalidControlPoint, ValueError)):
            NURBSCurve(2, [0, 0, 0, 1, 1, 1], cps)

    def test_nurbs_derivative_circle(self):
        """Derivative of a circle should be tangent (perpendicular to radius)."""
        cps = [[1, 0, 0], [1, 1, 0], [0, 1, 0]]
        w = [1.0, 1.0 / math.sqrt(2), 1.0]
        U = [0, 0, 0, 1, 1, 1]
        nc = NURBSCurve(2, U, cps, w)
        for u in [0.1, 0.5, 0.9]:
            p = nc.evaluate(u)
            d = nc.derivative(u, 1)
            # Tangent should be perpendicular to radius.
            dot = p[0] * d[0] + p[1] * d[1]
            assert abs(dot) < 1e-5, f"dot={dot} at u={u}"


# ============================================================
# NURBS Surface Tests
# ============================================================

class TestNURBSSurface:
    def test_bilinear_patch(self):
        cps = [[[0, 0, 0], [0, 1, 0]], [[1, 0, 0], [1, 1, 0]]]
        s = NURBSSurface(1, 1, [0, 0, 1, 1], [0, 0, 1, 1], cps)
        p = s.evaluate(0.5, 0.5)
        assert p == [0.5, 0.5, 0.0]

    def test_normal_flat(self):
        cps = [[[0, 0, 0], [0, 1, 0]], [[1, 0, 0], [1, 1, 0]]]
        s = NURBSSurface(1, 1, [0, 0, 1, 1], [0, 0, 1, 1], cps)
        n = s.normal(0.5, 0.5)
        assert abs(n[2] - 1.0) < 1e-10 or abs(n[2] + 1.0) < 1e-10

    def test_ragged_grid(self):
        cps = [[[0, 0, 0], [0, 1, 0]], [[1, 0, 0]]]  # second row has 1 cp
        with pytest.raises((InvalidControlPoint, ValueError)):
            NURBSSurface(1, 1, [0, 0, 1, 1], [0, 0, 1, 1], cps)

    def test_parameter_range(self):
        cps = [[[0, 0, 0], [0, 1, 0]], [[1, 0, 0], [1, 1, 0]]]
        s = NURBSSurface(1, 1, [0, 0, 1, 1], [0, 0, 1, 1], cps)
        (u0, u1), (v0, v1) = s.parameter_range
        assert (u0, u1) == (0.0, 1.0)
        assert (v0, v1) == (0.0, 1.0)


# ============================================================
# Bezier Tests
# ============================================================

class TestBezier:
    def test_evaluate_endpoints(self):
        bz = BezierCurve([[0, 0], [1, 2], [3, 2], [4, 0]])
        assert bz.evaluate(0) == [0, 0]
        assert bz.evaluate(1) == [4, 0]

    def test_degree(self):
        bz = BezierCurve([[0, 0], [1, 2], [3, 2], [4, 0]])
        assert bz.degree == 3

    def test_subdivide_endpoints(self):
        bz = BezierCurve([[0, 0], [1, 2], [3, 2], [4, 0]])
        left, right = bz.subdivide(0.5)
        assert left.evaluate(0) == [0, 0]
        assert right.evaluate(1) == [4, 0]
        # left(1) == right(0) == original(0.5)
        assert all(abs(a - b) < 1e-10 for a, b in
                    zip(left.evaluate(1), right.evaluate(0)))
        assert all(abs(a - b) < 1e-10 for a, b in
                    zip(left.evaluate(1), bz.evaluate(0.5)))

    def test_elevate_preserves_curve(self):
        bz = BezierCurve([[0, 0], [1, 2], [3, 2], [4, 0]])
        elevated = bz.elevate_degree()
        assert elevated.degree == 4
        for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
            p1 = bz.evaluate(t)
            p2 = elevated.evaluate(t)
            assert all(abs(a - b) < 1e-10 for a, b in zip(p1, p2))

    def test_too_few_points(self):
        with pytest.raises(ValueError):
            BezierCurve([[0, 0]])

    def test_bezier_to_bspline(self):
        bz = BezierCurve([[0, 0], [1, 2], [3, 2], [4, 0]])
        bs = bezier_to_bspline(bz)
        for t in [0.0, 0.3, 0.7, 1.0]:
            p1 = bz.evaluate(t)
            p2 = bs.evaluate(t)
            assert all(abs(a - b) < 1e-10 for a, b in zip(p1, p2))


# ============================================================
# Operations Tests
# ============================================================

class TestOperations:
    def test_knot_insert_preserves_curve(self):
        cp = [[0, 0, 0], [1, 2, 0], [3, 2, 0], [4, 0, 0]]
        U = generate_clamped_uniform_knot_vector(3, 3)
        c = BSplineCurve(3, U, cp)
        c2 = knot_insert(c, 0.5, 1)
        for u in [0.0, 0.3, 0.5, 0.7, 1.0]:
            p1 = c.evaluate(u)
            p2 = c2.evaluate(u)
            assert all(abs(a - b) < 1e-10 for a, b in zip(p1, p2))
        assert len(c2.control_points) == len(c.control_points) + 1

    def test_knot_insert_multiple(self):
        cp = [[0, 0, 0], [1, 2, 0], [3, 2, 0], [4, 0, 0]]
        U = generate_clamped_uniform_knot_vector(3, 3)
        c = BSplineCurve(3, U, cp)
        c2 = knot_insert(c, 0.5, 2)
        for u in [0.0, 0.3, 0.5, 0.7, 1.0]:
            p1 = c.evaluate(u)
            p2 = c2.evaluate(u)
            assert all(abs(a - b) < 1e-10 for a, b in zip(p1, p2))
        assert len(c2.control_points) == len(c.control_points) + 2

    def test_degree_elevate_preserves_curve(self):
        cp = [[0, 0, 0], [1, 2, 0], [3, 2, 0], [4, 0, 0]]
        U = generate_clamped_uniform_knot_vector(3, 3)
        c = BSplineCurve(3, U, cp)
        c2 = degree_elevate(c, 1)
        assert c2.degree == 4
        for u in [0.0, 0.2, 0.5, 0.8, 1.0]:
            p1 = c.evaluate(u)
            p2 = c2.evaluate(u)
            assert all(abs(a - b) < 1e-8 for a, b in zip(p1, p2)), \
                f"mismatch at u={u}: {p1} vs {p2}"

    def test_decompose_bezier(self):
        """A single Bezier segment decomposes to 1 segment."""
        cp = [[0, 0, 0], [1, 2, 0], [3, 2, 0], [4, 0, 0]]
        U = generate_clamped_uniform_knot_vector(3, 3)
        c = BSplineCurve(3, U, cp)
        segs = decompose_bezier_segments(c)
        assert len(segs) == 1
        assert len(segs[0]) == 4  # p+1 control points

    def test_decompose_multi_segment(self):
        """A B-spline with 2 spans should decompose to 2 Bezier segments."""
        cp = [[0, 0], [1, 1], [2, 1], [3, 0], [4, 1]]
        U = [0, 0, 0, 0, 1, 2, 2, 2, 2]  # n=4, p=3, 2 spans
        c = BSplineCurve(3, U, cp)
        segs = decompose_bezier_segments(c)
        assert len(segs) == 2
        for seg in segs:
            assert len(seg) == 4  # p+1


# ============================================================
# Fitting Tests
# ============================================================

class TestFitting:
    def test_fit_line(self):
        """Fitting a line should produce a straight curve."""
        data = [[float(i), float(i), 0] for i in range(5)]
        c = fit_bspline_curve(data, degree=1, num_control_points=2)
        for u in [0.0, 0.5, 1.0]:
            p = c.evaluate(u)
            assert abs(p[0] - p[1]) < 1e-8

    def test_fit_interpolates_endpoints(self):
        """With enough control points, endpoints should be close."""
        data = [[0.0, 0.0, 0], [0.5, 0.3, 0], [1.0, 0.5, 0],
                [1.5, 0.3, 0], [2.0, 0.0, 0]]
        c = fit_bspline_curve(data, degree=3, num_control_points=5)
        p0 = c.evaluate(0.0)
        p1 = c.evaluate(c.parameter_range[1])
        assert all(abs(a - b) < 1e-4 for a, b in zip(p0, data[0]))
        assert all(abs(a - b) < 1e-4 for a, b in zip(p1, data[-1]))

    def test_too_many_control_points(self):
        data = [[0, 0], [1, 1]]
        with pytest.raises(ValueError):
            fit_bspline_curve(data, degree=1, num_control_points=3)

    def test_too_few_points(self):
        with pytest.raises(ValueError):
            fit_bspline_curve([[0, 0]], degree=1, num_control_points=2)


# ============================================================
# Projection Tests
# ============================================================

class TestProjection:
    def test_project_on_curve(self):
        """Projecting a point that's on the curve should return u close."""
        cp = [[0, 0, 0], [1, 2, 0], [3, 2, 0], [4, 0, 0]]
        U = generate_clamped_uniform_knot_vector(3, 3)
        c = BSplineCurve(3, U, cp)
        target_u = 0.5
        pt = c.evaluate(target_u)
        u, closest = project_point(c, pt, samples=200)
        assert abs(u - target_u) < 1e-4
        assert all(abs(a - b) < 1e-4 for a, b in zip(closest, pt))


# ============================================================
# Arc Length Tests
# ============================================================

class TestArcLength:
    def test_line_length(self):
        """Arc length of a line should be its Euclidean length."""
        cp = [[0, 0, 0], [3, 4, 0]]
        U = [0, 0, 1, 1]
        c = BSplineCurve(1, U, cp)
        length = arc_length(c, samples=100)
        assert abs(length - 5.0) < 1e-4

    def test_circle_circumference(self):
        """Arc length of a circle should be 2*pi*r."""
        circ = make_circle(1.0, (0, 0), 4)
        length = arc_length(circ, samples=1000)
        assert abs(length - 2 * math.pi) < 1e-2

    def test_reparameterize(self):
        cp = [[0, 0, 0], [1, 1, 0], [2, 0, 0]]
        U = [0, 0, 0, 1, 1, 1]
        c = BSplineCurve(2, U, cp)
        table = reparameterize_arc_length(c, num_samples=50)
        assert len(table) == 50
        assert table[0][1] == 0.0
        # Arc length should be monotonically increasing.
        for i in range(1, len(table)):
            assert table[i][1] >= table[i - 1][1]


# ============================================================
# Presets Tests
# ============================================================

class TestPresets:
    def test_circle_exact(self):
        circ = make_circle(1.0, (0, 0), 4)
        for u in [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0]:
            p = circ.evaluate(u)
            r = math.hypot(p[0], p[1])
            assert abs(r - 1.0) < 1e-6, f"r={r} at u={u}"

    def test_circle_radius_2(self):
        circ = make_circle(2.0, (0, 0), 4)
        for u in [0.0, 0.5, 1.0, 2.0, 3.0]:
            p = circ.evaluate(u)
            r = math.hypot(p[0], p[1])
            assert abs(r - 2.0) < 1e-6

    def test_circle_center_offset(self):
        circ = make_circle(1.0, (3, 4), 4)
        for u in [0.0, 1.0, 2.0, 3.0]:
            p = circ.evaluate(u)
            dx = p[0] - 3
            dy = p[1] - 4
            r = math.hypot(dx, dy)
            assert abs(r - 1.0) < 1e-6

    def test_circle_too_few_segments(self):
        with pytest.raises(ValueError):
            make_circle(1.0, (0, 0), 2)

    def test_cylinder(self):
        cyl = make_cylinder(1.0, 2.0, 4)
        # At v=0 (base) should be on circle, at v=2 (top) z=2.
        p_base = cyl.evaluate(0.5, 0.0)
        p_top = cyl.evaluate(0.5, 2.0)
        assert abs(p_base[2]) < 1e-6
        assert abs(p_top[2] - 2.0) < 1e-6
        # Both should be on the circle.
        assert abs(math.hypot(p_base[0], p_base[1]) - 1.0) < 1e-6
        assert abs(math.hypot(p_top[0], p_top[1]) - 1.0) < 1e-6

    def test_cone(self):
        cone = make_cone(1.0, 2.0, 4)
        # At v=0 (base), radius=1; at v=2 (apex), radius=0.
        p_base = cone.evaluate(0.5, 0.0)
        p_apex = cone.evaluate(0.5, 2.0)
        assert abs(math.hypot(p_base[0], p_base[1]) - 1.0) < 1e-6
        assert abs(math.hypot(p_apex[0], p_apex[1])) < 1e-6
        assert abs(p_apex[2] - 2.0) < 1e-6

    def test_torus(self):
        torus = make_torus(R=2.0, r=0.5, u_segments=4, v_segments=4)
        # At any (u, v), the point should be at distance R from z-axis
        # plus/minus r.
        for u in [0.0, 1.0, 2.0]:
            for v in [0.0, 1.0, 2.0]:
                p = torus.evaluate(u, v)
                dist_xy = math.hypot(p[0], p[1])
                # Distance from torus centerline should be r.
                assert abs(dist_xy - 2.0) <= 0.5 + 1e-6
                assert abs(p[2]) <= 0.5 + 1e-6

    def test_sphere_patch(self):
        sp = make_sphere_patch(1.0)
        # Evaluate at center of patch.
        p = sp.evaluate(0.5, 0.5)
        r = math.sqrt(p[0]**2 + p[1]**2 + p[2]**2)
        assert abs(r - 1.0) < 1e-6


# ============================================================
# Serialization Tests
# ============================================================

class TestSerialization:
    def test_bspline_roundtrip(self):
        cp = [[0, 0, 0], [1, 2, 0], [3, 2, 0], [4, 0, 0]]
        U = generate_clamped_uniform_knot_vector(3, 3)
        c = BSplineCurve(3, U, cp)
        s = curve_to_json(c)
        c2 = curve_from_json(s)
        for u in [0.0, 0.5, 1.0]:
            assert c.evaluate(u) == c2.evaluate(u)

    def test_nurbs_roundtrip(self):
        cps = [[1, 0, 0], [1, 1, 0], [0, 1, 0]]
        w = [1.0, 1.0 / math.sqrt(2), 1.0]
        U = [0, 0, 0, 1, 1, 1]
        nc = NURBSCurve(2, U, cps, w)
        s = curve_to_json(nc)
        nc2 = curve_from_json(s)
        for u in [0.0, 0.5, 1.0]:
            assert all(abs(a - b) < 1e-10 for a, b in
                        zip(nc.evaluate(u), nc2.evaluate(u)))

    def test_surface_roundtrip(self):
        cps = [[[0, 0, 0], [0, 1, 0]], [[1, 0, 0], [1, 1, 0]]]
        s = NURBSSurface(1, 1, [0, 0, 1, 1], [0, 0, 1, 1], cps)
        json_str = surface_to_json(s)
        s2 = surface_from_json(json_str)
        assert s.evaluate(0.5, 0.5) == s2.evaluate(0.5, 0.5)

    def test_dict_type(self):
        cp = [[0, 0], [1, 1]]
        c = BSplineCurve(1, [0, 0, 1, 1], cp)
        d = curve_to_dict(c)
        assert d["type"] == "bspline"

        nc = NURBSCurve(1, [0, 0, 1, 1], cp)
        d = curve_to_dict(nc)
        assert d["type"] == "nurbs"


# ============================================================
# Export Tests
# ============================================================

class TestExport:
    def test_tessellate_curve(self):
        cp = [[0, 0, 0], [1, 2, 0], [3, 2, 0], [4, 0, 0]]
        U = generate_clamped_uniform_knot_vector(3, 3)
        c = BSplineCurve(3, U, cp)
        pts = tessellate_curve(c, 10)
        assert len(pts) == 10
        assert pts[0] == [0.0, 0.0, 0.0]
        assert pts[-1] == [4.0, 0.0, 0.0]

    def test_tessellate_surface(self):
        cps = [[[0, 0, 0], [0, 1, 0]], [[1, 0, 0], [1, 1, 0]]]
        s = NURBSSurface(1, 1, [0, 0, 1, 1], [0, 0, 1, 1], cps)
        verts, faces = tessellate_surface(s, 3, 3)
        assert len(verts) == 9
        assert len(faces) == 8  # 2*(2*2)

    def test_export_obj(self):
        verts = [[0, 0, 0], [1, 0, 0], [0, 1, 0]]
        faces = [[0, 1, 2]]
        obj = export_obj(verts, faces)
        assert "v 0.000000 0.000000 0.000000" in obj
        assert "f 1 2 3" in obj  # 1-based

    def test_export_ply(self):
        verts = [[0, 0, 0], [1, 0, 0], [0, 1, 0]]
        faces = [[0, 1, 2]]
        ply = export_ply_ascii(verts, faces)
        assert "ply" in ply
        assert "element vertex 3" in ply
        assert "element face 1" in ply

    def test_tessellate_too_few_samples(self):
        cp = [[0, 0, 0], [1, 2, 0], [3, 2, 0], [4, 0, 0]]
        U = generate_clamped_uniform_knot_vector(3, 3)
        c = BSplineCurve(3, U, cp)
        with pytest.raises(ValueError):
            tessellate_curve(c, 1)


# ============================================================
# SVG Tests
# ============================================================

class TestSVG:
    def test_curve_svg(self):
        cp = [[0, 0], [1, 2], [3, 2], [4, 0]]
        U = generate_clamped_uniform_knot_vector(3, 3)
        c = BSplineCurve(3, U, cp)
        svg = curve_to_svg(c, samples=50)
        assert svg.startswith("<svg")
        assert svg.endswith("</svg>")
        assert "path" in svg

    def test_surface_svg(self):
        cps = [[[0, 0, 0], [0, 1, 0]], [[1, 0, 0], [1, 1, 0]]]
        s = NURBSSurface(1, 1, [0, 0, 1, 1], [0, 0, 1, 1], cps)
        svg = surface_to_svg_wireframe(s, 5, 5)
        assert svg.startswith("<svg")
        assert "</svg>" in svg


# ============================================================
# CLI Tests
# ============================================================

class TestCLI:
    def test_version(self):
        from nurbs.cli import main
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(["version"])
        assert rc == 0
        assert "nurbs-toolkit" in buf.getvalue()

    def test_eval_curve(self):
        from nurbs.cli import main
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main([
                "eval-curve", "--degree", "3",
                "--knots", "0,0,0,0,1,1,1,1",
                "--points", "0,0,0;1,2,0;3,2,0;4,0,0",
                "--u", "0.0",
            ])
        assert rc == 0
        import json
        result = json.loads(buf.getvalue())
        assert result["point"] == [0.0, 0.0, 0.0]

    def test_bezier(self):
        from nurbs.cli import main
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main([
                "bezier",
                "--points", "0,0;1,2;3,2;4,0",
                "--t", "0.0",
            ])
        assert rc == 0
        import json
        result = json.loads(buf.getvalue())
        assert result["point"] == [0.0, 0.0]

    def test_no_command(self):
        from nurbs.cli import main
        rc = main([])
        assert rc == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])