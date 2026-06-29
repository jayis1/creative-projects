"""EvOpt — A from-scratch evolutionary optimization toolkit.

Provides genetic algorithms, evolution strategies, differential evolution,
particle swarm optimization, NSGA-II multi-objective optimization, island model GA,
memetic algorithms, CMA-ES, and simulated annealing. Pure Python with optional
numpy support for CMA-ES and indicator computations.

Modules:
    - ``evopt.core`` — Individual, Population
    - ``evopt.algorithms`` — 9 optimization algorithms
    - ``evopt.problems`` — Benchmark and custom problem definitions
    - ``evopt.operators`` — Selection, crossover, mutation operators
    - ``evopt.utils`` — Statistics, visualization, callbacks, logging
    - ``evopt.config`` — Configuration file support (YAML/JSON)
    - ``evopt.results`` — Result objects, batch experiments, parameter sweeps
    - ``evopt.indicators`` — Multi-objective performance indicators (HV, IGD, etc.)
    - ``evopt.cli`` — Command-line interface
"""

from .core import Individual, Population
from .algorithms.ga import GeneticAlgorithm
from .algorithms.es import EvolutionStrategy
from .algorithms.de import DifferentialEvolution
from .algorithms.pso import ParticleSwarmOptimizer
from .algorithms.nsga2 import NSGA2
from .algorithms.island_model import IslandModelGA
from .algorithms.memetic import MemeticAlgorithm
from .algorithms.cmaes import CMAES
from .algorithms.simulated_annealing import SimulatedAnnealing
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
from .utils.logging_utils import get_logger, setup_logging
from .results import Result, Experiment, parameter_sweep
from .indicators import (
    hypervolume, generational_distance, inverted_generational_distance,
    spacing, spread,
)

__version__ = "3.0.0"

__all__ = [
    # Core
    "Individual", "Population",
    # Algorithms
    "GeneticAlgorithm", "EvolutionStrategy", "DifferentialEvolution",
    "ParticleSwarmOptimizer", "NSGA2", "IslandModelGA", "MemeticAlgorithm",
    "CMAES", "SimulatedAnnealing",
    # Problems
    "Problem", "ContinuousProblem", "CombinatorialProblem",
    "Sphere", "Rastrigin", "Rosenbrock", "TSP", "Knapsack",
    "Ackley", "Griewank", "Schwefel", "Michalewicz", "Zakharov",
    "ZDT1", "ZDT2",
    # Operators
    "tournament_selection", "roulette_selection", "rank_selection", "SUS_selection",
    "uniform_crossover", "one_point_crossover", "two_point_crossover",
    "blx_alpha_crossover", "sbx_crossover", "order_crossover", "cycle_crossover", "pmx_crossover",
    "gaussian_mutation", "polynomial_mutation", "bit_flip_mutation",
    "swap_mutation", "random_reset_mutation", "inversion_mutation", "insert_mutation", "scramble_mutation",
    # Utils
    "Statistics", "ascii_convergence_plot", "ascii_pareto_front", "diversity_plot",
    "MaxGenerations", "FitnessThreshold", "Stagnation", "TimeLimit", "Convergence",
    "AdaptiveMutationRate", "AdaptiveInertia",
    "get_logger", "setup_logging",
    # Results & experiments
    "Result", "Experiment", "parameter_sweep",
    # Indicators
    "hypervolume", "generational_distance", "inverted_generational_distance",
    "spacing", "spread",
]