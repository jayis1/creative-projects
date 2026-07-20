#!/usr/bin/env python3
"""Comprehensive pytest test suite for the TSP solver.

Run with::

    pytest test_suite.py -v
    pytest test_suite.py -v -k "held_karp or two_opt"

Tests cover:
- Instance creation, validation, generation, TSPLIB I/O
- Tour representation and operations
- All 18 algorithms: validity, non-worsening, correctness
- Solver dispatcher
- BenchmarkSuite
- Visualization
- Config loading
- Edge cases (n=2, n=3, single city error)
"""
from __future__ import annotations

import os
import sys
import json
import math
import tempfile

import numpy as np
import pytest

# Ensure we import from the local package
sys.path.insert(0, os.path.dirname(__file__))

from tsp_solver.instance import TSPInstance, generate_instance, load_tsplib, save_tsplib
from tsp_solver.tour import Tour
from tsp_solver.solver import solve, list_algorithms, list_algorithms_by_category, algorithm_category
from tsp_solver.exact import held_karp, branch_and_bound
from tsp_solver.heuristics import nearest_neighbor, nearest_neighbor_multistart, nearest_insertion, farthest_insertion, greedy
from tsp_solver.local_search import two_opt, three_opt, or_opt
from tsp_solver.metaheuristics import simulated_annealing, genetic_algorithm, ant_colony
from tsp_solver.approximation import mst_approx, christofides
from tsp_solver.advanced import savings, iterated_local_search, lin_kernighan, double_bridge
from tsp_solver.benchmark import BenchmarkSuite, BenchmarkResult
from tsp_solver.viz import ascii_plot, tour_to_json
from tsp_solver.config import SolverConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def small_inst():
    return generate_instance(10, seed=42)

@pytest.fixture
def tiny_inst():
    return generate_instance(5, seed=42)

@pytest.fixture
def exact_inst():
    """Instance small enough for exact solvers."""
    return generate_instance(8, seed=42)


# ---------------------------------------------------------------------------
# Instance tests
# ---------------------------------------------------------------------------

class TestInstance:
    def test_from_coords(self):
        inst = TSPInstance(coords=[[0, 0], [3, 4]])
        assert inst.n == 2
        assert inst.distance(0, 1) == 5.0

    def test_from_matrix(self):
        inst = TSPInstance(matrix=[[0, 10, 15], [10, 0, 20], [15, 20, 0]])
        assert inst.n == 3
        assert inst.distance(0, 1) == 10.0

    def test_requires_coords_or_matrix(self):
        with pytest.raises(ValueError, match="Either coords or matrix"):
            TSPInstance()

    def test_bad_coords_shape(self):
        with pytest.raises(ValueError, match="coords must be"):
            TSPInstance(coords=[[1, 2, 3]])

    def test_non_square_matrix(self):
        with pytest.raises(ValueError, match="matrix must be square"):
            TSPInstance(matrix=[[0, 1], [1, 0], [0, 1]])

    def test_negative_distance(self):
        with pytest.raises(ValueError, match="non-negative"):
            TSPInstance(matrix=[[0, -1], [-1, 0]])

    def test_too_few_cities(self):
        with pytest.raises(ValueError, match="at least 2"):
            TSPInstance(coords=[[0, 0]])

    def test_distance_out_of_range(self):
        inst = TSPInstance(coords=[[0, 0], [1, 1]])
        with pytest.raises(IndexError):
            inst.distance(0, 5)

    def test_tour_length_validation(self):
        inst = generate_instance(5, seed=1)
        with pytest.raises(ValueError, match="Tour length"):
            inst.tour_length([0, 1, 2])

    def test_tour_length_not_permutation(self):
        inst = generate_instance(5, seed=1)
        with pytest.raises(ValueError, match="not a valid permutation"):
            inst.tour_length([0, 1, 2, 2, 4])

    def test_symmetric_matrix(self):
        inst = TSPInstance(matrix=[[0, 10, 20], [12, 0, 15], [18, 22, 0]])
        # Should be symmetrized: (10+12)/2 = 11, (20+18)/2 = 19, (15+22)/2 = 18.5
        assert inst.distance(0, 1) == 11.0
        assert inst.distance(0, 2) == 19.0
        assert inst.distance(1, 2) == 18.5

    def test_nearest(self):
        inst = TSPInstance(coords=[[0, 0], [1, 0], [5, 0]])
        assert inst.nearest(0) == 1
        assert inst.nearest(0, [2]) == 2

    def test_repr(self):
        inst = TSPInstance(coords=[[0, 0], [1, 1]], name="test")
        assert "TSPInstance" in repr(inst)
        assert "test" in repr(inst)


class TestGenerateInstance:
    def test_basic(self):
        inst = generate_instance(20, seed=42)
        assert inst.n == 20

    def test_seed_reproducibility(self):
        a = generate_instance(10, seed=42)
        b = generate_instance(10, seed=42)
        assert np.array_equal(a.matrix, b.matrix)

    def test_different_seeds_differ(self):
        a = generate_instance(10, seed=1)
        b = generate_instance(10, seed=2)
        assert not np.array_equal(a.matrix, b.matrix)

    def test_n_too_small(self):
        with pytest.raises(ValueError):
            generate_instance(1)

    def test_cluster_distribution(self):
        inst = generate_instance(30, seed=42, distribution="cluster")
        assert inst.n == 30

    def test_bad_distribution(self):
        with pytest.raises(ValueError):
            generate_instance(10, distribution="bad")


class TestTSPLIB:
    def test_save_and_load_coords(self, tmp_path):
        inst = generate_instance(10, seed=42, name="test_inst")
        path = tmp_path / "test.tsp"
        save_tsplib(inst, str(path))
        loaded = load_tsplib(str(path))
        assert loaded.n == inst.n
        assert np.allclose(loaded.matrix, inst.matrix)

    def test_load_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_tsplib("/nonexistent/path.tsp")

    def test_load_empty_file(self, tmp_path):
        path = tmp_path / "empty.tsp"
        path.write_text("NAME : empty\nEOF\n")
        with pytest.raises(ValueError, match="No coordinates"):
            load_tsplib(str(path))

    def test_load_edge_weight_section(self, tmp_path):
        path = tmp_path / "matrix.tsp"
        path.write_text(
            "NAME : matrix_test\n"
            "TYPE : TSP\n"
            "DIMENSION : 3\n"
            "EDGE_WEIGHT_TYPE : EXPLICIT\n"
            "EDGE_WEIGHT_FORMAT : FULL_MATRIX\n"
            "EDGE_WEIGHT_SECTION\n"
            "0 10 15\n"
            "10 0 20\n"
            "15 20 0\n"
            "EOF\n"
        )
        inst = load_tsplib(str(path))
        assert inst.n == 3
        assert inst.distance(0, 1) == 10.0


# ---------------------------------------------------------------------------
# Tour tests
# ---------------------------------------------------------------------------

class TestTour:
    def test_basic(self):
        t = Tour([0, 1, 2, 3], 10.0)
        assert t.order == (0, 1, 2, 3)
        assert t.length == 10.0
        assert t.n == 4
        assert len(t) == 4

    def test_compute_length(self):
        inst = TSPInstance(coords=[[0, 0], [3, 4]])
        t = Tour([0, 1], distances=inst.distance)
        assert t.length == 10.0  # 3+4+3+4 = 10 roundtrip

    def test_requires_length_or_distances(self):
        with pytest.raises(ValueError, match="length or distances"):
            Tour([0, 1])

    def test_edges(self):
        t = Tour([0, 1, 2], 6.0)
        edges = list(t.edges())
        assert edges == [(0, 1), (1, 2), (2, 0)]

    def test_reversed(self):
        t = Tour([0, 1, 2, 3], 10.0)
        r = t.reversed()
        assert r.order == (3, 2, 1, 0)
        assert r.length == 10.0

    def test_rotated(self):
        t = Tour([0, 1, 2, 3], 10.0)
        r = t.rotated(2)
        assert r.order == (2, 3, 0, 1)

    def test_equality(self):
        t1 = Tour([0, 1, 2], 6.0)
        t2 = Tour([0, 1, 2], 6.0)
        assert t1 == t2
        assert t1 != 42  # type: ignore[comparison-overlap]

    def test_immutable(self):
        t = Tour([0, 1, 2], 6.0)
        with pytest.raises(AttributeError):
            t.order = (3, 2, 1)  # type: ignore[misc]

    def test_to_list(self):
        t = Tour([0, 1, 2], 6.0)
        assert t.to_list() == [0, 1, 2]


# ---------------------------------------------------------------------------
# Algorithm validity tests
# ---------------------------------------------------------------------------

ALL_ALGOS = list_algorithms()


def is_valid_tour(tour: Tour, n: int) -> bool:
    """Check that tour is a valid permutation of [0, n-1]."""
    return sorted(tour.order) == list(range(n))


class TestAlgorithmValidity:
    @pytest.mark.parametrize("algo", ALL_ALGOS)
    def test_produces_valid_permutation(self, algo, small_inst):
        """Every algorithm must produce a valid permutation."""
        kwargs = {}
        if algo in ("simulated_annealing", "genetic_algorithm", "ant_colony",
                    "iterated_local_search", "lin_kernighan",
                    "nearest_neighbor_multistart"):
            kwargs["seed"] = 42
        # Cap iterations for speed
        if algo == "simulated_annealing":
            kwargs["max_iter"] = 5000
        if algo == "genetic_algorithm":
            kwargs["generations"] = 50
            kwargs["population_size"] = 30
        if algo == "ant_colony":
            kwargs["n_iterations"] = 30
            kwargs["n_ants"] = 20
        if algo == "iterated_local_search":
            kwargs["max_iter"] = 50
        if algo == "lin_kernighan":
            kwargs["max_iter"] = 200
        tour = solve(small_inst, algo, **kwargs)
        assert is_valid_tour(tour, small_inst.n), f"{algo}: {tour.order}"

    @pytest.mark.parametrize("algo", ALL_ALGOS)
    def test_positive_length(self, algo, small_inst):
        """Every algorithm must produce a positive-length tour."""
        kwargs = {"seed": 42} if algo in (
            "simulated_annealing", "genetic_algorithm", "ant_colony",
            "iterated_local_search", "lin_kernighan",
            "nearest_neighbor_multistart",
        ) else {}
        if algo == "simulated_annealing":
            kwargs["max_iter"] = 5000
        if algo == "genetic_algorithm":
            kwargs["generations"] = 50
            kwargs["population_size"] = 30
        if algo == "ant_colony":
            kwargs["n_iterations"] = 30
            kwargs["n_ants"] = 20
        if algo == "iterated_local_search":
            kwargs["max_iter"] = 50
        if algo == "lin_kernighan":
            kwargs["max_iter"] = 200
        tour = solve(small_inst, algo, **kwargs)
        assert tour.length > 0


class TestExactAlgorithms:
    def test_held_karp_optimal(self, exact_inst):
        tour = held_karp(exact_inst)
        assert is_valid_tour(tour, exact_inst.n)
        # Compare with brute force
        import itertools
        n = exact_inst.n
        best = math.inf
        for perm in itertools.permutations(range(1, n)):
            order = [0] + list(perm)
            cost = exact_inst.tour_length(order)
            best = min(best, cost)
        assert abs(tour.length - best) < 1e-6

    def test_held_karp_too_large(self):
        inst = generate_instance(25, seed=1)
        with pytest.raises(ValueError, match="infeasible"):
            held_karp(inst)

    def test_branch_and_bound_optimal(self, exact_inst):
        tour = branch_and_bound(exact_inst)
        hk = held_karp(exact_inst)
        assert is_valid_tour(tour, exact_inst.n)
        assert abs(tour.length - hk.length) < 1e-6

    def test_bb_matches_hk_multiple_seeds(self):
        for seed in range(10):
            inst = generate_instance(8, seed=seed)
            hk = held_karp(inst)
            bb = branch_and_bound(inst)
            assert abs(hk.length - bb.length) < 1e-6, f"seed={seed}: HK={hk.length}, B&B={bb.length}"


class TestLocalSearchNonWorsening:
    def test_two_opt_does_not_worsen(self, small_inst):
        nn = nearest_neighbor(small_inst)
        improved = two_opt(small_inst, nn, max_iter=1000)
        assert improved.length <= nn.length + 1e-6

    def test_three_opt_does_not_worsen(self, small_inst):
        nn = nearest_neighbor(small_inst)
        improved = three_opt(small_inst, nn, max_iter=500)
        assert improved.length <= nn.length + 1e-6

    def test_or_opt_does_not_worsen(self, small_inst):
        nn = nearest_neighbor(small_inst)
        improved = or_opt(small_inst, nn, max_iter=1000)
        assert improved.length <= nn.length + 1e-6

    @pytest.mark.parametrize("seed", range(5))
    def test_two_opt_validity(self, seed):
        inst = generate_instance(10, seed=seed)
        t = two_opt(inst, max_iter=200)
        assert is_valid_tour(t, inst.n)

    @pytest.mark.parametrize("seed", range(5))
    def test_or_opt_validity(self, seed):
        inst = generate_instance(10, seed=seed)
        t = or_opt(inst, max_iter=200)
        assert is_valid_tour(t, inst.n)


class TestAdvancedAlgorithms:
    def test_savings_valid(self, small_inst):
        t = savings(small_inst)
        assert is_valid_tour(t, small_inst.n)
        assert t.length > 0

    def test_savings_does_not_exceed_2x_optimal(self, exact_inst):
        t = savings(exact_inst)
        opt = held_karp(exact_inst)
        assert t.length <= 2 * opt.length  # savings heuristic shouldn't be terrible

    def test_iterated_local_search_valid(self, small_inst):
        t = iterated_local_search(small_inst, seed=42, max_iter=50)
        assert is_valid_tour(t, small_inst.n)
        assert t.length > 0

    def test_ils_does_not_worsen(self, small_inst):
        nn = nearest_neighbor(small_inst)
        t = iterated_local_search(small_inst, nn, seed=42, max_iter=50)
        assert t.length <= nn.length + 1e-6

    def test_lin_kernighan_valid(self, small_inst):
        t = lin_kernighan(small_inst, seed=42, max_iter=200)
        assert is_valid_tour(t, small_inst.n)
        assert t.length > 0

    def test_lin_kernighan_does_not_worsen(self, small_inst):
        nn = nearest_neighbor(small_inst)
        t = lin_kernighan(small_inst, nn, max_iter=200)
        assert t.length <= nn.length + 1e-6

    def test_double_bridge_preserves_elements(self):
        import random
        rng = random.Random(42)
        order = list(range(20))
        kicked = double_bridge(order, rng)
        assert sorted(kicked) == sorted(order)
        assert kicked != order  # Should be different

    def test_double_bridge_small(self):
        import random
        rng = random.Random(42)
        order = list(range(5))
        kicked = double_bridge(order, rng)
        assert sorted(kicked) == sorted(order)

    def test_ils_bad_local_search(self, small_inst):
        with pytest.raises(ValueError, match="local_search"):
            iterated_local_search(small_inst, local_search="bad")


# ---------------------------------------------------------------------------
# Solver dispatcher tests
# ---------------------------------------------------------------------------

class TestSolver:
    def test_list_algorithms_contains_all(self):
        algos = list_algorithms()
        assert "held_karp" in algos
        assert "christofides" in algos
        assert "savings" in algos
        assert "iterated_local_search" in algos
        assert "lin_kernighan" in algos
        assert len(algos) == 18

    def test_unknown_algorithm(self, small_inst):
        with pytest.raises(ValueError, match="Unknown algorithm"):
            solve(small_inst, "nonexistent")

    def test_unknown_refiner(self, small_inst):
        with pytest.raises(ValueError, match="Unknown refiner"):
            solve(small_inst, "nearest_neighbor", refine="bad")

    def test_refine_improves(self, small_inst):
        nn = solve(small_inst, "nearest_neighbor")
        refined = solve(small_inst, "nearest_neighbor", refine="two_opt")
        assert refined.length <= nn.length + 1e-6

    def test_category(self):
        assert algorithm_category("held_karp") == "exact"
        assert algorithm_category("christofides") == "approximation"
        assert algorithm_category("two_opt") == "local_search"
        assert algorithm_category("ant_colony") == "metaheuristic"
        assert algorithm_category("nonexistent") is None

    def test_list_by_category(self):
        cats = list_algorithms_by_category()
        assert "exact" in cats
        assert "held_karp" in cats["exact"]
        assert len(cats) == 5


# ---------------------------------------------------------------------------
# Benchmark tests
# ---------------------------------------------------------------------------

class TestBenchmark:
    def test_run_and_summary(self, exact_inst):
        suite = BenchmarkSuite()
        suite.run(exact_inst, algorithms=["nearest_neighbor", "christofides"], seed=42)
        assert len(suite.results) == 2
        summary = suite.summary()
        assert "nearest_neighbor" in summary
        assert "Algorithm" in summary

    def test_best(self, exact_inst):
        suite = BenchmarkSuite()
        suite.run(exact_inst, algorithms=["nearest_neighbor", "held_karp"], seed=42)
        best = suite.best()
        assert best is not None
        # held_karp should be optimal (shortest)
        assert best.length == pytest.approx(min(r.length for r in suite.results))

    def test_to_csv(self, exact_inst, tmp_path):
        suite = BenchmarkSuite()
        suite.run(exact_inst, algorithms=["nearest_neighbor"], seed=42)
        csv_path = tmp_path / "results.csv"
        suite.to_csv(str(csv_path))
        text = csv_path.read_text()
        assert "algorithm" in text
        assert "nearest_neighbor" in text

    def test_to_json(self, exact_inst):
        suite = BenchmarkSuite()
        suite.run(exact_inst, algorithms=["nearest_neighbor"], seed=42)
        data = suite.to_json()
        parsed = json.loads(data)
        assert len(parsed["results"]) == 1

    def test_to_dict(self, exact_inst):
        suite = BenchmarkSuite()
        suite.run(exact_inst, algorithms=["nearest_neighbor"], seed=42)
        d = suite.to_dict()
        assert "results" in d

    def test_fastest(self, exact_inst):
        suite = BenchmarkSuite()
        suite.run(exact_inst, algorithms=["nearest_neighbor", "greedy"], seed=42)
        fast = suite.fastest()
        assert fast is not None

    def test_clear(self, exact_inst):
        suite = BenchmarkSuite()
        suite.run(exact_inst, algorithms=["nearest_neighbor"], seed=42)
        suite.clear()
        assert len(suite.results) == 0

    def test_run_instances(self):
        instances = [generate_instance(8, seed=s) for s in range(3)]
        suite = BenchmarkSuite()
        suite.run_instances(instances, algorithms=["nearest_neighbor"], seed=42)
        assert len(suite.results) == 3

    def test_error_handling(self):
        inst = generate_instance(25, seed=1)  # too large for held_karp
        suite = BenchmarkSuite()
        suite.run(inst, algorithms=["held_karp"], seed=42)
        # Should record error, not crash
        assert len(suite.results) == 1
        assert suite.results[0].error is not None

    def test_benchmark_result_ratio(self):
        r = BenchmarkResult(algorithm="test", length=120.0, time_s=0.1, optimal_length=100.0)
        assert r.ratio == pytest.approx(1.2)
        assert r.gap_pct == pytest.approx(20.0)

    def test_benchmark_result_no_optimal(self):
        r = BenchmarkResult(algorithm="test", length=100.0, time_s=0.1, optimal_length=None)
        assert r.ratio is None
        assert r.gap_pct is None


# ---------------------------------------------------------------------------
# Visualization tests
# ---------------------------------------------------------------------------

class TestVisualization:
    def test_ascii_plot(self, small_inst):
        tour = solve(small_inst, "nearest_neighbor")
        plot = ascii_plot(small_inst, tour)
        assert "Tour" in plot
        assert "@" in plot  # start marker

    def test_ascii_plot_no_coords(self):
        inst = TSPInstance(matrix=[[0, 10, 15], [10, 0, 20], [15, 20, 0]])
        tour = Tour([0, 1, 2], distances=inst.distance)
        plot = ascii_plot(inst, tour)
        assert "no coordinates" in plot

    def test_tour_to_json(self, small_inst):
        tour = solve(small_inst, "nearest_neighbor")
        data = tour_to_json(small_inst, tour)
        assert "name" in data
        assert "length" in data
        assert "order" in data


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------

class TestConfig:
    def test_defaults(self):
        cfg = SolverConfig()
        assert cfg.algorithm == "nearest_neighbor"
        assert cfg.n == 20
        assert cfg.output == "text"

    def test_from_dict(self):
        cfg = SolverConfig.from_dict({"algorithm": "christofides", "n": 100})
        assert cfg.algorithm == "christofides"
        assert cfg.n == 100

    def test_from_dict_ignores_unknown(self):
        cfg = SolverConfig.from_dict({"algorithm": "held_karp", "unknown_key": 42})
        assert cfg.algorithm == "held_karp"

    def test_to_dict(self):
        cfg = SolverConfig(algorithm="greedy", n=50)
        d = cfg.to_dict()
        assert d["algorithm"] == "greedy"
        assert d["n"] == 50

    def test_save_and_load_json(self, tmp_path):
        cfg = SolverConfig(algorithm="christofides", n=100, seed=42)
        path = tmp_path / "config.json"
        cfg.save(str(path))
        loaded = SolverConfig.from_file(str(path))
        assert loaded.algorithm == "christofides"
        assert loaded.n == 100
        assert loaded.seed == 42

    def test_save_and_load_yaml(self, tmp_path):
        cfg = SolverConfig(algorithm="greedy", n=50, seed=1)
        path = tmp_path / "config.yaml"
        cfg.save(str(path))
        loaded = SolverConfig.from_file(str(path))
        assert loaded.algorithm == "greedy"
        assert loaded.n == 50

    def test_load_missing_file(self):
        with pytest.raises(FileNotFoundError):
            SolverConfig.from_file("/nonexistent/config.yaml")

    def test_unsupported_format(self, tmp_path):
        path = tmp_path / "config.txt"
        path.write_text("hello")
        with pytest.raises(ValueError, match="Unsupported config format"):
            SolverConfig.from_file(str(path))


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_n_equals_2(self):
        inst = TSPInstance(coords=[[0, 0], [3, 4]])
        tour = solve(inst, "nearest_neighbor")
        assert is_valid_tour(tour, 2)
        assert abs(tour.length - 10.0) < 0.01  # 2 * 5

    def test_n_equals_2_held_karp(self):
        inst = TSPInstance(coords=[[0, 0], [3, 4]])
        tour = held_karp(inst)
        assert is_valid_tour(tour, 2)

    def test_n_equals_2_christofides(self):
        inst = TSPInstance(coords=[[0, 0], [3, 4]])
        tour = christofides(inst)
        assert is_valid_tour(tour, 2)

    def test_n_equals_3_all_algos(self):
        inst = generate_instance(3, seed=1)
        for algo in ["nearest_neighbor", "greedy", "mst_approx", "christofides",
                      "nearest_insertion", "farthest_insertion", "savings",
                      "two_opt", "or_opt", "three_opt"]:
            tour = solve(inst, algo, seed=42)
            assert is_valid_tour(tour, 3), f"{algo}: {tour.order}"


# ---------------------------------------------------------------------------
# Refinement chain tests
# ---------------------------------------------------------------------------

class TestRefinementChains:
    @pytest.mark.parametrize("refine", ["two_opt", "three_opt", "or_opt"])
    def test_refine_nn(self, small_inst, refine):
        tour = solve(small_inst, "nearest_neighbor", refine=refine)
        nn = solve(small_inst, "nearest_neighbor")
        assert tour.length <= nn.length + 1e-6

    def test_christofides_plus_2opt(self, small_inst):
        tour = solve(small_inst, "christofides", refine="two_opt")
        ch = solve(small_inst, "christofides")
        assert tour.length <= ch.length + 1e-6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])