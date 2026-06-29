#!/usr/bin/env python3
"""EvOpt CLI — command-line interface for the evolutionary optimization toolkit.

Usage:
    python -m evopt.cli solve --algorithm ga --problem sphere --dims 3 --generations 100
    python -m evopt.cli solve --algorithm de --problem rastrigin --dims 5 --generations 200
    python -m evopt.cli solve --algorithm pso --problem rosenbrock --dims 3
    python -m evopt.cli solve --algorithm es --problem sphere --dims 2 --generations 50
    python -m evopt.cli solve --algorithm nsga2 --problem zdt1 --dims 5 --generations 50
    python -m evopt.cli solve --algorithm ga --problem tsp --cities 15 --generations 200
    python -m evopt.cli solve --algorithm ga --problem knapsack --items 20 --generations 100
    python -m evopt.cli benchmark --algorithm all --problem sphere --dims 3 --generations 50
    python -m evopt.cli compare --problem rastrigin --dims 5 --generations 100
"""

import argparse
import sys
import json
import time

from . import (
    GeneticAlgorithm, EvolutionStrategy, DifferentialEvolution,
    ParticleSwarmOptimizer, NSGA2, Sphere, Rastrigin, Rosenbrock, TSP, Knapsack,
)


PROBLEMS_SINGLE = {
    'sphere': lambda **kw: Sphere(dims=kw.get('dims', 2)),
    'rastrigin': lambda **kw: Rastrigin(dims=kw.get('dims', 2)),
    'rosenbrock': lambda **kw: Rosenbrock(dims=kw.get('dims', 2)),
    'tsp': lambda **kw: TSP.random_cities(n=kw.get('cities', 15), seed=kw.get('seed', 42)),
    'knapsack': lambda **kw: Knapsack.random_items(n=kw.get('items', 20), seed=kw.get('seed', 42))[0],
}

PROBLEMS_MULTI = {
    'zdt1': None,  # lazy import
    'zdt2': None,
}

ALGORITHMS = ['ga', 'es', 'de', 'pso', 'nsga2']


def get_multi_problem(name, **kw):
    from .problems.multi_objective import ZDT1, ZDT2
    if name == 'zdt1':
        return ZDT1(dims=kw.get('dims', 10))
    elif name == 'zdt2':
        return ZDT2(dims=kw.get('dims', 10))
    raise ValueError(f"Unknown multi-objective problem: {name}")


def solve_single(algorithm_name, problem_name, args):
    """Solve a single-objective problem with the given algorithm."""
    if problem_name in PROBLEMS_SINGLE:
        problem = PROBLEMS_SINGLE[problem_name](dims=args.dims, cities=args.cities,
                                                  items=args.items, seed=args.seed)
    elif problem_name in PROBLEMS_MULTI:
        problem = get_multi_problem(problem_name, dims=args.dims)
    else:
        print(f"Unknown problem: {problem_name}", file=sys.stderr)
        sys.exit(1)

    pop = args.population
    gens = args.generations
    seed = args.seed

    t0 = time.time()
    if algorithm_name == 'ga':
        algo = GeneticAlgorithm(problem, population_size=pop, max_generations=gens, seed=seed, verbose=args.verbose)
    elif algorithm_name == 'de':
        algo = DifferentialEvolution(problem, population_size=pop, max_generations=gens, seed=seed, verbose=args.verbose)
    elif algorithm_name == 'es':
        mu = min(pop // 3, pop)
        lam = pop
        algo = EvolutionStrategy(problem, mu=mu, lam=lam, max_generations=gens, seed=seed, verbose=args.verbose)
    elif algorithm_name == 'pso':
        algo = ParticleSwarmOptimizer(problem, swarm_size=pop, max_generations=gens, seed=seed, verbose=args.verbose)
    elif algorithm_name == 'nsga2':
        algo = NSGA2(problem, population_size=pop, max_generations=gens, seed=seed, verbose=args.verbose)
        best = algo.run()
        elapsed = time.time() - t0
        pareto = algo.pareto_front
        print(f"NSGA-II on {problem_name}: {elapsed:.3f}s")
        print(f"Pareto front size: {len(pareto)}")
        if pareto and args.json:
            data = {
                'algorithm': 'nsga2',
                'problem': problem_name,
                'time_seconds': elapsed,
                'generations': gens,
                'pareto_front_size': len(pareto),
                'pareto_front': [ind.metadata.get('objectives', []) for ind in pareto],
            }
            print(json.dumps(data, indent=2))
        return

    best = algo.run()
    elapsed = time.time() - t0

    print(f"{algorithm_name.upper()} on {problem_name}: {elapsed:.3f}s, {gens} generations")
    print(f"Best fitness: {best.fitness:.6f}")
    print(f"Best genome: {[round(x, 6) if isinstance(x, float) else x for x in best.genome]}")

    if args.json:
        data = {
            'algorithm': algorithm_name,
            'problem': problem_name,
            'best_fitness': best.fitness,
            'best_genome': best.genome,
            'time_seconds': elapsed,
            'generations': gens,
            'statistics': algo.statistics.summary(),
        }
        print(json.dumps(data, indent=2, default=str))


def benchmark(args):
    """Run all algorithms on the same problem for comparison."""
    problem_name = args.problem
    gens = args.generations
    dims = args.dims
    seed = args.seed
    pop = args.population

    if problem_name in PROBLEMS_MULTI:
        print("Benchmark not supported for multi-objective problems in this mode.")
        return

    results = []
    for alg_name in ALGORITHMS:
        if alg_name == 'nsga2':
            continue
        problem = PROBLEMS_SINGLE[problem_name](dims=dims, seed=seed)
        t0 = time.time()
        if alg_name == 'ga':
            algo = GeneticAlgorithm(problem, population_size=pop, max_generations=gens, seed=seed)
        elif alg_name == 'de':
            algo = DifferentialEvolution(problem, population_size=pop, max_generations=gens, seed=seed)
        elif alg_name == 'es':
            algo = EvolutionStrategy(problem, mu=pop//3, lam=pop, max_generations=gens, seed=seed)
        elif alg_name == 'pso':
            algo = ParticleSwarmOptimizer(problem, swarm_size=pop, max_generations=gens, seed=seed)
        best = algo.run()
        elapsed = time.time() - t0
        results.append((alg_name, best.fitness, elapsed))
        print(f"  {alg_name.upper():6s}: fitness={best.fitness:12.6f}  time={elapsed:.3f}s")

    print("\nRanking (best fitness):")
    results.sort(key=lambda x: x[1])
    for i, (name, fit, t) in enumerate(results):
        print(f"  {i+1}. {name.upper():6s}: {fit:12.6f} ({t:.3f}s)")


def list_problems(args):
    """List available problems and algorithms."""
    print("Single-objective problems:")
    for name in sorted(PROBLEMS_SINGLE.keys()):
        print(f"  - {name}")
    print("\nMulti-objective problems:")
    for name in sorted(PROBLEMS_MULTI.keys()):
        print(f"  - {name}")
    print("\nAlgorithms:")
    for name in ALGORITHMS:
        print(f"  - {name}")


def main():
    parser = argparse.ArgumentParser(
        prog='evopt',
        description='Evolutionary optimization toolkit CLI'
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Solve command
    solve_parser = subparsers.add_parser('solve', help='Solve a problem with an algorithm')
    solve_parser.add_argument('--algorithm', type=str, required=True, choices=ALGORITHMS,
                               help='Algorithm to use')
    solve_parser.add_argument('--problem', type=str, required=True,
                               help='Problem to solve')
    solve_parser.add_argument('--dims', type=int, default=2, help='Problem dimensions')
    solve_parser.add_argument('--population', type=int, default=50, help='Population size')
    solve_parser.add_argument('--generations', type=int, default=100, help='Max generations')
    solve_parser.add_argument('--cities', type=int, default=15, help='Number of cities (TSP)')
    solve_parser.add_argument('--items', type=int, default=20, help='Number of items (Knapsack)')
    solve_parser.add_argument('--seed', type=int, default=42, help='Random seed')
    solve_parser.add_argument('--verbose', action='store_true', help='Verbose output')
    solve_parser.add_argument('--json', action='store_true', help='Output JSON')

    # Benchmark command
    bench_parser = subparsers.add_parser('benchmark', help='Benchmark all algorithms on a problem')
    bench_parser.add_argument('--problem', type=str, required=True, help='Problem to benchmark')
    bench_parser.add_argument('--dims', type=int, default=3, help='Problem dimensions')
    bench_parser.add_argument('--population', type=int, default=50, help='Population size')
    bench_parser.add_argument('--generations', type=int, default=50, help='Max generations')
    bench_parser.add_argument('--seed', type=int, default=42, help='Random seed')

    # List command
    subparsers.add_parser('list', help='List available problems and algorithms')

    args = parser.parse_args()

    if args.command == 'solve':
        solve_single(args.algorithm, args.problem, args)
    elif args.command == 'benchmark':
        benchmark(args)
    elif args.command == 'list':
        list_problems(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()