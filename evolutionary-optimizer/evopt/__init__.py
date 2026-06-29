"""EvOpt — A from-scratch evolutionary optimization toolkit.

Provides genetic algorithms, evolution strategies, differential evolution,
particle swarm optimization, and NSGA-II multi-objective optimization.
Pure Python, NumPy-optional.
"""

from .core import Individual, Population
from .algorithms.ga import GeneticAlgorithm
from .algorithms.es import EvolutionStrategy
from .algorithms.de import DifferentialEvolution
from .algorithms.pso import ParticleSwarmOptimizer
from .algorithms.nsga2 import NSGA2
from .problems.base import Problem, ContinuousProblem, CombinatorialProblem
from .problems.sphere import Sphere
from .problems.rastrigin import Rastrigin
from .problems.rosenbrock import Rosenbrock
from .problems.tsp import TSP
from .problems.knapsack import Knapsack
from .operators.selection import tournament_selection, roulette_selection, rank_selection, SUS_selection
from .operators.crossover import uniform_crossover, blx_alpha_crossover, sbx_crossover, one_point_crossover, order_crossover
from .operators.mutation import gaussian_mutation, polynomial_mutation, bit_flip_mutation, swap_mutation, random_reset_mutation
from .utils.statistics import Statistics
from .utils.logging_utils import get_logger

__version__ = "1.0.0"

__all__ = [
    "Individual", "Population",
    "GeneticAlgorithm", "EvolutionStrategy", "DifferentialEvolution",
    "ParticleSwarmOptimizer", "NSGA2",
    "Problem", "ContinuousProblem", "CombinatorialProblem",
    "Sphere", "Rastrigin", "Rosenbrock", "TSP", "Knapsack",
    "tournament_selection", "roulette_selection", "rank_selection", "SUS_selection",
    "uniform_crossover", "blx_alpha_crossover", "sbx_crossover", "one_point_crossover", "order_crossover",
    "gaussian_mutation", "polynomial_mutation", "bit_flip_mutation", "swap_mutation", "random_reset_mutation",
    "Statistics", "get_logger",
]