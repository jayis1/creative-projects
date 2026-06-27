"""
Comprehensive bug-hunt test suite for the delaunay-voronoi toolkit.

Each test exercises an edge case; failures indicate bugs that were found
and fixed during Phase 3.
"""
import os, sys, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from delaunay_voronoi.geometry import (
    Point, Edge, Triangle, Circle, orient2d, incircle, circumcenter,
    bounding_box, segment_intersection,
)
from delaunay_voronoi.delaunay import DelaunayTriangulation
from delaunay_voronoi.voronoi import VoronoiDiagram, VoronoiCell
from delaunay_voronoi.convex_hull import convex_hull
from delaunay_voronoi.lloyd import lloyd_relaxation, generate_poisson_seed
from delaunay_voronoi.refine import ruppert_refine, _min_angle_sin_ratio
from delaunay_voronoi.spatial import nearest_neighbor, k_nearest_neighbors, locate_point
from delaunay_voronoi.polygon import (
    polygon_area, polygon_centroid, point_in_polygon,
    sutherland_hodgman_clip, ear_clip_triangulate,
)
from delaunay_voronoi.render import render_svg, render_ppm
from delaunay_voronoi.serialize import (
    triangulation_to_dict, triangulation_from_dict, save_json, load_json,
)


# ---------------------------------------------------------------------------
# Geometry predicates
# ---------------------------------------------------------------------------

class TestOrient2d:
    def test_ccw(self):
        assert orient2d(Point(0,0), Point(1,0), Point(0,1)) > 0

    def test_cw(self):
        assert orient2d(Point(0,0), Point(0,1), Point(1,0)) < 0

    def test_collinear(self):
        assert orient2d(Point(0,0), Point(1,1), Point(2,2)) == 0

    def test_collinear_exact(self):
        """Exact arithmetic should detect collinearity of large coords."""
        assert orient2d(Point(0,0), Point(1e15,1e15), Point(2e15,2e15)) == 0


class TestIncircle:
    def test_inside(self):
        # Equilateral-ish triangle, point inside circumcircle
        a, b, c = Point(0,0), Point(2,0), Point(1, 1.732)
        d = Point(1, 0.5)
        assert incircle(a, b, c, d) > 0

    def test_outside(self):
        a, b, c = Point(0,0), Point(2,0), Point(1, 1.732)
        d = Point(10, 10)
        assert incircle(a, b, c, d) < 0

    def test_on_circle(self):
        """A point exactly on the circumcircle gives zero."""
        a, b, c = Point(0,0), Point(4,0), Point(0,4)
        # circumcircle center (2,2) radius sqrt(8); point (4,4) is on it
        d = Point(4, 4)
        assert incircle(a, b, c, d) == 0


class TestCircumcenter:
    def test_basic(self):
        c = circumcenter(Point(0,0), Point(4,0), Point(0,4))
        assert abs(c.x - 2.0) < 1e-9
        assert abs(c.y - 2.0) < 1e-9

    def test_collinear_raises(self):
        with pytest.raises(ValueError):
            circumcenter(Point(0,0), Point(1,1), Point(2,2))


class TestCircumcircle:
    def test_returns_circle(self):
        """circumcircle() must return a Circle, not a bare tuple."""
        t = Triangle(Point(0,0), Point(4,0), Point(0,4))
        cc = t.circumcircle()
        assert isinstance(cc, Circle), f"Expected Circle, got {type(cc)}"
        assert abs(cc.center.x - 2.0) < 1e-9
        assert abs(cc.center.y - 2.0) < 1e-9

    def test_degenerate_returns_circle(self):
        """Degenerate (collinear) triangle should still return a Circle."""
        t = Triangle(Point(0,0), Point(1,1), Point(2,2))
        cc = t.circumcircle()
        assert isinstance(cc, Circle), f"Expected Circle, got {type(cc)}"


class TestBoundingBox:
    def test_empty_raises(self):
        with pytest.raises(ValueError):
            bounding_box([])

    def test_single(self):
        mn, mx = bounding_box([Point(5, 3)])
        assert mn == Point(5, 3) and mx == Point(5, 3)


# ---------------------------------------------------------------------------
# Delaunay triangulation
# ---------------------------------------------------------------------------

class TestDelaunay:
    def test_min_points(self):
        with pytest.raises(ValueError):
            DelaunayTriangulation.from_points([Point(0,0)])
        with pytest.raises(ValueError):
            DelaunayTriangulation.from_points([Point(0,0), Point(1,1)])

    def test_square(self):
        pts = [Point(0,0), Point(10,0), Point(10,10), Point(0,10)]
        dt = DelaunayTriangulation.from_points(pts)
        # 4 points → 2 triangles
        assert len(dt.triangles) == 2

    def test_no_super_triangles_remain(self):
        pts = [Point(0,0), Point(10,0), Point(10,10), Point(0,10)]
        dt = DelaunayTriangulation.from_points(pts)
        for t in dt.triangles:
            for v in t.vertices():
                assert v in pts, f"Super-triangle vertex leaked: {v}"

    def test_delaunay_property(self):
        """No point should be inside the circumcircle of any triangle."""
        pts = generate_poisson_seed(30, (Point(0,0), Point(400,300)), seed=7)
        dt = DelaunayTriangulation.from_points(pts)
        for t in dt.triangles:
            for p in pts:
                if not t.shares_vertex(p):
                    # p must NOT be strictly inside the circumcircle
                    assert incircle(t.a, t.b, t.c, p) <= 1e-6, \
                        "Delaunay property violated"

    def test_collinear_points(self):
        """Collinear points have zero-area triangles; should not crash."""
        pts = [Point(0,0), Point(5,0), Point(10,0), Point(3,0)]
        # All collinear → no valid triangles
        dt = DelaunayTriangulation.from_points(pts)
        # Should produce 0 triangles (all degenerate)
        # (At minimum, must not crash or hang)
        assert len(dt.triangles) == 0 or all(
            t.area() > 0 for t in dt.triangles
        )

    def test_duplicate_points(self):
        """Duplicate points should be handled gracefully."""
        pts = [Point(0,0), Point(10,0), Point(10,10), Point(0,0)]
        dt = DelaunayTriangulation.from_points(pts)
        # Should not crash; may produce fewer triangles
        assert len(dt.triangles) >= 0

    def test_three_points(self):
        pts = [Point(0,0), Point(1,0), Point(0,1)]
        dt = DelaunayTriangulation.from_points(pts)
        assert len(dt.triangles) == 1


# ---------------------------------------------------------------------------
# Convex hull
# ---------------------------------------------------------------------------

class TestConvexHull:
    def test_square(self):
        pts = [Point(0,0), Point(10,0), Point(10,10), Point(0,10), Point(5,5)]
        hull = convex_hull(pts)
        assert len(hull) == 4
        assert Point(5,5) not in hull

    def test_collinear(self):
        pts = [Point(0,0), Point(1,1), Point(2,2), Point(3,3)]
        hull = convex_hull(pts)
        # Collinear points → at most 2 endpoints
        assert len(hull) <= 2

    def test_single_point(self):
        hull = convex_hull([Point(1,1)])
        assert hull == [Point(1,1)]

    def test_empty(self):
        assert convex_hull([]) == []

    def test_duplicates(self):
        pts = [Point(0,0), Point(0,0), Point(10,0), Point(10,0), Point(5,5)]
        hull = convex_hull(pts)
        assert len(hull) == 3  # triangle


# ---------------------------------------------------------------------------
# Voronoi
# ---------------------------------------------------------------------------

class TestVoronoi:
    def test_basic(self):
        pts = [Point(0,0), Point(10,0), Point(10,10), Point(0,10)]
        dt = DelaunayTriangulation.from_points(pts)
        vd = VoronoiDiagram.from_delaunay(dt, clip_box=(Point(-5,-5), Point(15,15)))
        assert len(vd.sites) == 4
        assert len(vd.edges) > 0

    def test_cells_exist(self):
        pts = generate_poisson_seed(15, (Point(0,0), Point(100,100)), seed=3)
        dt = DelaunayTriangulation.from_points(pts)
        vd = VoronoiDiagram.from_delaunay(dt, clip_box=(Point(0,0), Point(100,100)))
        assert len(vd.cells) == len(pts)
        # Interior cells should have at least 3 vertices
        interior_count = sum(1 for c in vd.cells.values() if len(c.vertices) >= 3)
        assert interior_count > 0

    def test_cell_area_positive(self):
        pts = generate_poisson_seed(10, (Point(0,0), Point(100,100)), seed=11)
        dt = DelaunayTriangulation.from_points(pts)
        vd = VoronoiDiagram.from_delaunay(dt, clip_box=(Point(0,0), Point(100,100)))
        for cell in vd.cells.values():
            if len(cell.vertices) >= 3:
                assert cell.area() > 0


# ---------------------------------------------------------------------------
# Lloyd relaxation
# ---------------------------------------------------------------------------

class TestLloyd:
    def test_relaxation_converges(self):
        box = (Point(0,0), Point(100,100))
        pts = generate_poisson_seed(20, box, seed=5)
        relaxed = lloyd_relaxation(pts, iterations=10, clip_box=box, seed=5)
        assert len(relaxed) == len(pts)
        # All points should be inside the box
        for p in relaxed:
            assert 0 <= p.x <= 100
            assert 0 <= p.y <= 100

    def test_zero_iterations(self):
        pts = [Point(1,1), Point(2,2), Point(3,3)]
        result = lloyd_relaxation(pts, iterations=0)
        assert result == pts

    def test_empty(self):
        assert lloyd_relaxation([], iterations=5) == []


# ---------------------------------------------------------------------------
# Ruppert refinement
# ---------------------------------------------------------------------------

class TestRuppert:
    def test_refine_terminates(self):
        pts = generate_poisson_seed(10, (Point(0,0), Point(100,100)), seed=1)
        refined = ruppert_refine(pts, min_angle_deg=20, max_points=200)
        assert len(refined) >= len(pts)

    def test_no_infinite_loop(self):
        """Even with aggressive angle, should not hang."""
        pts = generate_poisson_seed(5, (Point(0,0), Point(50,50)), seed=2)
        refined = ruppert_refine(pts, min_angle_deg=35, max_points=50)
        assert len(refined) < 500  # safety

    def test_max_area(self):
        # Use enough points that triangles can be made small
        pts = generate_poisson_seed(30, (Point(0,0), Point(200,200)), seed=4)
        refined = ruppert_refine(pts, min_angle_deg=20, max_area=500, max_points=500)
        dt = DelaunayTriangulation.from_points(refined)
        # After refinement, the number of large triangles should decrease
        # compared to the initial mesh.
        dt0 = DelaunayTriangulation.from_points(pts)
        large0 = sum(1 for t in dt0.triangles if t.area() > 500)
        large = sum(1 for t in dt.triangles if t.area() > 500)
        assert large < large0  # refinement should reduce large triangles


# ---------------------------------------------------------------------------
# Spatial queries
# ---------------------------------------------------------------------------

class TestSpatial:
    def test_nearest_neighbor(self):
        pts = [Point(0,0), Point(10,0), Point(0,10), Point(10,10)]
        dt = DelaunayTriangulation.from_points(pts)
        nn = nearest_neighbor(dt, Point(9, 9))
        assert nn == Point(10, 10)

    def test_nearest_neighbor_exact(self):
        pts = [Point(0,0), Point(5,0), Point(10,0)]
        dt = DelaunayTriangulation.from_points(pts)
        nn = nearest_neighbor(dt, Point(2, 0))
        assert nn == Point(0, 0)

    def test_knn(self):
        pts = generate_poisson_seed(20, (Point(0,0), Point(100,100)), seed=8)
        dt = DelaunayTriangulation.from_points(pts)
        knn = k_nearest_neighbors(dt, Point(50,50), 5)
        assert len(knn) == 5
        assert knn[0] == nearest_neighbor(dt, Point(50,50))

    def test_locate_inside(self):
        pts = [Point(0,0), Point(10,0), Point(10,10), Point(0,10)]
        dt = DelaunayTriangulation.from_points(pts)
        tri = locate_point(dt, Point(5, 5))
        assert tri is not None

    def test_locate_outside(self):
        pts = [Point(0,0), Point(10,0), Point(10,10), Point(0,10)]
        dt = DelaunayTriangulation.from_points(pts)
        tri = locate_point(dt, Point(-5, -5))
        assert tri is None


# ---------------------------------------------------------------------------
# Polygon utilities
# ---------------------------------------------------------------------------

class TestPolygon:
    def test_area(self):
        square = [Point(0,0), Point(10,0), Point(10,10), Point(0,10)]
        assert polygon_area(square) == 100.0

    def test_area_triangle(self):
        tri = [Point(0,0), Point(6,0), Point(0,4)]
        assert polygon_area(tri) == 12.0

    def test_centroid_square(self):
        square = [Point(0,0), Point(10,0), Point(10,10), Point(0,10)]
        c = polygon_centroid(square)
        assert abs(c.x - 5.0) < 1e-9
        assert abs(c.y - 5.0) < 1e-9

    def test_point_in_polygon_edge(self):
        square = [Point(0,0), Point(10,0), Point(10,10), Point(0,10)]
        # Edge points — behavior may vary but should not crash
        assert point_in_polygon(Point(5, 0), square) in (True, False)

    def test_point_in_polygon_center(self):
        square = [Point(0,0), Point(10,0), Point(10,10), Point(0,10)]
        assert point_in_polygon(Point(5, 5), square) is True

    def test_point_in_polygon_vertex(self):
        """Point exactly on a vertex should be handled (may be True or False)."""
        square = [Point(0,0), Point(10,0), Point(10,10), Point(0,10)]
        # Should not crash
        result = point_in_polygon(Point(0, 0), square)
        assert isinstance(result, bool)

    def test_point_in_polygon_complex(self):
        """Star-shaped polygon."""
        star = [Point(50,0), Point(61,35), Point(98,35), Point(68,57),
                Point(79,91), Point(50,70), Point(21,91), Point(32,57),
                Point(2,35), Point(39,35)]
        assert point_in_polygon(Point(50, 50), star) is True
        assert point_in_polygon(Point(0, 0), star) is False

    def test_point_outside(self):
        square = [Point(0,0), Point(10,0), Point(10,10), Point(0,10)]
        assert point_in_polygon(Point(15, 5), square) is False

    def test_clip(self):
        subject = [Point(0,0), Point(10,0), Point(10,10), Point(0,10)]
        clip = [Point(5,5), Point(20,5), Point(20,20), Point(5,20)]
        result = sutherland_hodgman_clip(subject, clip)
        # Clipped area = 25
        assert abs(polygon_area(result) - 25.0) < 1e-6

    def test_ear_clip(self):
        square = [Point(0,0), Point(10,0), Point(10,10), Point(0,10)]
        tris = ear_clip_triangulate(square)
        assert len(tris) == 2
        # Total area should match
        total = sum(
            abs(
                (t[1].x - t[0].x) * (t[2].y - t[0].y)
                - (t[2].x - t[0].x) * (t[1].y - t[0].y)
            ) / 2.0
            for t in tris
        )
        assert abs(total - 100.0) < 1e-6

    def test_ear_clip_concave(self):
        # Concave polygon (arrow)
        poly = [Point(0,0), Point(10,5), Point(0,10), Point(3,5)]
        tris = ear_clip_triangulate(poly)
        assert len(tris) == 2


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

class TestRender:
    def test_svg_basic(self):
        svg = render_svg(width=100, height=80)
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_svg_with_data(self):
        pts = [Point(0,0), Point(50,0), Point(25,50)]
        dt = DelaunayTriangulation.from_points(pts)
        svg = render_svg(width=100, height=80, delaunay_edges=dt.edges(),
                         points=pts)
        assert "circle" in svg

    def test_ppm_basic(self):
        pts = [Point(10,10), Point(50,40), Point(90,10)]
        data = render_ppm(100, 80, pts)
        assert data.startswith(b"P6\n")
        # P6 header: "P6\n100 80\n255\n"
        assert len(data) > 100 * 80 * 3

    def test_ppm_empty(self):
        """PPM with no points should produce a valid flat-filled image."""
        data = render_ppm(10, 10, [])
        assert data.startswith(b"P6\n10 10\n255\n")
        # 10*10 pixels * 3 bytes = 300 + header
        assert len(data) == len(b"P6\n10 10\n255\n") + 300


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

class TestSerialize:
    def test_roundtrip(self):
        pts = generate_poisson_seed(15, (Point(0,0), Point(100,100)), seed=6)
        dt = DelaunayTriangulation.from_points(pts)
        d = triangulation_to_dict(dt)
        dt2 = triangulation_from_dict(d)
        assert len(dt2.triangles) == len(dt.triangles)
        assert len(dt2.points) == len(pts)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])