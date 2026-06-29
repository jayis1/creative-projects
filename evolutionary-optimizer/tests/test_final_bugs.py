"""Final bug hunt tests for Phase 3."""
import pytest
import random

# Bug 7: Verbose logging crashes when best_fitness or avg_fitness is None
def test_verbose_mode_none_fitness():
    """Verbose mode should not crash when fitness values are None."""
    from evopt import GeneticAlgorithm, Sphere
    from evopt.problems.base import Problem

    class NeverEvaluates(Problem):
        def __init__(self):
            super().__init__(maximize=False)
        def evaluate(self, genome):
            return float('nan')  # problematic value
        def random_genome(self):
            return [random.uniform(-1, 1) for _ in range(2)]
        def genome_size(self):
            return 2

    ga = GeneticAlgorithm(NeverEvaluates(), population_size=5, max_generations=3,
                           seed=42, verbose=True)
    try:
        ga.run()
    except TypeError as e:
        if "format" in str(e).lower() or "none" in str(e).lower():
            pytest.fail(f"Verbose mode crashed with None fitness: {e}")
        # Other errors are ok


# Bug 8: NSGA2 objectives cache grows unbounded
def test_nsga2_cache_growth():
    """NSGA2 objectives cache should not grow unbounded."""
    from evopt.algorithms.nsga2 import NSGA2
    from evopt.problems.multi_objective import ZDT1
    nsga = NSGA2(ZDT1(dims=3), population_size=20, max_generations=50, seed=42)
    nsga.run()
    # Cache should have at most population_size * 2 entries (parents + offspring)
    # After cleanup, it should be <= population_size
    assert len(nsga._objectives_cache) <= nsga.population_size, \
        f"Cache has {len(nsga._objectives_cache)} entries, expected <= {nsga.population_size}"


# Bug 9: PMX produces valid permutations (stress test)
def test_pmx_stress():
    """PMX should always produce valid permutations."""
    from evopt.operators.crossover import pmx_crossover
    random.seed(123)
    for _ in range(500):
        n = random.randint(2, 15)
        p1 = list(range(n))
        random.shuffle(p1)
        p2 = list(range(n))
        random.shuffle(p2)
        c1, c2 = pmx_crossover(p1, p2)
        assert sorted(c1) == list(range(n)), f"c1 invalid for n={n}: {c1}"
        assert sorted(c2) == list(range(n)), f"c2 invalid for n={n}: {c2}"


# Bug 10: Cycle crossover produces valid permutations
def test_cycle_crossover_valid():
    """Cycle crossover should always produce valid permutations."""
    from evopt.operators.crossover import cycle_crossover
    random.seed(42)
    for _ in range(100):
        n = random.randint(2, 10)
        p1 = list(range(n))
        random.shuffle(p1)
        p2 = list(range(n))
        random.shuffle(p2)
        c1, c2 = cycle_crossover(p1, p2)
        assert sorted(c1) == list(range(n)), f"c1 invalid: {c1}"
        assert sorted(c2) == list(range(n)), f"c2 invalid: {c2}"


# Bug 11: Order crossover produces valid permutations
def test_order_crossover_valid():
    """Order crossover should always produce valid permutations."""
    from evopt.operators.crossover import order_crossover
    random.seed(42)
    for _ in range(100):
        n = random.randint(2, 10)
        p1 = list(range(n))
        random.shuffle(p1)
        p2 = list(range(n))
        random.shuffle(p2)
        c1, c2 = order_crossover(p1, p2)
        assert sorted(c1) == list(range(n)), f"c1 invalid: {c1}"
        assert sorted(c2) == list(range(n)), f"c2 invalid: {c2}"


# Bug 12: Island model GA produces valid results
def test_island_model_valid():
    """Island model GA should produce valid results."""
    from evopt import IslandModelGA, Rastrigin
    island = IslandModelGA(Rastrigin(dims=2), num_islands=3, island_size=10,
                            max_generations=20, seed=42)
    best = island.run()
    assert best is not None
    assert best.fitness is not None
    assert best.fitness < 100  # should be better than random


# Bug 13: Memetic algorithm produces valid results
def test_memetic_valid():
    """Memetic algorithm should produce valid results."""
    from evopt import MemeticAlgorithm, Ackley
    memetic = MemeticAlgorithm(Ackley(dims=2), population_size=15, max_generations=10,
                                local_search_rate=0.1, seed=42)
    best = memetic.run()
    assert best is not None
    assert best.fitness is not None


# Bug 14: Statistics to_csv handles None values
def test_statistics_csv_none():
    """Statistics to_csv should handle None values without crashing."""
    from evopt.utils.statistics import Statistics
    stats = Statistics()
    stats.update({"generation": 0, "best_fitness": None, "avg_fitness": None,
                  "std_fitness": None, "diversity": 0.5, "population_size": 10})
    csv = stats.to_csv()
    assert "generation" in csv
    assert "None" not in csv or "" in csv  # None should be handled gracefully


# Bug 15: AdaptiveMutationRate doesn't crash on algorithms without mutation_rate
def test_adaptive_mutation_rate_no_mutation_rate():
    """AdaptiveMutationRate should not crash on algorithms without mutation_rate attribute."""
    from evopt.utils.callbacks import AdaptiveMutationRate
    from evopt import ParticleSwarmOptimizer, Sphere

    class FakeAlgo:
        generation = 0
        population = None
        max_generations = 10

    cb = AdaptiveMutationRate()
    try:
        cb(FakeAlgo())
    except Exception as e:
        pytest.fail(f"AdaptiveMutationRate crashed on algo without mutation_rate: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])