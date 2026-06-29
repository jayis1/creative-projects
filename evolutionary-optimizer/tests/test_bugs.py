"""Bug hunt tests — verify bugs before fixing them."""
import pytest
import random

# Bug 1: PMX crossover mapping is reversed, producing invalid permutations
def test_pmx_produces_valid_permutation():
    """PMX should always produce valid permutations (each element appears exactly once)."""
    from evopt.operators.crossover import pmx_crossover
    random.seed(42)
    # Create parents where the segment values differ significantly
    parent1 = [0, 1, 2, 3, 4, 5]
    parent2 = [3, 4, 5, 0, 1, 2]
    # Force segment to be indices 0-2
    orig_sample = random.sample
    random.sample = lambda pop, k: [0, 2]
    try:
        c1, c2 = pmx_crossover(parent1, parent2)
        assert sorted(c1) == list(range(6)), f"c1 not valid permutation: {c1}, sorted={sorted(c1)}"
        assert sorted(c2) == list(range(6)), f"c2 not valid permutation: {c2}, sorted={sorted(c2)}"
    finally:
        random.sample = orig_sample


# Bug 2: Individual._next_id never resets — unbounded memory growth in NSGA2 cache
def test_individual_id_reset():
    """Individual IDs should be resettable to prevent unbounded memory growth."""
    from evopt.core import Individual
    Individual.reset_id_counter()
    id1 = Individual([1.0]).id
    id2 = Individual([2.0]).id
    assert id1 == 0
    assert id2 == 1
    Individual.reset_id_counter()
    id3 = Individual([3.0]).id
    assert id3 == 0, f"ID should be 0 after reset, got {id3}"


# Bug 3: Population.sort crashes when comparing individuals with None fitness
def test_population_sort_all_none_fitness():
    """Population.sort should handle ALL individuals having None fitness."""
    from evopt.core import Individual, Population
    pop = Population()
    for i in range(5):
        pop.append(Individual([float(i)], fitness=None))
    # This should not raise TypeError when comparing None values
    try:
        pop.sort(maximize=False)
    except TypeError as e:
        pytest.fail(f"Population.sort crashed with all None fitness: {e}")


# Bug 4: DE exponential crossover infinite loop when CR >= 1.0
def test_de_exponential_crossover_cr_eq_1():
    """DE exponential crossover should terminate when CR=1.0 (always copy)."""
    from evopt import DifferentialEvolution, Sphere
    de = DifferentialEvolution(Sphere(dims=3), population_size=10, max_generations=5,
                                CR=1.0, crossover_type='exponential', seed=42)
    try:
        best = de.run()
        assert best is not None
    except Exception as e:
        pytest.fail(f"DE with CR=1.0 exponential crossover failed: {e}")


# Bug 5: Knapsack evaluate returns negative for infeasible but GA treats it as fitness
def test_knapsack_infeasible_fitness_is_not_qualified():
    """Knapsack.evaluate returns negative for over-capacity solutions.
    This negative value is incorrectly treated as a valid fitness by minimization."""
    from evopt import Knapsack
    kp = Knapsack(items=[(10, 5), (10, 5), (1, 100)], capacity=5)
    # All items selected -> weight=21 > capacity=5
    genome = [1, 1, 1]
    fitness = kp.evaluate(genome)
    # The fitness should indicate infeasibility, not just be a large negative number
    # that a minimizer might interpret as "great, very low fitness!"
    assert fitness < 0, f"Over-capacity should return negative, got {fitness}"
    # But this negative fitness is lower than any feasible solution's positive fitness,
    # so a minimizer would prefer the infeasible solution! This is a bug.
    feasible_fitness = kp.evaluate([0, 0, 1])  # weight=1 <= 5, value=100
    assert feasible_fitness == 100
    # If minimizing, the infeasible solution (-16) would be preferred over feasible (100).
    # If maximizing, the feasible (100) is preferred. So the bug only affects minimization.


# Bug 6: PSO global_best_position can be None when evolve_one_generation is called
def test_pso_global_best_not_none_in_evolve():
    """PSO should have global_best_position set before evolve_one_generation uses it."""
    from evopt import ParticleSwarmOptimizer, Sphere
    pso = ParticleSwarmOptimizer(Sphere(dims=2), swarm_size=5, max_generations=3, seed=42)
    pso.population = pso.initialize()
    pso.evaluate_population(pso.population)
    # global_best_position should be set after evaluation
    assert pso.global_best_position is not None, "global_best_position should be set after evaluation"
    # Now evolve should work
    new_pop = pso.evolve_one_generation()
    assert len(new_pop) == 5


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])