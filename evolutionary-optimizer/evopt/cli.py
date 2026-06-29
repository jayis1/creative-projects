#!/usr/bin/env python3
"""EvOpt CLI — command-line interface for the evolutionary optimization toolkit.

Usage:
    python -m evopt.cli solve --algorithm ga --problem sphere --dims 3 --generations 100
    python -m evopt.cli solve --algorithm de --problem rastrigin --dims 5 --generations 200
    python -m evopt.cli solve --algorithm pso --problem rosenbrock --dims 3
    python -m evopt.cli solve --algorithm es --problem sphere --dims 2 --generations 50
    python -m evopt.cli solve --algorithm nsga2 --problem zdt1 --dims 5 --generations 50
    python -m evopt.cli solve --algorithm cmaes --problem sphere --dims 3 --generations 50
    python -m evopt.cli solve --algorithm sa --problem rastrigin --dims 3 --generations 200
    python -m evopt.cli solve --algorithm ga --problem tsp --cities 15 --generations 200
    python -m evopt.cli solve --algorithm ga --problem knapsack --items 20 --generations 100
    python -m evopt.cli solve --algorithm island --problem rastrigin --dims 3 --generations 100
    python -m evopt.cli solve --algorithm memetic --problem ackley --dims 2 --generations 50
    python -m evopt.cli benchmark --problem rastrigin --dims 3 --generations 50
    python -m evopt.cli compare --problem rastrigin --dims 5 --generations 100
    python -m evopt.cli plot --algorithm ga --problem sphere --dims 3 --generations 50
    python -m evopt.cli config run config.yaml
    python -m evopt.cli config template --algorithm ga --problem sphere --output config.yaml
    python -m evopt.cli list
"""

import argparse
import sys
import json
import time

from . import (
    GeneticAlgorithm, EvolutionStrategy, DifferentialEvolution,
    ParticleSwarmOptimizer, NSGA2, IslandModelGA, MemeticAlgorithm,
    CMAES, SimulatedAnnealing,
    Sphere, Rastrigin, Rosenbrock, TSP, Knapsack,
    Ackley, Griewank, Schwefel, Michalewicz, Zakharov,
)


SINGLE_OBJECTIVE_PROBLEMS = {
    'sphere': lambda **kw: Sphere(dims=kw.get('dims', 2)),
    'rastrigin': lambda **kw: Rastrigin(dims=kw.get('dims', 2)),
    'rosenbrock': lambda **kw: Rosenbrock(dims=kw.get('dims', 2)),
    'ackley': lambda **kw: Ackley(dims=kw.get('dims', 2)),
    'griewank': lambda **kw: Griewank(dims=kw.get('dims', 2)),
    'schwefel': lambda **kw: Schwefel(dims=kw.get('dims', 2)),
    'michalewicz': lambda **kw: Michalewicz(dims=kw.get('dims', 2)),
    'zakharov': lambda **kw: Zakharov(dims=kw.get('dims', 2)),
    'tsp': lambda **kw: TSP.random_cities(n=kw.get('cities', 15), seed=kw.get('seed', 42)),
    'knapsack': lambda **kw: Knapsack.random_items(n=kw.get('items', 20), seed=kw.get('seed', 42))[0],
}

MULTI_OBJECTIVE_PROBLEMS = {'zdt1', 'zdt2'}

ALGORITHMS = ['ga', 'es', 'de', 'pso', 'nsga2', 'island', 'memetic', 'cmaes', 'sa']


def get_multi_problem(name, **kw):
    from .problems.multi_objective import ZDT1, ZDT2
    if name == 'zdt1':
        return ZDT1(dims=kw.get('dims', 10))
    elif name == 'zdt2':
        return ZDT2(dims=kw.get('dims', 10))
    raise ValueError(f"Unknown multi-objective problem: {name}")


def create_algorithm(alg_name, problem, pop, gens, seed, verbose, extra_params=None):
    """Create and configure an algorithm instance."""
    extra_params = extra_params or {}
    if alg_name == 'ga':
        return GeneticAlgorithm(problem, population_size=pop, max_generations=gens, seed=seed, verbose=verbose, **extra_params)
    elif alg_name == 'de':
        return DifferentialEvolution(problem, population_size=pop, max_generations=gens, seed=seed, verbose=verbose, **extra_params)
    elif alg_name == 'es':
        mu = min(pop // 3, pop)
        return EvolutionStrategy(problem, mu=mu, lam=pop, max_generations=gens, seed=seed, verbose=verbose, **extra_params)
    elif alg_name == 'pso':
        return ParticleSwarmOptimizer(problem, swarm_size=pop, max_generations=gens, seed=seed, verbose=verbose, **extra_params)
    elif alg_name == 'nsga2':
        return NSGA2(problem, population_size=pop, max_generations=gens, seed=seed, verbose=verbose, **extra_params)
    elif alg_name == 'island':
        num_islands = extra_params.pop('num_islands', 4)
        return IslandModelGA(problem, num_islands=num_islands, island_size=max(pop // num_islands, 10),
                             max_generations=gens, seed=seed, verbose=verbose, **extra_params)
    elif alg_name == 'memetic':
        return MemeticAlgorithm(problem, population_size=pop, max_generations=gens, seed=seed, verbose=verbose, **extra_params)
    elif alg_name == 'cmaes':
        return CMAES(problem, population_size=pop if pop != 50 else None, max_generations=gens, seed=seed, verbose=verbose, **extra_params)
    elif alg_name == 'sa':
        return SimulatedAnnealing(problem, max_generations=gens, seed=seed, verbose=verbose, **extra_params)
    else:
        raise ValueError(f"Unknown algorithm: {alg_name}")


def solve_single(algorithm_name, problem_name, args):
    """Solve a problem with the given algorithm."""
    if problem_name in SINGLE_OBJECTIVE_PROBLEMS:
        problem = SINGLE_OBJECTIVE_PROBLEMS[problem_name](dims=args.dims, cities=args.cities,
                                                            items=args.items, seed=args.seed)
    elif problem_name in MULTI_OBJECTIVE_PROBLEMS:
        problem = get_multi_problem(problem_name, dims=args.dims)
    else:
        print(f"Unknown problem: {problem_name}", file=sys.stderr)
        sys.exit(1)

    t0 = time.time()
    algo = create_algorithm(algorithm_name, problem, args.population, args.generations,
                            args.seed, args.verbose)

    if algorithm_name == 'nsga2':
        algo.run()
        elapsed = time.time() - t0
        pareto = algo.pareto_front
        print(f"NSGA-II on {problem_name}: {elapsed:.3f}s")
        print(f"Pareto front size: {len(pareto)}")

        # Compute hypervolume if numpy available
        if pareto and args.json:
            try:
                from .indicators import hypervolume
                objs = [ind.metadata.get('objectives', []) for ind in pareto]
                if objs and len(objs[0]) == 2:
                    ref = [max(o[0] for o in objs) + 1, max(o[1] for o in objs) + 1]
                    hv = hypervolume(objs, ref)
                    print(f"Hypervolume: {hv:.6f}")
            except Exception:
                pass

            data = {
                'algorithm': 'nsga2',
                'problem': problem_name,
                'time_seconds': elapsed,
                'generations': args.generations,
                'pareto_front_size': len(pareto),
                'pareto_front': [ind.metadata.get('objectives', []) for ind in pareto],
            }
            print(json.dumps(data, indent=2))

        if args.plot:
            from .utils.visualization import ascii_pareto_front
            print()
            print(ascii_pareto_front(pareto, title=f"Pareto Front — NSGA-II on {problem_name}"))
        return

    best = algo.run()
    elapsed = time.time() - t0

    print(f"{algorithm_name.upper()} on {problem_name}: {elapsed:.3f}s, {args.generations} generations")
    print(f"Best fitness: {best.fitness:.6f}")
    print(f"Best genome: {[round(float(x), 6) if isinstance(x, (int, float)) or hasattr(x, '__float__') else x for x in best.genome]}")

    if args.plot:
        from .utils.visualization import ascii_convergence_plot
        print()
        print(ascii_convergence_plot(algo.history, title=f"Convergence — {algorithm_name.upper()} on {problem_name}"))

    if args.json:
        data = {
            'algorithm': algorithm_name,
            'problem': problem_name,
            'best_fitness': best.fitness,
            'best_genome': best.genome,
            'time_seconds': elapsed,
            'generations': args.generations,
            'statistics': algo.statistics.summary(),
        }
        print(json.dumps(data, indent=2, default=str))

    # Save result if --output specified
    if args.output:
        from .results import Result
        result = Result.from_algorithm(algo, problem_name=problem_name,
                                        algorithm_name=algorithm_name, time_seconds=elapsed)
        if args.output.endswith('.json'):
            result.to_json(args.output)
            print(f"Result saved to {args.output}")
        elif args.output.endswith('.csv'):
            result.to_csv(args.output)
            print(f"History saved to {args.output}")


def benchmark(args):
    """Run all single-objective algorithms on the same problem for comparison."""
    problem_name = args.problem
    gens = args.generations
    dims = args.dims
    seed = args.seed
    pop = args.population

    if problem_name in MULTI_OBJECTIVE_PROBLEMS:
        print("Benchmark not supported for multi-objective problems in this mode.")
        return
    if problem_name not in SINGLE_OBJECTIVE_PROBLEMS:
        print(f"Unknown problem: {problem_name}", file=sys.stderr)
        sys.exit(1)

    results = []
    for alg_name in ['ga', 'es', 'de', 'pso', 'island', 'memetic', 'cmaes', 'sa']:
        problem = SINGLE_OBJECTIVE_PROBLEMS[problem_name](dims=dims, seed=seed)
        t0 = time.time()
        try:
            algo = create_algorithm(alg_name, problem, pop, gens, seed, False)
            best = algo.run()
            elapsed = time.time() - t0
            results.append((alg_name, best.fitness, elapsed))
            print(f"  {alg_name.upper():8s}: fitness={best.fitness:12.6f}  time={elapsed:.3f}s")
        except Exception as e:
            elapsed = time.time() - t0
            print(f"  {alg_name.upper():8s}: FAILED ({e})  time={elapsed:.3f}s")

    print("\nRanking (best fitness):")
    results.sort(key=lambda x: x[1])
    for i, (name, fit, t) in enumerate(results):
        print(f"  {i+1}. {name.upper():8s}: {fit:12.6f} ({t:.3f}s)")


def plot_command(args):
    """Run an algorithm and display convergence + diversity plots."""
    if args.problem in MULTI_OBJECTIVE_PROBLEMS:
        # Pareto front plot
        problem = get_multi_problem(args.problem, dims=args.dims)
        algo = NSGA2(problem, population_size=args.population, max_generations=args.generations,
                     seed=args.seed, verbose=False)
        algo.run()
        from .utils.visualization import ascii_pareto_front
        print(ascii_pareto_front(algo.pareto_front, title=f"Pareto Front — NSGA-II on {args.problem}"))
        return

    problem = SINGLE_OBJECTIVE_PROBLEMS[args.problem](dims=args.dims, seed=args.seed)
    algo = create_algorithm(args.algorithm, problem, args.population, args.generations, args.seed, False)
    algo.run()

    from .utils.visualization import ascii_convergence_plot, diversity_plot
    print(ascii_convergence_plot(algo.history, title=f"Convergence — {args.algorithm.upper()} on {args.problem}"))
    print()
    print(diversity_plot(algo.history, title=f"Diversity — {args.algorithm.upper()} on {args.problem}"))


def list_problems(args):
    """List available problems and algorithms."""
    print("Single-objective problems:")
    for name in sorted(SINGLE_OBJECTIVE_PROBLEMS.keys()):
        print(f"  - {name}")
    print("\nMulti-objective problems:")
    for name in sorted(MULTI_OBJECTIVE_PROBLEMS):
        print(f"  - {name}")
    print("\nAlgorithms:")
    for name in ALGORITHMS:
        print(f"  - {name}")
    print("\nIndicators (multi-objective):")
    print("  - hypervolume, igd, gd, spacing, spread")
    print("\nCommands:")
    print("  - solve, benchmark, plot, list, config, batch")


def config_command(args):
    """Run from or generate a config file."""
    from .config import load_config, save_config, build_from_config, default_config

    if args.config_action == 'run':
        if not args.config_file:
            print("Error: --config-file required for 'config run'", file=sys.stderr)
            sys.exit(1)
        cfg = load_config(args.config_file)
        problem, algo = build_from_config(cfg)
        t0 = time.time()
        if isinstance(algo, NSGA2):
            algo.run()
            elapsed = time.time() - t0
            pareto = algo.pareto_front
            print(f"NSGA-II: {elapsed:.3f}s, Pareto front size: {len(pareto)}")
            if args.json:
                data = {
                    'config': cfg,
                    'pareto_front_size': len(pareto),
                    'time_seconds': elapsed,
                }
                print(json.dumps(data, indent=2, default=str))
        else:
            best = algo.run()
            elapsed = time.time() - t0
            print(f"{algo.__class__.__name__}: {elapsed:.3f}s")
            print(f"Best fitness: {best.fitness:.6f}")
            print(f"Best genome: {best.genome}")
            if args.json:
                data = {
                    'config': cfg,
                    'best_fitness': best.fitness,
                    'best_genome': best.genome,
                    'time_seconds': elapsed,
                }
                print(json.dumps(data, indent=2, default=str))
    elif args.config_action == 'template':
        alg = args.algorithm or 'ga'
        prob = args.problem or 'sphere'
        cfg = default_config(alg, prob, population_size=50, max_generations=100)
        if args.dims:
            cfg['problem']['params']['dims'] = args.dims
        if args.output:
            save_config(cfg, args.output)
            print(f"Template config saved to {args.output}")
        else:
            print(json.dumps(cfg, indent=2, default=str))
    elif args.config_action == 'list':
        from .config import _ensure_registries, _ALGORITHM_REGISTRY, _PROBLEM_REGISTRY, _CALLBACK_REGISTRY
        _ensure_registries()
        print("Available algorithms:")
        for name in sorted(_ALGORITHM_REGISTRY):
            print(f"  - {name}")
        print("\nAvailable problems:")
        for name in sorted(_PROBLEM_REGISTRY):
            print(f"  - {name}")
        print("\nAvailable callbacks:")
        for name in sorted(_CALLBACK_REGISTRY):
            print(f"  - {name}")


def batch_command(args):
    """Run a batch experiment comparing algorithms on a problem."""
    from .results import Experiment

    exp = Experiment(name=f"batch_{args.problem}")
    problem_name = args.problem
    for alg in args.algorithms.split(','):
        alg = alg.strip().lower()
        if alg in ALGORITHMS:
            exp.add(alg, problem_name, {
                "dims": args.dims,
                "population_size": args.population,
                "max_generations": args.generations,
            }, seed=args.seed)
        else:
            print(f"Warning: unknown algorithm '{alg}', skipping")

    exp.run(repeats=args.repeats, verbose=args.verbose)
    exp.report()
    if args.output:
        exp.save_results(args.output)
        print(f"\nResults saved to {args.output}/")


def main():
    parser = argparse.ArgumentParser(
        prog='evopt',
        description='Evolutionary optimization toolkit CLI — 9 algorithms, 12 problems, multi-objective support'
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
    solve_parser.add_argument('--plot', action='store_true', help='Show ASCII convergence plot')
    solve_parser.add_argument('--output', type=str, default=None,
                               help='Save result to file (.json or .csv)')

    # Benchmark command
    bench_parser = subparsers.add_parser('benchmark', help='Benchmark all algorithms on a problem')
    bench_parser.add_argument('--problem', type=str, required=True, help='Problem to benchmark')
    bench_parser.add_argument('--dims', type=int, default=3, help='Problem dimensions')
    bench_parser.add_argument('--population', type=int, default=50, help='Population size')
    bench_parser.add_argument('--generations', type=int, default=50, help='Max generations')
    bench_parser.add_argument('--seed', type=int, default=42, help='Random seed')

    # Plot command
    plot_parser = subparsers.add_parser('plot', help='Run algorithm and display plots')
    plot_parser.add_argument('--algorithm', type=str, default='ga', choices=ALGORITHMS,
                              help='Algorithm to use')
    plot_parser.add_argument('--problem', type=str, required=True, help='Problem to solve')
    plot_parser.add_argument('--dims', type=int, default=2, help='Problem dimensions')
    plot_parser.add_argument('--population', type=int, default=50, help='Population size')
    plot_parser.add_argument('--generations', type=int, default=50, help='Max generations')
    plot_parser.add_argument('--seed', type=int, default=42, help='Random seed')

    # Config command
    config_parser = subparsers.add_parser('config', help='Run from or generate config files')
    config_sub = config_parser.add_subparsers(dest='config_action', required=True)
    config_run = config_sub.add_parser('run', help='Run an optimization from a config file')
    config_run.add_argument('--config-file', type=str, required=True, help='Path to config file (YAML/JSON)')
    config_run.add_argument('--json', action='store_true', help='Output JSON')
    config_template = config_sub.add_parser('template', help='Generate a template config file')
    config_template.add_argument('--algorithm', type=str, default='ga', help='Algorithm name')
    config_template.add_argument('--problem', type=str, default='sphere', help='Problem name')
    config_template.add_argument('--dims', type=int, default=2, help='Problem dimensions')
    config_template.add_argument('--output', type=str, default=None, help='Output file path')
    config_sub.add_parser('list', help='List available algorithms, problems, and callbacks for config files')

    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Run a batch experiment comparing algorithms')
    batch_parser.add_argument('--problem', type=str, required=True, help='Problem to solve')
    batch_parser.add_argument('--algorithms', type=str, default='ga,de,pso',
                               help='Comma-separated list of algorithms')
    batch_parser.add_argument('--dims', type=int, default=3, help='Problem dimensions')
    batch_parser.add_argument('--population', type=int, default=50, help='Population size')
    batch_parser.add_argument('--generations', type=int, default=50, help='Max generations')
    batch_parser.add_argument('--repeats', type=int, default=3, help='Independent runs per algorithm')
    batch_parser.add_argument('--seed', type=int, default=42, help='Base random seed')
    batch_parser.add_argument('--verbose', action='store_true', help='Verbose output')
    batch_parser.add_argument('--output', type=str, default=None, help='Directory to save results')

    # List command
    subparsers.add_parser('list', help='List available problems and algorithms')

    args = parser.parse_args()

    if args.command == 'solve':
        solve_single(args.algorithm, args.problem, args)
    elif args.command == 'benchmark':
        benchmark(args)
    elif args.command == 'plot':
        plot_command(args)
    elif args.command == 'list':
        list_problems(args)
    elif args.command == 'config':
        config_command(args)
    elif args.command == 'batch':
        batch_command(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()