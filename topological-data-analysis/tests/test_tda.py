"""
Test suite for the TDA toolkit.

Tests cover:
- Simplex and SimplexTree data structures
- Complex construction (Rips, weighted Rips, Cech, sublevel)
- Boundary matrix and persistence computation
- Persistence diagrams and barcodes
- Distance metrics (bottleneck, Hausdorff, Wasserstein)
- Betti curves and persistence landscapes
- Persistence images
- JSON serialization
- CLI
"""

import math
import pytest
from tda import (
    Simplex, SimplexTree,
    VietorisRipsComplex, WeightedRipsComplex, CechComplex, SublevelFiltration,
    BoundaryMatrix, reduce_matrix, compute_persistence,
    PersistenceDiagram, PersistencePair,
    diagrams_from_persistence, barcode_string,
    bottleneck_distance, hausdorff_distance, wasserstein_distance,
    betti_curve, persistence_landscape, landscape_norm,
    persistence_image, image_to_ascii,
    plot_diagram_ascii,
    diagrams_to_json, diagrams_from_json, save_diagrams, load_diagrams,
)
from tda.complexes_extra import _circumradius_3pts


# ---------------------------------------------------------------------------
# Simplex tests
# ---------------------------------------------------------------------------

class TestSimplex:
    def test_basic_properties(self):
        s = Simplex((0, 1, 2))
        assert s.dimension == 2
        assert len(s) == 3
        assert s.vertices == (0, 1, 2)

    def test_vertex_sorting(self):
        s = Simplex((2, 0, 1))
        assert s.vertices == (0, 1, 2)

    def test_deduplication(self):
        s = Simplex((0, 0, 1))
        assert s.vertices == (0, 1)
        assert s.dimension == 1

    def test_negative_vertex_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            Simplex((0, -1))

    def test_empty_simplex(self):
        s = Simplex([])
        assert s.dimension == -1
        assert len(s) == 0

    def test_faces(self):
        s = Simplex((0, 1, 2))
        faces = sorted(s.faces())
        assert faces == [Simplex((0, 1)), Simplex((0, 2)), Simplex((1, 2))]

    def test_faces_of_vertex(self):
        s = Simplex((0,))
        assert list(s.faces()) == []

    def test_boundary_of_vertex(self):
        """boundary() should yield nothing for a 0-simplex."""
        s = Simplex((0,))
        assert list(s.boundary()) == []

    def test_boundary_signs(self):
        s = Simplex((0, 1, 2))
        signs = [sign for sign, _ in s.boundary()]
        assert signs == [1, -1, 1]

    def test_equality_and_hashing(self):
        s1 = Simplex((0, 1))
        s2 = Simplex((1, 0))
        assert s1 == s2
        assert hash(s1) == hash(s2)
        assert Simplex((0, 1)) != Simplex((0, 2))

    def test_ordering(self):
        s1 = Simplex((0, 1))
        s2 = Simplex((0, 2))
        assert s1 < s2

    def test_all_subsimplices_of_vertex(self):
        """all_subsimplices of a 0-simplex should be empty (no proper subsimplices)."""
        s = Simplex((0,))
        subs = list(s.all_subsimplices())
        assert subs == []

    def test_all_subsimplices_of_edge(self):
        s = Simplex((0, 1))
        subs = sorted(s.all_subsimplices())
        assert subs == [Simplex((0,)), Simplex((1,))]

    def test_subsimplices_of_dim(self):
        s = Simplex((0, 1, 2))
        verts = sorted(s.subsimplices(0))
        assert verts == [Simplex((0,)), Simplex((1,)), Simplex((2,))]
        edges = sorted(s.subsimplices(1))
        assert len(edges) == 3


# ---------------------------------------------------------------------------
# SimplexTree tests
# ---------------------------------------------------------------------------

class TestSimplexTree:
    def test_insert_and_contains(self):
        st = SimplexTree()
        st.insert(Simplex((0,)), 0.0)
        st.insert(Simplex((1,)), 0.0)
        st.insert(Simplex((0, 1)), 0.5)
        assert Simplex((0, 1)) in st
        assert Simplex((0,)) in st
        assert Simplex((1,)) in st
        assert Simplex((0, 2)) not in st

    def test_filtration_value(self):
        st = SimplexTree()
        st.insert(Simplex((0,)), 0.0)
        st.insert(Simplex((1,)), 0.0)
        st.insert(Simplex((0, 1)), 0.5)
        assert st.filtration_value(Simplex((0,))) == 0.0
        assert st.filtration_value(Simplex((0, 1))) == 0.5

    def test_filtration_min_update(self):
        """Re-inserting with lower filtration should update to the minimum."""
        st = SimplexTree()
        st.insert(Simplex((0, 1)), 5.0)
        st.insert(Simplex((0,)), 0.0)
        assert st.filtration_value(Simplex((0,))) == 0.0

    def test_num_simplices(self):
        st = SimplexTree()
        st.insert(Simplex((0, 1)), 0.5)
        st.insert(Simplex((1, 2)), 0.8)
        assert st.num_simplices() == 4  # vertices 0,1,2 + edges 01,12

    def test_dimension(self):
        st = SimplexTree()
        st.insert(Simplex((0, 1, 2)), 1.0)
        assert st.dimension() == 2

    def test_max_dimension_limit(self):
        st = SimplexTree(max_dimension=1)
        result = st.insert(Simplex((0, 1, 2)), 1.0)
        assert result is False
        assert st.num_simplices() == 0

    def test_iteration(self):
        st = SimplexTree()
        for v in range(3):
            st.insert(Simplex((v,)), 0.0)
        st.insert(Simplex((0, 1)), 0.5)
        st.insert(Simplex((1, 2)), 0.8)
        simplices = list(st)
        assert Simplex((0,)) in simplices
        assert Simplex((1,)) in simplices
        assert Simplex((2,)) in simplices
        assert Simplex((0, 1)) in simplices
        assert Simplex((1, 2)) in simplices

    def test_unique_ids(self):
        """Each simplex should get a unique ID."""
        st = SimplexTree()
        st.insert(Simplex((0, 1)), 0.5)
        st.insert(Simplex((1, 2)), 0.8)
        ids = st.all_simplex_ids()
        id_values = list(ids.values())
        assert len(id_values) == len(set(id_values)), "IDs should be unique"
        assert len(ids) == st.num_simplices()


# ---------------------------------------------------------------------------
# Vietoris-Rips tests
# ---------------------------------------------------------------------------

class TestVietorisRips:
    def test_single_point(self):
        vr = VietorisRipsComplex([(0, 0)], max_scale=1.0, max_dimension=1)
        tree = vr.build()
        assert tree.num_simplices() == 1
        assert tree.dimension() == 0

    def test_two_points(self):
        vr = VietorisRipsComplex([(0, 0), (1, 0)], max_scale=1.0, max_dimension=1)
        tree = vr.build()
        assert tree.num_simplices() == 3  # 2 vertices + 1 edge
        assert Simplex((0, 1)) in tree

    def test_two_points_too_far(self):
        vr = VietorisRipsComplex([(0, 0), (2, 0)], max_scale=1.0, max_dimension=1)
        tree = vr.build()
        assert tree.num_simplices() == 2  # only vertices
        assert Simplex((0, 1)) not in tree

    def test_empty_point_cloud_raises(self):
        with pytest.raises(ValueError):
            VietorisRipsComplex([], max_scale=1.0)

    def test_triangle_homology(self):
        """A filled triangle should have H0=1 essential, no H1."""
        pts = [(0, 0), (1, 0), (0.5, 0.866)]
        vr = VietorisRipsComplex(pts, max_scale=2.0, max_dimension=2)
        tree = vr.build()
        persistence = compute_persistence(tree, max_dimension=2, min_persistence=0.01)
        h0 = persistence.get(0, [])
        essential_h0 = [p for p in h0 if p[1] == float('inf')]
        assert len(essential_h0) == 1, "Should have exactly 1 essential H0"
        h1 = persistence.get(1, [])
        real_h1 = [p for p in h1 if p[1] - p[0] > 0.01]
        assert len(real_h1) == 0, "Filled triangle should have no H1"

    def test_circle_homology(self):
        """8 points on a circle should have H0=1 essential, H1=1 essential."""
        pts = [(math.cos(2 * math.pi * i / 8), math.sin(2 * math.pi * i / 8))
               for i in range(8)]
        vr = VietorisRipsComplex(pts, max_scale=1.0, max_dimension=1)
        tree = vr.build()
        persistence = compute_persistence(tree, max_dimension=1)
        h0 = persistence.get(0, [])
        essential_h0 = [p for p in h0 if p[1] == float('inf')]
        assert len(essential_h0) == 1
        h1 = persistence.get(1, [])
        essential_h1 = [p for p in h1 if p[1] == float('inf')]
        assert len(essential_h1) == 1

    def test_custom_metric(self):
        """Test with Manhattan distance."""
        vr = VietorisRipsComplex(
            [(0, 0), (1, 1)], max_scale=2.0, max_dimension=1,
            metric=lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1]),
        )
        tree = vr.build()
        assert Simplex((0, 1)) in tree
        assert tree.filtration_value(Simplex((0, 1))) == 2.0


# ---------------------------------------------------------------------------
# Weighted Rips tests
# ---------------------------------------------------------------------------

class TestWeightedRips:
    def test_weights_length_mismatch(self):
        with pytest.raises(ValueError):
            WeightedRipsComplex([(0, 0), (1, 0)], [0.0], max_scale=1.0)

    def test_negative_weights(self):
        with pytest.raises(ValueError):
            WeightedRipsComplex([(0, 0)], [-1.0], max_scale=1.0)

    def test_vertex_filtration(self):
        pts = [(0, 0), (1, 0), (2, 0)]
        w = [0.0, 0.5, 1.0]
        wr = WeightedRipsComplex(pts, w, max_scale=3.0, max_dimension=1)
        tree = wr.build()
        assert tree.filtration_value(Simplex((0,))) == 0.0
        assert tree.filtration_value(Simplex((1,))) == 0.5
        assert tree.filtration_value(Simplex((2,))) == 1.0


# ---------------------------------------------------------------------------
# Cech complex tests
# ---------------------------------------------------------------------------

class TestCechComplex:
    def test_basic(self):
        pts = [(0, 0), (1, 0), (0.5, 0.866)]
        cech = CechComplex(pts, epsilon=0.6, max_dimension=2)
        tree = cech.build()
        assert Simplex((0, 1)) in tree
        assert Simplex((0, 1, 2)) in tree  # circumradius ≈ 0.577

    def test_negative_epsilon(self):
        with pytest.raises(ValueError):
            CechComplex([(0, 0)], epsilon=-1.0)

    def test_circumradius_degenerate(self):
        r = _circumradius_3pts([(0, 0), (1, 0), (2, 0)])
        assert r == pytest.approx(1.0)

    def test_circumradius_equilateral(self):
        r = _circumradius_3pts([(0, 0), (1, 0), (0.5, 0.866)])
        assert r == pytest.approx(0.577, abs=0.01)


# ---------------------------------------------------------------------------
# Sublevel filtration tests
# ---------------------------------------------------------------------------

class TestSublevelFiltration:
    def test_1d(self):
        sf = SublevelFiltration([0, 3, 1], max_dimension=1)
        tree = sf.build()
        assert tree.num_simplices() == 5  # 3 vertices + 2 edges

    def test_2d(self):
        sf = SublevelFiltration([[0, 1], [2, 3]], max_dimension=2)
        tree = sf.build()
        assert tree.num_simplices() >= 6

    def test_empty_grid(self):
        with pytest.raises(ValueError):
            SublevelFiltration([])

    def test_non_rectangular(self):
        with pytest.raises(ValueError):
            SublevelFiltration([[0, 1], [2]])

    def test_single_element(self):
        sf = SublevelFiltration([5], max_dimension=1)
        tree = sf.build()
        persistence = compute_persistence(tree)
        assert len(persistence.get(0, [])) == 1


# ---------------------------------------------------------------------------
# Persistence computation tests
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_empty_tree_raises(self):
        st = SimplexTree()
        with pytest.raises(ValueError, match="empty"):
            compute_persistence(st)

    def test_min_persistence_filter(self):
        pts = [(0, 0), (1, 0), (0.5, 0.866)]
        vr = VietorisRipsComplex(pts, max_scale=2.0, max_dimension=2)
        tree = vr.build()
        all_persist = compute_persistence(tree, max_dimension=2)
        filtered = compute_persistence(tree, max_dimension=2, min_persistence=0.01)
        total_all = sum(len(v) for v in all_persist.values())
        total_filtered = sum(len(v) for v in filtered.values())
        assert total_filtered <= total_all

    def test_two_disconnected_points(self):
        pts = [(0, 0), (10, 0)]
        vr = VietorisRipsComplex(pts, max_scale=1.0, max_dimension=0)
        tree = vr.build()
        persistence = compute_persistence(tree, max_dimension=0)
        h0 = persistence.get(0, [])
        essential = [p for p in h0 if p[1] == float('inf')]
        assert len(essential) == 2  # Two disconnected components


# ---------------------------------------------------------------------------
# PersistenceDiagram tests
# ---------------------------------------------------------------------------

class TestPersistenceDiagram:
    def test_basic(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        assert d.num_features == 1
        assert d.num_essential == 0

    def test_essential(self):
        d = PersistenceDiagram(1)
        d.add(0.0, float('inf'))
        assert d.num_essential == 1
        assert d.pairs[0].is_essential

    def test_invalid_pair(self):
        with pytest.raises(ValueError):
            PersistencePair(1.0, 0.5, 0)  # death < birth

    def test_betti_number(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        d.add(0.5, 2.0)
        assert d.betti_number(0.0) == 1  # only first is alive at t=0
        assert d.betti_number(0.5) == 2  # both alive
        assert d.betti_number(1.0) == 1  # first dies at 1.0
        assert d.betti_number(2.0) == 0  # both dead

    def test_betti_number_essential(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        d.add(0.0, float('inf'))
        assert d.betti_number(0.5) == 2
        assert d.betti_number(1.5) == 1  # essential still alive
        assert d.betti_number(100) == 1

    def test_max_persistence(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        d.add(0.0, 2.0)
        d.add(0.0, float('inf'))
        assert d.max_persistence == float('inf')

    def test_max_persistence_finite_only(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        d.add(0.0, 2.0)
        assert d.max_persistence == 2.0

    def test_empty_diagram(self):
        d = PersistenceDiagram(0)
        assert d.num_features == 0
        assert d.max_persistence == 0.0

    def test_serialization(self):
        d = PersistenceDiagram(1)
        d.add(0.0, 1.0)
        d.add(0.5, float('inf'))
        s = diagrams_to_json({1: d})
        loaded = diagrams_from_json(s)
        assert loaded[1].num_features == 2
        assert loaded[1].pairs[0].birth == 0.0
        assert loaded[1].pairs[0].death == 1.0
        assert loaded[1].pairs[1].death == float('inf')

    def test_barcode_string(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        d.add(0.0, float('inf'))
        s = barcode_string({0: d})
        assert "H0" in s
        assert "∞" in s


# ---------------------------------------------------------------------------
# Distance tests
# ---------------------------------------------------------------------------

class TestBottleneckDistance:
    def test_identical_diagrams(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        d.add(0.0, 2.0)
        assert bottleneck_distance(d, d) == pytest.approx(0.0)

    def test_small_difference(self):
        d1 = PersistenceDiagram(0)
        d1.add(0.0, 1.0)
        d2 = PersistenceDiagram(0)
        d2.add(0.0, 1.1)
        assert bottleneck_distance(d1, d2) == pytest.approx(0.1)

    def test_both_empty(self):
        d1 = PersistenceDiagram(0)
        d2 = PersistenceDiagram(0)
        assert bottleneck_distance(d1, d2) == 0.0

    def test_one_empty(self):
        d1 = PersistenceDiagram(0)
        d2 = PersistenceDiagram(0)
        d2.add(0.0, 1.0)
        d = bottleneck_distance(d1, d2)
        assert d == pytest.approx(0.5)  # distance to diagonal = (1-0)/2

    def test_dimension_mismatch(self):
        d1 = PersistenceDiagram(0)
        d2 = PersistenceDiagram(1)
        with pytest.raises(ValueError):
            bottleneck_distance(d1, d2)

    def test_with_essential(self):
        d1 = PersistenceDiagram(0)
        d1.add(0.0, 1.0)
        d1.add(0.0, float('inf'))
        d2 = PersistenceDiagram(0)
        d2.add(0.0, 1.0)
        d2.add(0.0, float('inf'))
        assert bottleneck_distance(d1, d2) == pytest.approx(0.0)


class TestWassersteinDistance:
    def test_identical(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        d.add(0.0, 2.0)
        assert wasserstein_distance(d, d, p=2.0) == pytest.approx(0.0)

    def test_w2(self):
        d1 = PersistenceDiagram(0)
        d1.add(0.0, 1.0)
        d2 = PersistenceDiagram(0)
        d2.add(0.0, 1.5)
        # W2 with n1+n2 augmentation: optimal matching is (0,1)->(0,1.5)
        # and diag->diag, total = 0.5^2 + 0.25^2 = 0.3125, W2 = sqrt(0.3125)
        assert wasserstein_distance(d1, d2, p=2.0) == pytest.approx(0.559, abs=0.01)

    def test_w1(self):
        d1 = PersistenceDiagram(0)
        d1.add(0.0, 1.0)
        d2 = PersistenceDiagram(0)
        d2.add(0.0, 1.5)
        # W1: 0.5 + 0.25 = 0.75
        assert wasserstein_distance(d1, d2, p=1.0) == pytest.approx(0.75, abs=0.01)

    def test_p_less_than_1_raises(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        with pytest.raises(ValueError):
            wasserstein_distance(d, d, p=0.5)

    def test_both_empty(self):
        d1 = PersistenceDiagram(0)
        d2 = PersistenceDiagram(0)
        assert wasserstein_distance(d1, d2) == 0.0

    def test_p_inf_equals_bottleneck(self):
        """Wasserstein with p=inf should equal bottleneck distance."""
        d1 = PersistenceDiagram(0)
        d1.add(0.0, 1.0)
        d1.add(0.0, 2.0)
        d2 = PersistenceDiagram(0)
        d2.add(0.0, 1.5)
        d2.add(0.0, 2.5)
        w_inf = wasserstein_distance(d1, d2, p=float('inf'))
        bn = bottleneck_distance(d1, d2)
        assert w_inf == pytest.approx(bn)


class TestHausdorffDistance:
    def test_identical(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        assert hausdorff_distance(d, d) == pytest.approx(0.0)

    def test_dimension_mismatch(self):
        d1 = PersistenceDiagram(0)
        d2 = PersistenceDiagram(1)
        with pytest.raises(ValueError):
            hausdorff_distance(d1, d2)


# ---------------------------------------------------------------------------
# Curves and landscapes tests
# ---------------------------------------------------------------------------

class TestBettiCurve:
    def test_basic(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        d.add(0.0, 2.0)
        curves = betti_curve({0: d}, resolution=10, t_max=2.0)
        curve = curves[0]
        # At t=0, both alive
        assert curve[0][1] == 2
        # At t=2, both dead
        assert curve[-1][1] == 0


class TestPersistenceLandscape:
    def test_basic(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 2.0)
        landscapes = persistence_landscape(d, resolution=100, max_functions=1)
        # The tent function peaks at t=1 with value 1.0.
        vals = [v for _, v in landscapes[0]]
        assert max(vals) == pytest.approx(1.0, abs=0.05)

    def test_empty_diagram(self):
        d = PersistenceDiagram(0)
        landscapes = persistence_landscape(d, resolution=10, max_functions=2)
        assert len(landscapes) == 2
        for landscape in landscapes:
            assert all(v == 0.0 for _, v in landscape)

    def test_essential_only(self):
        d = PersistenceDiagram(0)
        d.add(0.0, float('inf'))
        landscapes = persistence_landscape(d, resolution=10, max_functions=1)
        for landscape in landscapes:
            assert all(v == 0.0 for _, v in landscape)

    def test_landscape_norm(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 2.0)
        landscapes = persistence_landscape(d, resolution=200, max_functions=1)
        # Sup norm should be close to 1.0 (tent peak height).
        sup = landscape_norm(landscapes[0], p=0)
        assert sup == pytest.approx(1.0, abs=0.05)
        # L2 norm should be positive.
        l2 = landscape_norm(landscapes[0], p=2)
        assert l2 > 0


# ---------------------------------------------------------------------------
# Persistence images tests
# ---------------------------------------------------------------------------

class TestPersistenceImage:
    def test_basic(self):
        d = PersistenceDiagram(1)
        d.add(0.0, 2.0)
        d.add(1.0, 3.0)
        img, b_range, p_range = persistence_image(d, resolution=20, sigma=0.5)
        assert len(img) == 20
        assert len(img[0]) == 20
        assert any(any(row) for row in img)  # Not all zeros

    def test_empty_diagram(self):
        d = PersistenceDiagram(0)
        img, _, _ = persistence_image(d, resolution=10)
        assert all(all(v == 0.0 for v in row) for row in img)

    def test_essential_only(self):
        d = PersistenceDiagram(0)
        d.add(0.0, float('inf'))
        img, _, _ = persistence_image(d, resolution=10)
        assert all(all(v == 0.0 for v in row) for row in img)

    def test_image_to_ascii(self):
        img = [[0, 0.5, 1.0], [0.5, 1.0, 0.5], [0, 0.5, 0]]
        s = image_to_ascii(img, width=10)
        assert len(s) > 0


# ---------------------------------------------------------------------------
# Plot tests
# ---------------------------------------------------------------------------

class TestPlot:
    def test_basic_plot(self):
        diagrams = {0: PersistenceDiagram(0)}
        diagrams[0].add(0.0, 1.0)
        diagrams[0].add(0.5, 2.0)
        s = plot_diagram_ascii(diagrams, width=30, height=10)
        assert len(s) > 0
        assert "Legend" in s

    def test_empty_diagrams(self):
        s = plot_diagram_ascii({0: PersistenceDiagram(0)})
        assert "empty" in s.lower()


# ---------------------------------------------------------------------------
# I/O tests
# ---------------------------------------------------------------------------

class TestIO:
    def test_roundtrip(self, tmp_path):
        d = PersistenceDiagram(1)
        d.add(0.0, 1.0)
        d.add(0.5, float('inf'))
        path = str(tmp_path / "test.json")
        save_diagrams({1: d}, path)
        loaded = load_diagrams(path)
        assert loaded[1].num_features == 2
        assert loaded[1].pairs[1].death == float('inf')


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------

class TestCLI:
    def test_compute_summary(self, tmp_path):
        import json
        pts = [[0, 0], [1, 0], [0.5, 0.866]]
        path = str(tmp_path / "pts.json")
        with open(path, "w") as f:
            json.dump(pts, f)
        from tda.cli import main
        assert main(["compute", path, "--max-scale", "2.0", "-d", "2",
                      "--format", "summary"]) == 0

    def test_compute_barcode(self, tmp_path):
        import json
        pts = [[0, 0], [1, 0], [0.5, 0.866]]
        path = str(tmp_path / "pts.json")
        with open(path, "w") as f:
            json.dump(pts, f)
        from tda.cli import main
        assert main(["compute", path, "--max-scale", "2.0", "-d", "2",
                      "--format", "barcode"]) == 0

    def test_compute_output(self, tmp_path):
        import json
        pts = [[0, 0], [1, 0], [0.5, 0.866]]
        pts_path = str(tmp_path / "pts.json")
        out_path = str(tmp_path / "out.json")
        with open(pts_path, "w") as f:
            json.dump(pts, f)
        from tda.cli import main
        assert main(["compute", pts_path, "--max-scale", "2.0", "-d", "2",
                      "--output", out_path]) == 0
        import os
        assert os.path.exists(out_path)

    def test_info(self, tmp_path):
        import json
        data = {"diagrams": [{"dimension": 0, "pairs": [{"birth": 0.0, "death": 1.0, "persistence": 1.0}]}]}
        path = str(tmp_path / "diag.json")
        with open(path, "w") as f:
            json.dump(data, f)
        from tda.cli import main
        assert main(["info", path]) == 0

    def test_distance(self, tmp_path):
        import json
        data = {"diagrams": [{"dimension": 0, "pairs": [{"birth": 0.0, "death": 1.0, "persistence": 1.0}]}]}
        p1 = str(tmp_path / "d1.json")
        p2 = str(tmp_path / "d2.json")
        for p in [p1, p2]:
            with open(p, "w") as f:
                json.dump(data, f)
        from tda.cli import main
        assert main(["distance", p1, p2, "--metric", "bottleneck"]) == 0

    def test_compare(self, tmp_path):
        import json
        data = {"diagrams": [{"dimension": 0, "pairs": [{"birth": 0.0, "death": 1.0, "persistence": 1.0}]}]}
        p1 = str(tmp_path / "d1.json")
        p2 = str(tmp_path / "d2.json")
        for p in [p1, p2]:
            with open(p, "w") as f:
                json.dump(data, f)
        from tda.cli import main
        assert main(["compare", p1, p2]) == 0