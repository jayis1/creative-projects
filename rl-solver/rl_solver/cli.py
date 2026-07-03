"""Command-line interface for rl-solver."""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from . import (
    MDP, GridWorld, Policy,
    value_iteration, policy_iteration, modified_policy_iteration,
    policy_evaluation_iterative, q_values,
    linear_programming_solve, gauss_seidel_value_iteration,
    prioritized_sweeping, rtdp,
    QLearner, SARSALearner, ExpectedSARSALearner, DoubleQLearner, MonteCarloLearner,
    NStepSARSALearner, NStepTreeBackupLearner, SARSALambdaLearner, QLambdaLearner,
    DynaQLearner, RMaxLearner, BoltzmannQLearner,
    make_russell_norvig_grid, make_cliff_walking, make_frozen_lake, make_chain,
    make_taxi, make_bridge_walking, make_random_mdp,
    make_maze, make_windy_gridworld, make_blackjack, make_dice_game, make_pendulum,
    PRESETS, EXTENDED_PRESETS,
    simulate_policy, compare_planners, compare_learners,
    render_value_heatmap, render_policy_grid, render_q_table, render_learning_curve,
    serialize_value_function, serialize_policy,
)


def _get_mdp(args) -> MDP:
    preset_registry = EXTENDED_PRESETS
    if args.preset:
        factory = preset_registry[args.preset]
        kwargs = {}
        if args.gamma is not None:
            kwargs["gamma"] = args.gamma
        if args.slip is not None and args.preset in ("russell_norvig", "frozen_lake", "maze"):
            kwargs["slip"] = args.slip
        return factory(**kwargs)
    elif args.grid:
        parts = args.grid.split(",")
        rows, cols = int(parts[0]), int(parts[1])
        return GridWorld(rows=rows, cols=cols, gamma=args.gamma or 0.99).to_mdp()
    else:
        return make_russell_norvig_grid()


def cmd_plan(args) -> None:
    mdp = _get_mdp(args)
    method_map = {
        "value": value_iteration,
        "policy": policy_iteration,
        "modified": modified_policy_iteration,
        "lp": linear_programming_solve,
        "gauss_seidel": gauss_seidel_value_iteration,
        "prioritized": prioritized_sweeping,
        "rtdp": rtdp,
    }
    fn = method_map[args.method]
    if args.method == "rtdp":
        V, pi, info = fn(mdp, n_trials=args.trials, seed=args.seed)
    elif args.method == "lp":
        V, pi, info = fn(mdp)
    else:
        V, pi, info = fn(mdp, theta=args.theta)
    print(f"Method: {args.method}")
    print(f"Iterations: {info.get('iterations', info.get('trials', 'N/A'))}")
    print(f"Time: {info['time']*1000:.2f} ms")
    print(f"States: {len(mdp.states)}, Actions: {len(mdp.actions)}")
    print()
    if args.show_values:
        print("Optimal state values (heatmap):")
        print(render_value_heatmap(mdp, V))
        print()
    if args.show_policy:
        print("Optimal policy (grid):")
        print(render_policy_grid(mdp, pi))
        print()
        for s in mdp.states:
            a = pi[s]
            print(f"  {s}: {a}")
    if args.json:
        out = {
            "method": args.method,
            "iterations": info.get("iterations", info.get("trials")),
            "time_ms": info["time"] * 1000,
            "values": {str(s): V[s] for s in mdp.states},
            "policy": pi.to_dict(),
        }
        print(json.dumps(out, indent=2))
    if args.save_values:
        serialize_value_function(V, args.save_values)
        print(f"Values saved to {args.save_values}")
    if args.save_policy:
        serialize_policy(pi, args.save_policy)
        print(f"Policy saved to {args.save_policy}")


def cmd_learn(args) -> None:
    mdp = _get_mdp(args)
    learner_classes = {
        "q": QLearner, "sarsa": SARSALearner, "expected_sarsa": ExpectedSARSALearner,
        "double_q": DoubleQLearner, "mc": MonteCarloLearner,
        "nstep_sarsa": NStepSARSALearner, "nstep_tree": NStepTreeBackupLearner,
        "sarsa_lambda": SARSALambdaLearner, "q_lambda": QLambdaLearner,
        "dyna_q": DynaQLearner, "rmax": RMaxLearner, "boltzmann_q": BoltzmannQLearner,
    }
    cls = learner_classes[args.algo]
    kwargs = dict(
        alpha=args.alpha, epsilon=args.epsilon, epsilon_decay=args.decay,
        epsilon_min=args.eps_min, seed=args.seed,
    )
    if args.algo == "mc":
        kwargs["first_visit"] = not args.every_visit
    if args.algo in ("nstep_sarsa", "nstep_tree"):
        kwargs["n"] = args.n_step
    if args.algo in ("sarsa_lambda", "q_lambda"):
        kwargs["lam"] = args.lam
        kwargs["replace_traces"] = args.replace_traces
    if args.algo == "dyna_q":
        kwargs["n_planning"] = args.n_planning
    if args.algo == "rmax":
        kwargs["r_max"] = args.r_max
        kwargs["threshold"] = args.threshold
    if args.algo == "boltzmann_q":
        kwargs["temperature"] = args.temperature
        kwargs["temp_decay"] = args.temp_decay
    learner = cls(mdp, **kwargs)
    stats = learner.train(n_episodes=args.episodes, max_steps=args.max_steps, verbose=args.verbose)
    print(f"Algorithm: {args.algo}")
    print(f"Episodes: {stats['episodes']}")
    print(f"Steps: {stats['steps']}")
    print(f"Mean reward: {stats['mean_reward']:.4f}")
    print(f"Mean length: {stats['mean_length']:.2f}")
    if args.simulate:
        pi = learner.greedy_policy()
        sim = simulate_policy(mdp, pi, n_episodes=args.sim_episodes, seed=args.seed)
        print(f"Greedy policy sim — mean return: {sim['mean_return']:.4f}, "
              f"success: {sim['success_rate']:.2%}")
    if args.show_q:
        print("\nLearned Q-values:")
        print(render_q_table(learner.Q))
    if args.show_curve:
        print()
        print(render_learning_curve(learner.episode_rewards, title=f"{args.algo} learning curve"))


def cmd_compare(args) -> None:
    mdp = _get_mdp(args)
    if args.mode == "planners":
        results = compare_planners(mdp, sim_episodes=args.sim_episodes, seed=args.seed)
        print(f"{'Planner':<25} {'Iters':>6} {'Time(ms)':>10} {'SimReturn':>12} {'Success':>10}")
        print("-" * 65)
        for r in results:
            print(f"{r['name']:<25} {r['iterations']:>6} {r['time']*1000:>10.2f} "
                  f"{r['sim_mean_return']:>12.4f} {r['sim_success_rate']:>10.2%}")
    elif args.mode == "learners":
        learners = [
            QLearner(mdp, seed=args.seed),
            SARSALearner(mdp, seed=args.seed),
            ExpectedSARSALearner(mdp, seed=args.seed),
            DoubleQLearner(mdp, seed=args.seed),
            MonteCarloLearner(mdp, seed=args.seed),
        ]
        results = compare_learners(mdp, learners, n_episodes=args.episodes,
                                   sim_episodes=args.sim_episodes, seed=args.seed)
        print(f"{'Learner':<25} {'TrainReward':>12} {'SimReturn':>12} {'Success':>10}")
        print("-" * 60)
        for r in results:
            print(f"{r['name']:<25} {r['train_stats']['mean_reward']:>12.4f} "
                  f"{r['sim_mean_return']:>12.4f} {r['sim_success_rate']:>10.2%}")


def cmd_info(args) -> None:
    mdp = _get_mdp(args)
    print(f"States: {len(mdp.states)}")
    print(f"Actions: {len(mdp.actions)}")
    print(f"Gamma: {mdp.gamma}")
    print(f"Terminal states: {len(mdp.terminal_states)}")
    print(f"Start state: {mdp.start_state}")
    print(f"Fingerprint: {mdp.fingerprint()}")
    if args.json:
        print(json.dumps(mdp.to_dict(), indent=2))


def cmd_list(_args) -> None:
    print("Available presets:")
    for name in EXTENDED_PRESETS:
        print(f"  {name}")


def cmd_config(args) -> None:
    """Run an experiment from a config file."""
    from .config import load_config, validate_config
    config = load_config(args.config_file)
    validate_config(config)
    env_cfg = config.get("env", {})
    preset = env_cfg.get("preset", "russell_norvig")
    factory = EXTENDED_PRESETS.get(preset, EXTENDED_PRESETS["russell_norvig"])
    mdp = factory(**{k: v for k, v in env_cfg.items() if k != "preset"})
    # Planner
    planner_cfg = config.get("planner")
    if planner_cfg:
        method = planner_cfg.get("method", "value_iteration")
        if method == "value_iteration":
            V, pi, info = value_iteration(mdp, theta=planner_cfg.get("theta", 1e-8))
        elif method == "policy_iteration":
            V, pi, info = policy_iteration(mdp, theta=planner_cfg.get("theta", 1e-8))
        elif method == "modified_policy_iteration":
            V, pi, info = modified_policy_iteration(mdp, theta=planner_cfg.get("theta", 1e-8))
        elif method == "gauss_seidel":
            V, pi, info = gauss_seidel_value_iteration(mdp, theta=planner_cfg.get("theta", 1e-8))
        elif method == "rtdp":
            V, pi, info = rtdp(mdp, n_trials=planner_cfg.get("trials", 1000),
                               seed=planner_cfg.get("seed"))
        else:
            V, pi, info = linear_programming_solve(mdp)
        print(f"Planner: {method}")
        print(f"  Iterations: {info.get('iterations', info.get('trials', 'N/A'))}")
        print(f"  Time: {info['time']*1000:.2f} ms")
        print(f"  V(start) = {V.get(mdp.start_state, 0):.6f}")
    # Learner
    learner_cfg = config.get("learner")
    if learner_cfg:
        algo = learner_cfg.get("algo", "q")
        learner_map = {
            "q": QLearner, "sarsa": SARSALearner, "expected_sarsa": ExpectedSARSALearner,
            "double_q": DoubleQLearner, "mc": MonteCarloLearner,
            "dyna_q": DynaQLearner, "boltzmann_q": BoltzmannQLearner,
        }
        cls = learner_map.get(algo, QLearner)
        kwargs = {k: v for k, v in learner_cfg.items() if k != "algo"}
        learner = cls(mdp, **kwargs)
        stats = learner.train(
            n_episodes=learner_cfg.get("episodes", 5000),
            max_steps=learner_cfg.get("max_steps", 1000),
            verbose=True,
        )
        print(f"\nLearner: {algo}")
        print(f"  Episodes: {stats['episodes']}")
        print(f"  Mean reward: {stats['mean_reward']:.4f}")
        sim_cfg = config.get("simulation", {})
        sim = simulate_policy(mdp, learner.greedy_policy(),
                              n_episodes=sim_cfg.get("episodes", 500),
                              seed=sim_cfg.get("seed"))
        print(f"  Sim return: {sim['mean_return']:.4f}, success: {sim['success_rate']:.2%}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="rl-solver", description="MDP & RL toolkit v3.0")
    sub = p.add_subparsers(dest="command", required=True)

    def add_mdp_args(sp):
        sp.add_argument("--preset", choices=list(EXTENDED_PRESETS.keys()),
                        help="Use a preset MDP")
        sp.add_argument("--grid", help="Custom gridworld: ROWS,COLS")
        sp.add_argument("--gamma", type=float, default=None, help="Discount factor")
        sp.add_argument("--slip", type=float, default=None, help="Slip probability")
        sp.add_argument("--seed", type=int, default=None, help="Random seed")

    # --- plan ---
    sp_plan = sub.add_parser("plan", help="Solve MDP with dynamic programming")
    add_mdp_args(sp_plan)
    sp_plan.add_argument("--method",
                         choices=["value", "policy", "modified", "lp",
                                  "gauss_seidel", "prioritized", "rtdp"],
                         default="value")
    sp_plan.add_argument("--theta", type=float, default=1e-8, help="Convergence threshold")
    sp_plan.add_argument("--trials", type=int, default=1000, help="Trials for RTDP")
    sp_plan.add_argument("--show-values", action="store_true")
    sp_plan.add_argument("--show-policy", action="store_true")
    sp_plan.add_argument("--json", action="store_true")
    sp_plan.add_argument("--save-values", type=str, default=None, help="Save V to JSON file")
    sp_plan.add_argument("--save-policy", type=str, default=None, help="Save policy to JSON file")
    sp_plan.set_defaults(func=cmd_plan)

    # --- learn ---
    sp_learn = sub.add_parser("learn", help="Learn with model-free RL")
    add_mdp_args(sp_learn)
    sp_learn.add_argument("--algo",
                          choices=["q", "sarsa", "expected_sarsa", "double_q", "mc",
                                   "nstep_sarsa", "nstep_tree", "sarsa_lambda", "q_lambda",
                                   "dyna_q", "rmax", "boltzmann_q"],
                          default="q")
    sp_learn.add_argument("--alpha", type=float, default=0.1)
    sp_learn.add_argument("--epsilon", type=float, default=0.1)
    sp_learn.add_argument("--decay", type=float, default=0.999)
    sp_learn.add_argument("--eps-min", type=float, default=0.01, dest="eps_min")
    sp_learn.add_argument("--episodes", type=int, default=5000)
    sp_learn.add_argument("--max-steps", type=int, default=1000, dest="max_steps")
    sp_learn.add_argument("--every-visit", action="store_true", help="MC every-visit (default first)")
    sp_learn.add_argument("--n-step", type=int, default=3, dest="n_step", help="n for n-step methods")
    sp_learn.add_argument("--lam", type=float, default=0.9, help="lambda for TD(λ) methods")
    sp_learn.add_argument("--replace-traces", action="store_true", dest="replace_traces")
    sp_learn.add_argument("--n-planning", type=int, default=10, dest="n_planning",
                          help="Planning steps for Dyna-Q")
    sp_learn.add_argument("--r-max", type=float, default=1.0, dest="r_max",
                          help="Max reward for R-Max")
    sp_learn.add_argument("--threshold", type=int, default=5,
                          help="Sample threshold for R-Max")
    sp_learn.add_argument("--temperature", type=float, default=1.0,
                          help="Initial temperature for Boltzmann")
    sp_learn.add_argument("--temp-decay", type=float, default=0.999, dest="temp_decay",
                          help="Temperature decay for Boltzmann")
    sp_learn.add_argument("--simulate", action="store_true")
    sp_learn.add_argument("--sim-episodes", type=int, default=500, dest="sim_episodes")
    sp_learn.add_argument("--show-q", action="store_true", dest="show_q")
    sp_learn.add_argument("--show-curve", action="store_true", dest="show_curve")
    sp_learn.add_argument("--verbose", action="store_true")
    sp_learn.set_defaults(func=cmd_learn)

    # --- compare ---
    sp_cmp = sub.add_parser("compare", help="Compare planners or learners")
    add_mdp_args(sp_cmp)
    sp_cmp.add_argument("--mode", choices=["planners", "learners"], default="planners")
    sp_cmp.add_argument("--episodes", type=int, default=5000)
    sp_cmp.add_argument("--sim-episodes", type=int, default=500, dest="sim_episodes")
    sp_cmp.set_defaults(func=cmd_compare)

    # --- info ---
    sp_info = sub.add_parser("info", help="Show MDP information")
    add_mdp_args(sp_info)
    sp_info.add_argument("--json", action="store_true")
    sp_info.set_defaults(func=cmd_info)

    # --- list ---
    sp_list = sub.add_parser("list", help="List preset MDPs")
    sp_list.set_defaults(func=cmd_list)

    # --- config ---
    sp_cfg = sub.add_parser("config", help="Run experiment from config file")
    sp_cfg.add_argument("config_file", help="Path to config file (JSON/TOML/YAML)")
    sp_cfg.set_defaults(func=cmd_config)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())