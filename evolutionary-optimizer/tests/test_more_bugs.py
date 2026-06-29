"""Additional bug hunt tests."""
import pytest
import random

# Bug 3: NSGA2 crowding_distance computes wrong obj_min/obj_max when maximize[m]=True
def test_crowding_distance_maximize_boundary():
    """When maximize[m]=True, the first sorted element has the highest objective value.
    But obj_min/obj_max are computed from sorted_front[0] and sorted_front[-1],
    which when reverse=True gives obj_max at [0] and obj_min at [-1].
    So obj_min should be sorted_front[-1] and obj_max should be sorted_front[0].
    But the code does: obj_min = objectives[sorted_front[0]], obj_max = objectives[sorted_front[-1]]
    which is reversed when maximize=True!
    """
    from evopt.algorithms.nsga2 import crowding_distance
    # 4 solutions with objective values 1, 5, 7, 10 (maximize)
    objectives = [[10.0], [5.0], [1.0], [7.0]]
    front = [0, 1, 2, 3]
    distances = crowding_distance(objectives, front, maximize=[True])
    # The denominator should be max - min = 10 - 1 = 9 (positive)
    # If the bug exists, denom = 1 - 10 = -9 (negative), making distances negative
    for idx in front:
        d = distances[idx]
        # Non-boundary solutions should have positive distances
        if d != float('inf'):
            assert d >= 0, f"Distance for idx {idx} is {d}, should be non-negative"


# Bug 4: Knapsack evaluate returns negative for infeasible, which is better for minimizers
def test_knapsack_repair_makes_feasible():
    """Knapsack.repair should produce a feasible genome."""
    from evopt import Knapsack
    kp = Knapsack(items=[(10, 5), (10, 5), (1, 100)], capacity=5)
    genome = [1, 1, 1]  # weight=21 > capacity=5
    repaired = kp.repair(genome)
    total_weight = sum(kp.items[i][0] for i, b in enumerate(repaired) if b)
    assert total_weight <= kp.capacity, \
        f"Repaired genome still over capacity: weight={total_weight} > {kp.capacity}"


# Bug 5: ES _extract uses integer division but genome might have odd length if genome_size changes
def test_es_extract_odd_length():
    """ES _extract should handle genomes with even length properly."""
    from evopt import EvolutionStrategy, Sphere
    es = EvolutionStrategy(Sphere(dims=3), mu=5, lam=10, max_generations=1, seed=42)
    pop = es.initialize()
    ind = pop[0]
    solution, sigmas = es._extract(ind)
    assert len(solution) == 3, f"Solution should have 3 elements, got {len(solution)}"
    assert len(sigmas) == 3, f"Sigmas should have 3 elements, got {len(sigmas)}"


# Bug 6: Order crossover (OX) can produce wrong-length children when a=0
def test_ox_a_zero():
    """OX should handle a=0 (segment from start) correctly."""
    from evopt.operators.crossover import order_crossover
    random.seed(42)
    parent1 = [0, 1, 2, 3, 4]
    parent2 = [4, 3, 2, 1, 0]
    # Force a=0, b=2
    orig_sample = random.sample
    random.sample = lambda pop, k: [0, 2]
    try:
        c1, c2 = order_crossover(parent1, parent2)
        assert len(c1) == 5, f"c1 should have 5 elements, got {len(c1)}: {c1}"
        assert len(c2) == 5, f"c2 should have 5 elements, got {len(c2)}: {c2}"
        assert sorted(c1) == list(range(5)), f"c1 not valid permutation: {c1}"
        assert sorted(c2) == list(range(5)), f"c2 not valid permutation: {c2}"
    finally:
        random.sample = orig_sample


# Bug 7: GA with empty population after elitism
def test_ga_elite_size_larger_than_population():
    """GA should handle elite_size > population_size gracefully."""
    from evopt import GeneticAlgorithm, Sphere
    ga = GeneticAlgorithm(Sphere(dims=2), population_size=10, max_generations=5,
                          elite_size=20, seed=42)  # elite_size > pop_size
    try:
        best = ga.run()
        assert best is not None
    except Exception as e:
        pytest.fail(f"GA with elite_size > pop_size failed: {e}")


# Bug 8: Stagnation callback never resets between runs
def test_stagnation_reset():
    """Stagnation callback should work correctly when reused."""
    from evopt import GeneticAlgorithm, Sphere
    from evopt.utils.callbacks import Stagnation
    stagnation = Stagnation(patience=3)
    ga = GeneticAlgorithm(Sphere(dims=2), population_size=10, max_generations=50,
                           seed=42, callbacks=[stagnation])
    ga.run()
    # Run again — the callback should reset its internal state
    ga2 = GeneticAlgorithm(Sphere(dims=2), population_size=10, max_generations=50,
                            seed=43, callbacks=[stagnation])
    try:
        ga2.run()
    except Exception as e:
        pytest.fail(f"Stagnation callback failed on reuse: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])