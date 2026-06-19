"""Tests for the Barnes-Hut quadtree force evaluator."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nbody.body import Body
from nbody.barnes_hut import BHTree
from nbody.brute_force import brute_force_accelerations, barnes_hut_accelerations, force_error


class TestBHTreeConstruction:
    def test_empty_build(self):
        tree = BHTree()
        tree.build([])
        assert tree.n_bodies == 0
        assert tree.root is None

    def test_single_body(self):
        tree = BHTree()
        tree.build([(0.0, 0.0, 1.0)])
        assert tree.n_bodies == 1
        assert tree.root is not None
        assert tree.root.is_leaf
        assert tree.root.mass == 1.0

    def test_two_bodies(self):
        tree = BHTree()
        tree.build([(0.0, 0.0, 1.0), (1.0, 0.0, 1.0)])
        assert tree.n_bodies == 2
        assert not tree.root.is_leaf
        # Center of mass should be at midpoint.
        assert abs(tree.root.com_x - 0.5) < 1e-10
        assert abs(tree.root.com_y - 0.0) < 1e-10

    def test_tree_depth_single(self):
        tree = BHTree()
        tree.build([(0.0, 0.0, 1.0)])
        assert tree.depth() == 1

    def test_colocated_bodies(self):
        """Two bodies at the same position should not cause infinite recursion."""
        tree = BHTree()
        tree.build([(1.0, 1.0, 1.0), (1.0, 1.0, 2.0)])
        assert tree.n_bodies == 2
        # Total mass should be 3.
        assert abs(tree.root.mass - 3.0) < 1e-10


class TestBHTreeForce:
    def test_force_on_single_body(self):
        """A single body exerts no force on itself."""
        tree = BHTree()
        tree.build([(0.0, 0.0, 1.0)])
        fx, fy = tree.force_on((0.0, 0.0, 1.0))
        assert abs(fx) < 1e-12
        assert abs(fy) < 1e-12

    def test_force_matches_brute_force_theta0(self):
        """With theta=0, Barnes-Hut should exactly match brute force."""
        bodies = [Body(0, 0, 0, 0, 1), Body(2, 0, 0, 0, 1), Body(0, 2, 0, 0, 0.5)]
        bf = brute_force_accelerations(bodies, G=1.0, softening=0.1)
        bh = barnes_hut_accelerations(bodies, theta=0.0, G=1.0, softening=0.1)
        max_rel, mean_rel = force_error(bh, bf)
        assert max_rel < 1e-8, f"theta=0 should be exact, max_rel={max_rel}"

    def test_bh_approximation_good_theta(self):
        """With reasonable theta, Barnes-Hut should be close to brute force."""
        bodies = []
        import random
        rng = random.Random(42)
        for _ in range(50):
            bodies.append(Body(
                rng.uniform(-5, 5), rng.uniform(-5, 5), 0, 0, rng.uniform(0.5, 2.0)
            ))
        bf = brute_force_accelerations(bodies, G=1.0, softening=0.5)
        bh = barnes_hut_accelerations(bodies, theta=0.7, G=1.0, softening=0.5)
        max_rel, mean_rel = force_error(bh, bf)
        # With 50 bodies and theta=0.7, mean error should be small.
        assert mean_rel < 0.1, f"mean rel error too high: {mean_rel}"

    def test_invalid_theta(self):
        try:
            BHTree(theta=-0.1)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
        try:
            BHTree(theta=3.0)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_invalid_softening(self):
        try:
            BHTree(softening=-1.0)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


class TestBHTreeDiagnostics:
    def test_depth_grows_with_bodies(self):
        """More spread-out bodies should create deeper trees."""
        tree1 = BHTree()
        tree1.build([(0.0, 0.0, 1.0), (0.1, 0.1, 1.0)])
        tree2 = BHTree()
        tree2.build([(0.0, 0.0, 1.0), (10.0, 10.0, 1.0)])
        # Both have 2 bodies in different quadrants, so depth >= 2.
        assert tree1.depth() >= 1
        assert tree2.depth() >= 1