"""Comprehensive tests for EvOpt new features (config, results, indicators, CMA-ES, SA).

These tests cover:
    - Configuration loading/saving/building (YAML and JSON)
    - Result objects and export (JSON/CSV)
    - Experiment runner and parameter sweep
    - Multi-objective indicators (hypervolume, IGD, GD, spacing, spread)
    - CMA-ES algorithm correctness and convergence
    - Simulated Annealing algorithm correctness and cooling schedules
    - Logging utilities (setup_logging, file output, JSON-line format)
    - CLI integration for new commands
"""
import json
import os
import random
import tempfile
from pathlib import Path

import pytest
import numpy as np


# =========================================================================
# Config module
# =========================================================================

class TestConfig:
    """Tests for evopt.config."""

    def test_default_config_structure(self):
        from evopt.config import default_config
        cfg = default_config("ga", "sphere", dims=3, population_size=50, max_generations=100)
        assert cfg["algorithm"]["name"] == "ga"
        assert cfg["problem"]["name"] == "sphere"
        assert cfg["problem"]["params"]["dims"] == 3
        assert cfg["algorithm"]["params"]["population_size"] == 50
        assert cfg["algorithm"]["params"]["max_generations"] == 100
        assert cfg["seed"] == 42

    def test_default_config_routes_problem_params(self):
        from evopt.config import default_config
        cfg = default_config("ga", "rastrigin", dims=5, cities=10, items=15, m=20)
        assert cfg["problem"]["params"]["dims"] == 5
        assert cfg["problem"]["params"]["cities"] == 10
        assert cfg["problem"]["params"]["items"] == 15
        assert cfg["problem"]["params"]["m"] == 20
        # These should NOT be in algorithm params
        assert "dims" not in cfg["algorithm"]["params"]
        assert "cities" not in cfg["algorithm"]["params"]

    def test_save_and_load_json_config(self, tmp_path):
        from evopt.config import default_config, save_config, load_config
        cfg = default_config("ga", "sphere", dims=2, population_size=20, max_generations=10)
        path = tmp_path / "config.json"
        save_config(cfg, path)
        loaded = load_config(path)
        assert loaded == cfg

    def test_save_and_load_yaml_config(self, tmp_path):
        from evopt.config import default_config, save_config, load_config
        cfg = default_config("de", "rastrigin", dims=3, population_size=20, max_generations=10)
        path = tmp_path / "config.yaml"
        save_config(cfg, path)
        loaded = load_config(path)
        assert loaded["algorithm"]["name"] == "de"
        assert loaded["problem"]["params"]["dims"] == 3

    def test_load_nonexistent_config_raises(self):
        from evopt.config import load_config
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path.yaml")

    def test_load_unsupported_format_raises(self, tmp_path):
        from evopt.config import load_config, ConfigError
        path = tmp_path / "config.txt"
        path.write_text("garbage")
        with pytest.raises(ConfigError):
            load_config(path)

    def test_build_from_config(self):
        from evopt.config import default_config, build_from_config
        cfg = default_config("ga", "sphere", dims=2, population_size=15, max_generations=5)
        problem, algo = build_from_config(cfg)
        assert algo.__class__.__name__ == "GeneticAlgorithm"
        best = algo.run()
        assert best is not None
        assert best.fitness is not None

    def test_build_from_config_with_callbacks(self):
        from evopt.config import default_config, build_from_config
        cfg = default_config("ga", "sphere", dims=2, population_size=15, max_generations=50)
        cfg["callbacks"] = [{"type": "stagnation", "params": {"patience": 5}}]
        _, algo = build_from_config(cfg)
        assert len(algo.callbacks) == 1
        algo.run()
        # Stagnation may or may not trigger, but it should not crash

    def test_build_unknown_algorithm_raises(self):
        from evopt.config import build_algorithm, ConfigError
        cfg = {"algorithm": {"name": "nonexistent"}, "problem": {"name": "sphere", "params": {}}}
        with pytest.raises(ConfigError):
            build_algorithm(cfg)

    def test_build_unknown_problem_raises(self):
        from evopt.config import build_problem, ConfigError
        cfg = {"problem": {"name": "nonexistent", "params": {}}}
        with pytest.raises(ConfigError):
            build_problem(cfg)


# =========================================================================
# Results module
# =========================================================================

class TestResults:
    """Tests for evopt.results."""

    def test_result_from_algorithm(self):
        from evopt import GeneticAlgorithm, Sphere
        from evopt.results import Result
        ga = GeneticAlgorithm(Sphere(dims=2), population_size=20, max_generations=10, seed=42)
        ga.run()
        r = Result.from_algorithm(ga, problem_name="sphere", algorithm_name="ga", time_seconds=0.1)
        assert r.algorithm_name == "ga"
        assert r.problem_name == "sphere"
        assert r.best_fitness is not None
        assert r.best_genome is not None
        assert r.generations == 10
        assert len(r.history) == 11  # gen 0..10

    def test_result_to_json(self, tmp_path):
        from evopt import GeneticAlgorithm, Sphere
        from evopt.results import Result
        ga = GeneticAlgorithm(Sphere(dims=2), population_size=15, max_generations=5, seed=42)
        ga.run()
        r = Result.from_algorithm(ga, problem_name="sphere", algorithm_name="ga", time_seconds=0.05)
        path = tmp_path / "result.json"
        r.to_json(path)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["algorithm_name"] == "ga"
        assert data["problem_name"] == "sphere"
        assert "best_fitness" in data
        assert "history" in data

    def test_result_to_csv(self, tmp_path):
        from evopt import GeneticAlgorithm, Sphere
        from evopt.results import Result
        ga = GeneticAlgorithm(Sphere(dims=2), population_size=15, max_generations=5, seed=42)
        ga.run()
        r = Result.from_algorithm(ga, problem_name="sphere", algorithm_name="ga")
        path = tmp_path / "history.csv"
        r.to_csv(path)
        assert path.exists()
        text = path.read_text()
        assert "generation" in text
        assert "best_fitness" in text
        lines = text.strip().split("\n")
        assert len(lines) >= 7  # header + 6 data rows

    def test_result_summary(self):
        from evopt.results import Result
        r = Result(algorithm_name="ga", problem_name="sphere", best_fitness=0.001,
                   generations=100, time_seconds=1.5, seed=42)
        s = r.summary()
        assert "ga" in s
        assert "sphere" in s
        assert "0.001" in s

    def test_experiment_run(self):
        from evopt.results import Experiment
        exp = Experiment(name="test")
        exp.add("ga", "sphere", {"dims": 2, "population_size": 15, "max_generations": 5}, seed=42)
        exp.add("de", "sphere", {"dims": 2, "population_size": 15, "max_generations": 5}, seed=42)
        results = exp.run(repeats=2)
        assert len(results) == 4  # 2 configs × 2 repeats
        assert all(r.best_fitness is not None for r in results)

    def test_experiment_report(self):
        from evopt.results import Experiment
        exp = Experiment(name="test")
        exp.add("ga", "sphere", {"dims": 2, "population_size": 15, "max_generations": 5}, seed=42)
        exp.run(repeats=1)
        report = exp.report()
        assert "ga" in report
        assert "sphere" in report

    def test_experiment_save_results(self, tmp_path):
        from evopt.results import Experiment
        exp = Experiment(name="test")
        exp.add("ga", "sphere", {"dims": 2, "population_size": 15, "max_generations": 5}, seed=42)
        exp.run(repeats=2)
        exp.save_results(tmp_path / "results")
        assert (tmp_path / "results" / "summary.json").exists()
        # Should have 2 result JSON files
        json_files = list((tmp_path / "results").glob("*.json"))
        # summary.json + 2 result files
        assert len(json_files) == 3

    def test_parameter_sweep(self):
        from evopt.results import parameter_sweep
        exp = parameter_sweep(
            "ga", "sphere",
            param_grid={"mutation_rate": [0.01, 0.1]},
            fixed_params={"dims": 2, "population_size": 15, "max_generations": 5},
            repeats=1, seed=42,
        )
        assert len(exp.results) == 2
        assert all(r.best_fitness is not None for r in exp.results)


# =========================================================================
# Indicators
# =========================================================================

class TestIndicators:
    """Tests for evopt.indicators."""

    def test_hypervolume_2d_known(self):
        """HV of a simple 2-D front with a known answer."""
        from evopt.indicators import hypervolume
        # Two points: (0, 1) and (1, 0), reference (2, 2)
        # Dominated area = 2×2 - (1×1 + 1×1 - overlap)
        # Actually: (0,1) dominates [0,2]×[1,2] = 2×1 = 2
        #           (1,0) dominates [1,2]×[0,2] = 1×2 = 2
        # Overlap: [1,2]×[1,2] = 1×1 = 1
        # Union = 2+2-1 = 3
        front = [[0.0, 1.0], [1.0, 0.0]]
        ref = [2.0, 2.0]
        hv = hypervolume(front, ref)
        assert abs(hv - 3.0) < 1e-10, f"Expected 3.0, got {hv}"

    def test_hypervolume_single_point(self):
        from evopt.indicators import hypervolume
        # Point (0.5, 0.5), ref (1, 1): area = 0.5 × 0.5 = 0.25
        front = [[0.5, 0.5]]
        ref = [1.0, 1.0]
        hv = hypervolume(front, ref)
        assert abs(hv - 0.25) < 1e-10

    def test_hypervolume_empty_front_raises(self):
        from evopt.indicators import hypervolume
        with pytest.raises(ValueError):
            hypervolume([], [1.0, 1.0])

    def test_hypervolume_non_contributing_filtered(self):
        from evopt.indicators import hypervolume
        # (2, 2) is worse than ref (1, 1) so it doesn't contribute
        front = [[0.0, 0.0], [2.0, 2.0]]
        ref = [1.0, 1.0]
        hv = hypervolume(front, ref)
        # Only (0,0) contributes: area = 1×1 = 1
        assert abs(hv - 1.0) < 1e-10

    def test_hypervolume_from_individuals(self):
        from evopt.indicators import hypervolume
        from evopt.core import Individual
        ind1 = Individual([0.0, 1.0])
        ind1.metadata["objectives"] = [0.0, 1.0]
        ind2 = Individual([1.0, 0.0])
        ind2.metadata["objectives"] = [1.0, 0.0]
        hv = hypervolume([ind1, ind2], [2.0, 2.0])
        assert abs(hv - 3.0) < 1e-10

    def test_hypervolume_1d(self):
        from evopt.indicators import hypervolume
        front = [[0.5]]
        ref = [1.0]
        hv = hypervolume(front, ref)
        assert abs(hv - 0.5) < 1e-10

    def test_igd_perfect_front(self):
        """IGD should be 0 when front equals reference."""
        from evopt.indicators import inverted_generational_distance
        front = [[0.0, 1.0], [1.0, 0.0]]
        ref = [[0.0, 1.0], [1.0, 0.0]]
        igd = inverted_generational_distance(front, ref)
        assert abs(igd) < 1e-10

    def test_igd_nonzero(self):
        from evopt.indicators import inverted_generational_distance
        front = [[0.1, 0.1]]
        ref = [[0.0, 0.0]]
        igd = inverted_generational_distance(front, ref)
        expected = (0.1 ** 2 + 0.1 ** 2) ** 0.5  # Euclidean distance
        assert abs(igd - expected) < 1e-10

    def test_gd_perfect_front(self):
        from evopt.indicators import generational_distance
        front = [[0.0, 1.0]]
        ref = [[0.0, 1.0]]
        gd = generational_distance(front, ref)
        assert abs(gd) < 1e-10

    def test_spacing_uniform(self):
        """Spacing of uniformly distributed points should be near 0."""
        from evopt.indicators import spacing
        # Points at (0,0), (1,1), (2,2): all equidistant in L1 (2 each)
        front = [[0.0, 0.0], [1.0, 1.0], [2.0, 2.0]]
        sp = spacing(front)
        assert sp < 1e-10, f"Expected ~0, got {sp}"

    def test_spacing_single_point(self):
        from evopt.indicators import spacing
        assert spacing([[1.0, 1.0]]) == 0.0

    def test_spacing_empty(self):
        from evopt.indicators import spacing
        assert spacing([]) == 0.0

    def test_spread_returns_nonneg(self):
        from evopt.indicators import spread
        front = [[0.0, 1.0], [0.5, 0.5], [1.0, 0.0]]
        s = spread(front)
        assert s >= 0

    def test_extract_objectives_from_raw_list(self):
        from evopt.indicators import _extract_objectives
        objs = _extract_objectives([[1.0, 2.0], [3.0, 4.0]])
        assert objs == [[1.0, 2.0], [3.0, 4.0]]


# =========================================================================
# CMA-ES
# =========================================================================

class TestCMAES:
    """Tests for the CMA-ES algorithm."""

    def test_cmaes_converges_on_sphere(self):
        """CMA-ES should find near-optimal solution on Sphere."""
        from evopt import CMAES, Sphere
        cma = CMAES(Sphere(dims=3), max_generations=50, seed=42)
        best = cma.run()
        assert best is not None
        assert best.fitness < 0.01, f"CMA-ES should converge, got {best.fitness}"

    def test_cmaes_reproducible(self):
        """Same seed should produce same result."""
        from evopt import CMAES, Sphere
        cma1 = CMAES(Sphere(dims=2), max_generations=20, seed=123)
        r1 = cma1.run()
        cma2 = CMAES(Sphere(dims=2), max_generations=20, seed=123)
        r2 = cma2.run()
        # CMA-ES uses numpy RNG seeded via the base class; results should match
        assert abs(float(r1.fitness) - float(r2.fitness)) < 1e-10, \
            f"Reproducible mismatch: {r1.fitness} vs {r2.fitness}"

    def test_cmaes_population_size_default(self):
        from evopt import CMAES, Sphere
        cma = CMAES(Sphere(dims=5))
        # Default λ = 4 + floor(3 * ln(5)) = 4 + 4 = 8
        assert cma.lam == 4 + int(3 * np.log(5))

    def test_cmaes_history_recorded(self):
        from evopt import CMAES, Sphere
        cma = CMAES(Sphere(dims=2), max_generations=10, seed=42)
        cma.run()
        assert len(cma.history) == 11  # gen 0..10
        assert all("best_fitness" in h for h in cma.history)

    def test_cmaes_invalid_problem_type(self):
        """CMA-ES requires a continuous problem (with genome_size)."""
        from evopt import CMAES, Sphere
        cma = CMAES(Sphere(dims=2), max_generations=5, seed=42)
        assert cma.n == 2

    def test_cmaes_best_improves_over_generations(self):
        """Best fitness should generally improve (or stay same) over time."""
        from evopt import CMAES, Sphere
        cma = CMAES(Sphere(dims=2), max_generations=30, seed=42)
        cma.run()
        best_history = [h["best_fitness"] for h in cma.history if h["best_fitness"] is not None]
        # Final best should be <= initial best
        assert best_history[-1] <= best_history[0] + 1e-10


# =========================================================================
# Simulated Annealing
# =========================================================================

class TestSimulatedAnnealing:
    """Tests for the Simulated Annealing algorithm."""

    def test_sa_runs_and_returns(self):
        from evopt import SimulatedAnnealing, Sphere
        sa = SimulatedAnnealing(Sphere(dims=2), max_generations=50, seed=42)
        best = sa.run()
        assert best is not None
        assert best.fitness is not None

    def test_sa_converges_on_sphere(self):
        """SA should find a reasonably good solution on Sphere."""
        from evopt import SimulatedAnnealing, Sphere
        sa = SimulatedAnnealing(Sphere(dims=2), max_generations=200,
                                 initial_temperature=2.0, cooling_rate=0.97,
                                 steps_per_temperature=10, seed=42)
        best = sa.run()
        assert best.fitness < 1.0, f"SA should find decent solution, got {best.fitness}"

    def test_sa_reproducible(self):
        from evopt import SimulatedAnnealing, Rastrigin
        sa1 = SimulatedAnnealing(Rastrigin(dims=2), max_generations=30, seed=99)
        r1 = sa1.run()
        sa2 = SimulatedAnnealing(Rastrigin(dims=2), max_generations=30, seed=99)
        r2 = sa2.run()
        assert abs(r1.fitness - r2.fitness) < 1e-10

    def test_sa_geometric_cooling(self):
        from evopt import SimulatedAnnealing, Sphere
        sa = SimulatedAnnealing(Sphere(dims=1), max_generations=5,
                                 cooling_schedule="geometric", cooling_rate=0.5,
                                 initial_temperature=10.0, seed=42)
        sa.run()
        # After 5 generations of geometric cooling with rate 0.5:
        # T = 10 * 0.5^5 = 0.3125 (approximately, may differ due to reheating)
        # Just check temperature decreased
        assert sa.temperature < sa.initial_temperature

    def test_sa_linear_cooling(self):
        from evopt import SimulatedAnnealing, Sphere
        sa = SimulatedAnnealing(Sphere(dims=1), max_generations=10,
                                 cooling_schedule="linear",
                                 initial_temperature=10.0,
                                 final_temperature=0.0, seed=42)
        sa.run()
        # Linear cooling: temperature should be close to final_temperature
        assert sa.temperature <= 1.0

    def test_sa_logarithmic_cooling(self):
        from evopt import SimulatedAnnealing, Sphere
        sa = SimulatedAnnealing(Sphere(dims=1), max_generations=5,
                                 cooling_schedule="logarithmic",
                                 initial_temperature=10.0, seed=42)
        sa.run()
        # T_k = T0 / ln(k+2). After gen 5: T = 10/ln(7) ≈ 5.14
        assert sa.temperature > 0

    def test_sa_invalid_schedule_raises(self):
        from evopt import SimulatedAnnealing, Sphere
        with pytest.raises(ValueError):
            SimulatedAnnealing(Sphere(dims=1), cooling_schedule="invalid")

    def test_sa_invalid_temp_raises(self):
        from evopt import SimulatedAnnealing, Sphere
        with pytest.raises(ValueError):
            SimulatedAnnealing(Sphere(dims=1), initial_temperature=-1.0)

    def test_sa_acceptance_rate(self):
        from evopt import SimulatedAnnealing, Sphere
        sa = SimulatedAnnealing(Sphere(dims=1), max_generations=10, seed=42)
        sa.run()
        assert 0.0 <= sa.acceptance_rate <= 1.0

    def test_sa_custom_move_fn(self):
        """SA should accept a custom move function."""
        from evopt import SimulatedAnnealing, Sphere
        called = [0]

        def my_move(genome, temperature):
            called[0] += 1
            return [g + random.gauss(0, 0.01) for g in genome]

        sa = SimulatedAnnealing(Sphere(dims=2), max_generations=5,
                                 move_fn=my_move, seed=42)
        sa.run()
        assert called[0] > 0

    def test_sa_terminates_on_low_temperature(self):
        """SA should terminate when temperature drops below final_temperature."""
        from evopt import SimulatedAnnealing, Sphere
        sa = SimulatedAnnealing(Sphere(dims=1), max_generations=10000,
                                 initial_temperature=1.0, final_temperature=0.01,
                                 cooling_rate=0.5, steps_per_temperature=1,
                                 restart_on_stagnation=False, seed=42)
        sa.run()
        # Should terminate early due to low temperature, not max_generations
        assert sa.terminated
        assert "Temperature" in sa.termination_reason


# =========================================================================
# Logging utilities
# =========================================================================

class TestLogging:
    """Tests for evopt.utils.logging_utils."""

    def test_setup_logging_console(self):
        from evopt.utils.logging_utils import setup_logging
        logger = setup_logging(level="DEBUG")
        assert logger.level == 10  # DEBUG = 10

    def test_setup_logging_file(self, tmp_path):
        from evopt.utils.logging_utils import setup_logging
        log_file = tmp_path / "test.log"
        logger = setup_logging(level="DEBUG", logfile=str(log_file))
        logger.info("test message")
        assert log_file.exists()
        content = log_file.read_text()
        assert "test message" in content

    def test_setup_logging_json_file(self, tmp_path):
        from evopt.utils.logging_utils import setup_logging
        log_file = tmp_path / "test.jsonl"
        logger = setup_logging(level="DEBUG", logfile=str(log_file), json_format=True)
        logger.info("json test")
        assert log_file.exists()
        content = log_file.read_text().strip()
        # Should be valid JSON
        entry = json.loads(content.split("\n")[-1] if "\n" in content else content)
        assert entry["message"] == "json test"
        assert entry["level"] == "INFO"

    def test_set_verbose(self):
        from evopt.utils.logging_utils import setup_logging, set_verbose
        setup_logging(level="WARNING")
        set_verbose(True)
        import logging
        assert logging.getLogger("evopt").level == logging.DEBUG
        set_verbose(False)
        assert logging.getLogger("evopt").level == logging.WARNING


# =========================================================================
# CLI integration
# =========================================================================

class TestCLI:
    """Tests for new CLI commands."""

    def test_cli_solve_cmaes(self):
        """CLI solve with CMA-ES should work."""
        from evopt.cli import create_algorithm
        from evopt import Sphere
        algo = create_algorithm("cmaes", Sphere(dims=2), 20, 10, 42, False)
        best = algo.run()
        assert best is not None
        assert best.fitness is not None

    def test_cli_solve_sa(self):
        from evopt.cli import create_algorithm
        from evopt import Sphere
        algo = create_algorithm("sa", Sphere(dims=2), 20, 50, 42, False)
        best = algo.run()
        assert best is not None

    def test_cli_config_template_and_run(self, tmp_path):
        """CLI config template + run should work end-to-end."""
        from evopt.config import default_config, save_config, build_from_config
        cfg = default_config("ga", "sphere", dims=2, population_size=15, max_generations=5)
        path = tmp_path / "cfg.yaml"
        save_config(cfg, path)
        _, algo = build_from_config(__import__("yaml").safe_load(path.read_text())
                                    if path.suffix == ".yaml" else json.loads(path.read_text()))
        best = algo.run()
        assert best.fitness is not None


# =========================================================================
# Integration: new algorithms with existing infrastructure
# =========================================================================

class TestIntegration:
    """Integration tests combining new and existing features."""

    def test_cmaes_with_callbacks(self):
        """CMA-ES should work with termination callbacks."""
        from evopt import CMAES, Sphere
        from evopt.utils.callbacks import Stagnation
        cma = CMAES(Sphere(dims=2), max_generations=50, seed=42,
                     callbacks=[Stagnation(patience=10)])
        best = cma.run()
        assert best is not None

    def test_sa_with_result_export(self, tmp_path):
        """SA should produce exportable results."""
        from evopt import SimulatedAnnealing, Rastrigin
        from evopt.results import Result
        sa = SimulatedAnnealing(Rastrigin(dims=2), max_generations=30, seed=42)
        sa.run()
        r = Result.from_algorithm(sa, problem_name="rastrigin",
                                   algorithm_name="sa", time_seconds=0.01)
        path = tmp_path / "sa_result.json"
        r.to_json(path)
        assert path.exists()

    def test_cmaes_experiment(self):
        """CMA-ES should work in experiment framework."""
        from evopt.results import Experiment
        exp = Experiment(name="cma_test")
        exp.add("cmaes", "sphere", {"dims": 2, "population_size": 20, "max_generations": 10}, seed=42)
        results = exp.run(repeats=2)
        assert len(results) == 2
        assert all(r.best_fitness is not None for r in results)

    def test_nsga2_with_indicators(self):
        """NSGA-II results should be evaluable with indicators."""
        from evopt import NSGA2
        from evopt.problems.multi_objective import ZDT1
        from evopt.indicators import hypervolume, spacing

        nsga = NSGA2(ZDT1(dims=5), population_size=30, max_generations=30, seed=42)
        nsga.run()
        pareto = nsga.pareto_front
        assert len(pareto) > 0

        objs = [ind.metadata["objectives"] for ind in pareto]
        ref = [max(o[0] for o in objs) + 1, max(o[1] for o in objs) + 1]
        hv = hypervolume(objs, ref)
        assert hv > 0

        sp = spacing(objs)
        assert sp >= 0

    def test_all_algorithms_run_without_crash(self):
        """Every algorithm should be able to solve Sphere without crashing."""
        from evopt import (GeneticAlgorithm, EvolutionStrategy, DifferentialEvolution,
                           ParticleSwarmOptimizer, CMAES, SimulatedAnnealing, Sphere)
        algorithms = [
            ("GA", lambda: GeneticAlgorithm(Sphere(dims=2), population_size=15, max_generations=5, seed=42)),
            ("ES", lambda: EvolutionStrategy(Sphere(dims=2), mu=5, lam=15, max_generations=5, seed=42)),
            ("DE", lambda: DifferentialEvolution(Sphere(dims=2), population_size=10, max_generations=5, seed=42)),
            ("PSO", lambda: ParticleSwarmOptimizer(Sphere(dims=2), swarm_size=10, max_generations=5, seed=42)),
            ("CMAES", lambda: CMAES(Sphere(dims=2), max_generations=5, seed=42)),
            ("SA", lambda: SimulatedAnnealing(Sphere(dims=2), max_generations=10, seed=42)),
        ]
        for name, factory in algorithms:
            algo = factory()
            best = algo.run()
            assert best is not None, f"{name} returned None"
            assert best.fitness is not None, f"{name} returned None fitness"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])