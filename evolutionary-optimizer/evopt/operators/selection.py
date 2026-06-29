"""Selection operators for evolutionary algorithms."""

from __future__ import annotations

import random
from typing import List
from ..core import Individual, Population


def tournament_selection(population: Population, k: int = 3, maximize: bool = False) -> Individual:
    """k-tournament selection: pick k random individuals, return the best.

    Args:
        population: The population to select from.
        k: Tournament size (number of individuals competing).
        maximize: If True, higher fitness wins; if False, lower fitness wins.
    """
    if len(population) == 0:
        raise ValueError("Cannot select from empty population")
    if k < 1:
        raise ValueError("Tournament size k must be >= 1")
    contestants = population.sample(min(k, len(population)))
    if maximize:
        return max(contestants, key=lambda i: i.fitness if i.fitness is not None else float('-inf'))
    else:
        return min(contestants, key=lambda i: i.fitness if i.fitness is not None else float('inf'))


def roulette_selection(population: Population, maximize: bool = True) -> Individual:
    """Roulette-wheel (fitness-proportionate) selection.

    For minimization problems, fitness is inverted: weight = max_fitness - fitness + epsilon.
    For maximization, weight = fitness - min_fitness + epsilon.

    Args:
        population: The population to select from.
        maximize: If True, use fitness directly; if False, use inverted fitness.
    """
    evaluated = [ind for ind in population.individuals if ind.fitness is not None]
    if not evaluated:
        raise ValueError("No evaluated individuals for roulette selection")
    fitnesses = [ind.fitness for ind in evaluated]
    min_f = min(fitnesses)
    max_f = max(fitnesses)
    if maximize:
        weights = [f - min_f + 1e-10 for f in fitnesses]
    else:
        weights = [max_f - f + 1e-10 for f in fitnesses]
    total = sum(weights)
    if total <= 0:
        # All weights zero (all fitnesses equal); pick randomly
        return random.choice(evaluated)
    r = random.uniform(0, total)
    cumulative = 0.0
    for ind, w in zip(evaluated, weights):
        cumulative += w
        if r <= cumulative:
            return ind
    return evaluated[-1]  # fallback


def rank_selection(population: Population, maximize: bool = False, pressure: float = 2.0) -> Individual:
    """Rank-based selection with linear ranking.

    Args:
        population: The population to select from.
        maximize: If True, rank from worst to best (best gets highest rank).
        pressure: Selection pressure (1.0 = no pressure, 2.0 = typical).
    """
    evaluated = [ind for ind in population.individuals if ind.fitness is not None]
    if not evaluated:
        raise ValueError("No evaluated individuals for rank selection")
    n = len(evaluated)
    evaluated.sort(key=lambda i: i.fitness, reverse=not maximize)
    # Best individual gets rank 0 (highest weight)
    weights = [pressure - (pressure - 1) * i / max(n - 1, 1) for i in range(n)]
    total = sum(weights)
    r = random.uniform(0, total)
    cumulative = 0.0
    for ind, w in zip(evaluated, weights):
        cumulative += w
        if r <= cumulative:
            return ind
    return evaluated[-1]


def SUS_selection(population: Population, n: int, maximize: bool = True) -> List[Individual]:
    """Stochastic Universal Sampling — selects n individuals with a single random spin.

    Better distribution than n independent roulette spins; reduces selection bias.

    Args:
        population: The population to select from.
        n: Number of individuals to select.
        maximize: If True, higher fitness gets more slots.
    """
    evaluated = [ind for ind in population.individuals if ind.fitness is not None]
    if not evaluated:
        raise ValueError("No evaluated individuals for SUS")
    if n < 1:
        raise ValueError("n must be >= 1")
    fitnesses = [ind.fitness for ind in evaluated]
    min_f = min(fitnesses)
    max_f = max(fitnesses)
    if maximize:
        weights = [f - min_f + 1e-10 for f in fitnesses]
    else:
        weights = [max_f - f + 1e-10 for f in fitnesses]
    total = sum(weights)
    if total <= 0:
        return random.choices(evaluated, k=n)
    # Place individuals on a wheel with cumulative weights
    pointer_distance = total / n
    start = random.uniform(0, pointer_distance)
    pointers = [start + i * pointer_distance for i in range(n)]
    selected = []
    cumulative = 0.0
    idx = 0
    for p in pointers:
        while cumulative < p and idx < len(evaluated):
            cumulative += weights[idx]
            idx += 1
        selected.append(evaluated[min(idx - 1, len(evaluated) - 1)] if idx > 0 else evaluated[0])
    return selected