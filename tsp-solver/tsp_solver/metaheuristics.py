"""Metaheuristic algorithms for TSP: Simulated Annealing, Genetic Algorithm, Ant Colony."""

from __future__ import annotations

import math
import random
from typing import List, Optional, Tuple

from .instance import TSPInstance
from .tour import Tour


def simulated_annealing(
    instance: TSPInstance,
    tour: Optional[Tour] = None,
    *,
    initial_temp: float = 100.0,
    cooling_rate: float = 0.9995,
    min_temp: float = 1e-3,
    max_iter: int = 100000,
    seed: Optional[int] = None,
) -> Tour:
    """Simulated annealing with 2-opt-style moves.

    Uses the geometric cooling schedule ``T *= cooling_rate`` and accepts
    worse solutions with probability ``exp(delta / T)``.
    """
    from .heuristics import nearest_neighbor

    rng = random.Random(seed)
    if tour is None:
        tour = nearest_neighbor(instance, start=rng.randint(0, instance.n - 1))

    order = list(tour.order)
    n = len(order)
    matrix = instance.matrix
    current_cost = instance.tour_length(order)
    best_order = list(order)
    best_cost = current_cost
    temp = initial_temp

    for it in range(max_iter):
        if temp < min_temp:
            break
        # Pick two random indices and reverse the segment (2-opt move)
        i, j = sorted(rng.sample(range(n), 2))
        if i == j:
            continue
        # Skip when the segment wraps the entire tour (i=0, j=n-1): the two
        # edges being broken are the same wrap-around edge, so the delta
        # formula would be incorrect.
        if i == 0 and j == n - 1:
            continue
        a = order[i]
        b = order[(i - 1) % n]
        c = order[j]
        d = order[(j + 1) % n]
        # Cost change from reversing segment [i..j]
        delta = (matrix[b, c] + matrix[a, d]) - (matrix[b, a] + matrix[c, d])
        if delta < 0 or rng.random() < math.exp(-delta / temp):
            order[i : j + 1] = order[i : j + 1][::-1]
            current_cost += delta
            if current_cost < best_cost:
                best_cost = current_cost
                best_order = list(order)
        temp *= cooling_rate

    return Tour(best_order, best_cost)


def genetic_algorithm(
    instance: TSPInstance,
    *,
    population_size: int = 100,
    generations: int = 500,
    mutation_rate: float = 0.2,
    tournament_size: int = 5,
    elite_size: int = 2,
    seed: Optional[int] = None,
) -> Tour:
    """Genetic algorithm with order crossover (OX) and inversion mutation."""
    rng = random.Random(seed)
    n = instance.n
    matrix = instance.matrix

    def tour_cost(ind: List[int]) -> float:
        return float(matrix[ind, [ind[(i + 1) % n] for i in range(n)]].sum())

    def random_individual() -> List[int]:
        ind = list(range(n))
        rng.shuffle(ind)
        return ind

    def crossover(parent1: List[int], parent2: List[int]) -> List[int]:
        """Order crossover (OX): copy a slice from p1, fill rest from p2 in order."""
        a, b = sorted(rng.sample(range(n), 2))
        child = [-1] * n
        child[a:b] = parent1[a:b]
        p2_remaining = [c for c in parent2 if c not in set(child[a:b])]
        idx = 0
        for i in range(n):
            if child[i] == -1:
                child[i] = p2_remaining[idx]
                idx += 1
        return child

    def mutate(ind: List[int]) -> None:
        if rng.random() < mutation_rate:
            a, b = sorted(rng.sample(range(n), 2))
            ind[a : b + 1] = ind[a : b + 1][::-1]

    population = [random_individual() for _ in range(population_size)]
    costs = [tour_cost(ind) for ind in population]

    for gen in range(generations):
        # Sort by cost
        ranked = sorted(zip(population, costs), key=lambda x: x[1])
        population = [ind for ind, _ in ranked]
        costs = [c for _, c in ranked]

        new_pop = list(population[:elite_size])  # elitism
        new_costs = costs[:elite_size]
        while len(new_pop) < population_size:
            # Tournament selection
            contenders = rng.sample(range(min(population_size, len(population))), tournament_size)
            best_idx = min(contenders, key=lambda i: costs[i])
            p1 = population[best_idx]
            contenders = rng.sample(range(min(population_size, len(population))), tournament_size)
            best_idx = min(contenders, key=lambda i: costs[i])
            p2 = population[best_idx]
            child = crossover(p1, p2)
            mutate(child)
            new_pop.append(child)
            new_costs.append(tour_cost(child))
        population = new_pop
        costs = new_costs

    best_idx = min(range(len(costs)), key=lambda i: costs[i])
    return Tour(population[best_idx], costs[best_idx])


def ant_colony(
    instance: TSPInstance,
    *,
    n_ants: int = 50,
    n_iterations: int = 200,
    alpha: float = 1.0,
    beta: float = 3.0,
    rho: float = 0.1,
    Q: float = 100.0,
    seed: Optional[int] = None,
) -> Tour:
    """Ant Colony Optimization (ACS-style) for TSP.

    Parameters
    ----------
    alpha : float
        Pheromone influence exponent.
    beta : float
        Heuristic (visibility) influence exponent.
    rho : float
        Evaporation rate (0 < rho < 1).
    Q : float
        Pheromone deposit factor.
    """
    rng = random.Random(seed)
    n = instance.n
    matrix = instance.matrix

    # Avoid division by zero
    safe_dist = matrix.copy()
    safe_dist[safe_dist == 0] = 1e-10
    visibility = 1.0 / safe_dist

    pheromone = [[1.0 / n for _ in range(n)] for _ in range(n)]
    best_order: List[int] = []
    best_cost = math.inf

    for _ in range(n_iterations):
        all_tours: List[Tuple[List[int], float]] = []
        for _ in range(n_ants):
            start = rng.randint(0, n - 1)
            visited = [False] * n
            visited[start] = True
            order = [start]
            cur = start
            cost = 0.0
            for _ in range(n - 1):
                # Compute probabilities
                probs = []
                total = 0.0
                for j in range(n):
                    if visited[j]:
                        probs.append(0.0)
                    else:
                        p = (pheromone[cur][j] ** alpha) * (visibility[cur][j] ** beta)
                        probs.append(p)
                        total += p
                if total == 0:
                    # fallback: random unvisited
                    unvisited = [j for j in range(n) if not visited[j]]
                    nxt = rng.choice(unvisited)
                else:
                    probs = [p / total for p in probs]
                    nxt = rng.choices(range(n), weights=probs, k=1)[0]
                cost += matrix[cur, nxt]
                visited[nxt] = True
                order.append(nxt)
                cur = nxt
            cost += matrix[cur, start]
            all_tours.append((order, cost))
            if cost < best_cost:
                best_cost = cost
                best_order = list(order)
        # Evaporate
        for i in range(n):
            for j in range(n):
                pheromone[i][j] *= (1 - rho)
        # Deposit
        for order, cost in all_tours:
            deposit = Q / cost
            for i in range(n):
                a, b = order[i], order[(i + 1) % n]
                pheromone[a][b] += deposit
                pheromone[b][a] += deposit

    if not best_order:
        best_order = list(range(n))
        best_cost = instance.tour_length(best_order)
    return Tour(best_order, best_cost)