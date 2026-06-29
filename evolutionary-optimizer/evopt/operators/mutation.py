"""Mutation operators."""

from __future__ import annotations

import random
import copy
from typing import List, Sequence, Any


def gaussian_mutation(genome: Sequence[float], rate: float = 0.1, sigma: float = 0.2,
                      bounds: Sequence = None) -> List[float]:
    """Gaussian mutation: add N(0, sigma) to each gene with probability *rate*.

    Args:
        genome: Real-valued genome.
        rate: Per-gene mutation probability.
        sigma: Standard deviation of the Gaussian noise.
        bounds: Optional [(lo, hi), ...] to clip results.
    """
    result = list(genome)
    for i in range(len(result)):
        if random.random() < rate:
            result[i] += random.gauss(0, sigma)
            if bounds is not None:
                lo, hi = bounds[i]
                result[i] = max(lo, min(hi, result[i]))
    return result


def polynomial_mutation(genome: Sequence[float], rate: float = 0.1, eta: float = 20.0,
                        bounds: Sequence = None) -> List[float]:
    """Polynomial mutation (Deb & Goyal): perturbs each gene with a polynomial distribution.

    Args:
        genome: Real-valued genome.
        rate: Per-gene mutation probability.
        eta: Distribution index (higher = smaller perturbation).
        bounds: Optional [(lo, hi), ...] for boundary handling.
    """
    result = list(genome)
    for i in range(len(result)):
        if random.random() > rate:
            continue
        x = result[i]
        # Guard against non-real inputs (can arise from SBX numerical issues)
        if isinstance(x, complex):
            x = x.real
        lo, hi = bounds[i] if bounds else (x - 1.0, x + 1.0)
        delta = hi - lo
        if delta <= 0:
            continue
        # Clamp x to bounds to avoid complex exponentiation
        x = max(lo, min(hi, x))
        u = random.random()
        delta1 = (x - lo) / delta
        delta2 = (hi - x) / delta
        mut_pow = 1.0 / (eta + 1)
        if u <= 0.5:
            xy = 1 - delta1
            # Guard: xy must be >= 0 for real exponentiation
            xy = max(xy, 0.0)
            val = 2 * u + (1 - 2 * u) * (xy ** (eta + 1))
            deltaq = abs(val) ** mut_pow - 1
        else:
            xy = 1 - delta2
            xy = max(xy, 0.0)
            val = 2 * (1 - u) + (2 * u - 1) * (xy ** (eta + 1))
            deltaq = 1 - abs(val) ** mut_pow
        x = x + deltaq * delta
        result[i] = max(lo, min(hi, x))
    return result


def bit_flip_mutation(genome: Sequence[int], rate: float = 0.01) -> List[int]:
    """Bit-flip mutation for binary genomes: flip each bit with probability *rate*."""
    if not (0.0 <= rate <= 1.0):
        raise ValueError("rate must be in [0, 1]")
    return [1 - g if random.random() < rate else g for g in genome]


def swap_mutation(genome: Sequence, rate: float = 0.2) -> List:
    """Swap mutation for permutations: swap two random positions with probability *rate*."""
    result = list(genome)
    if random.random() < rate and len(result) >= 2:
        i, j = random.sample(range(len(result)), 2)
        result[i], result[j] = result[j], result[i]
    return result


def random_reset_mutation(genome: Sequence, rate: float = 0.01, values: Sequence = None) -> List:
    """Random-reset mutation: replace each gene with a random value from *values* with probability *rate*.

    Args:
        genome: The genome to mutate.
        rate: Per-gene mutation probability.
        values: Pool of possible replacement values (default: {0, 1} for binary).
    """
    if values is None:
        values = [0, 1]
    result = list(genome)
    for i in range(len(result)):
        if random.random() < rate:
            result[i] = random.choice(list(values))
    return result


def inversion_mutation(genome: Sequence, rate: float = 0.2) -> List:
    """Inversion mutation for permutations: reverse a random subsequence with probability *rate*."""
    result = list(genome)
    if random.random() < rate and len(result) >= 2:
        i, j = sorted(random.sample(range(len(result)), 2))
        result[i:j + 1] = result[i:j + 1][::-1]
    return result


def insert_mutation(genome: Sequence, rate: float = 0.2) -> List:
    """Insert mutation for permutations: remove a gene at position i and insert at position j."""
    result = list(genome)
    if random.random() < rate and len(result) >= 2:
        i, j = random.sample(range(len(result)), 2)
        val = result.pop(i)
        result.insert(j, val)
    return result


def scramble_mutation(genome: Sequence, rate: float = 0.2) -> List:
    """Scramble mutation for permutations: shuffle a random subsequence with probability *rate*."""
    result = list(genome)
    if random.random() < rate and len(result) >= 2:
        i, j = sorted(random.sample(range(len(result)), 2))
        segment = result[i:j + 1]
        random.shuffle(segment)
        result[i:j + 1] = segment
    return result