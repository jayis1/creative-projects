"""EvOpt — A from-scratch evolutionary optimization toolkit.

Provides genetic algorithms, evolution strategies, differential evolution,
particle swarm optimization, NSGA-II multi-objective optimization, island model GA,
and memetic algorithms. Pure Python, no external dependencies.
"""

from .core import Individual, Population
from .algorithms.ga import GeneticAlgorithm
from .algorithms.es import EvolutionStrategy
from .algorithms.de import DifferentialEvolution
from .algorithms.pso import ParticleSwarmOptimizer
from .algorithms.nsga2 import NSGA2
from .algorithms.island_model import IslandModelGA
from .algorithms.memetic import MemeticAlgorithm
from .problems.base import Problem, ContinuousProblem, CombinatorialProblem
from .problems.sphere import Sphere
from .problems.rastrigin import Rastrigin
from .problems.rosenbrock import Rosenbrock
from .problems.tsp import TSP
from .problems.knapsack import Knapsack
from .problems.benchmarks import Ackley, Griewank, Schwefel, Michalewicz, Zakharov
from .problems.multi_objective import ZDT1, ZDT2
from .operators.selection import tournament_selection, roulette_selection, rank_selection, SUS_selection
from .operators.crossover import (uniform_crossover, one_point_crossover, two_point_crossover,
                                   blx_alpha_crossover, sbx_crossover, order_crossover,
                                   cycle_crossover, pmx_crossover)
from .operators.mutation import (gaussian_mutation, polynomial_mutation, bit_flip_mutation,
                                  swap_mutation, random_reset_mutation, inversion_mutation,
                                  insert_mutation, scramble_mutation)
from .utils.statistics import Statistics
from .utils.visualization import ascii_convergence_plot, ascii_pareto_front, diversity_plot
from .utils.callbacks import (MaxGenerations, FitnessThreshold, Stagnation,
                               TimeLimit, Convergence, AdaptiveMutationRate, AdaptiveInertia)
from .utils.logging_utils import get_logger

__version__ = "2.0.0"

__all__ = [
    "Individual", "Population",
    "GeneticAlgorithm", "EvolutionStrategy", "DifferentialEvolution",
    "ParticleSwarmOptimizer", "NSGA2", "IslandModelGA", "MemeticAlgorithm",
    "Problem", "ContinuousProblem", "CombinatorialProblem",
    "Sphere", "Rastrigin", "Rosenbrock", "TSP", "Knapsack",
    "Ackley", "Griewank", "Schwefel", "Michalewicz", "Zakharov",
    "ZDT1", "ZDT2",
    "tournament_selection", "roulette_selection", "rank_selection", "SUS_selection",
    "uniform_crossover", "one_point_crossover", "two_point_crossover",
    "blx_alpha_crossover", "sbx_crossover", "order_crossover", "cycle_crossover", "pmx_crossover",
    "gaussian_mutation", "polynomial_mutation", "bit_flip_mutation",
    "swap_mutation", "random_reset_mutation", "inversion_mutation", "insert_mutation", "scramble_mutation",
    "Statistics", "ascii_convergence_plot", "ascii_pareto_front", "diversity_plot",
    "MaxGenerations", "FitnessThreshold", "Stagnation", "TimeLimit", "Convergence",
    "AdaptiveMutationRate", "AdaptiveInertia",
    "get_logger",
]