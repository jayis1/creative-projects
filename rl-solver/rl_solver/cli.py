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
    QLearner, SARSALearner, ExpectedSARSALearner, DoubleQLearner, MonteCarloLearner,
    NStepSARSALearner, NStepTreeBackupLearner, SARSALambdaLearner, QLambdaLearner,
    make_russell_norvig_grid, make_cliff_walking, make_frozen_lake, make_chain,
    make_taxi, make_bridge_walking, make_random_mdp,
    PRESETS,
    simulate_policy, compare_planners, compare_learners,
    render_value_heatmap, render_policy_grid, render_q_table, render_learning_curve,
    serialize_value_function, serialize_policy,
)


def _get_mdp(args) -> MDP:
    if args.preset:
        factory = PRESETS[args.preset]
        kwargs = {}
        if args.gamma is not None:
            kwargs["gamma"] = args.gamma
        if args.slip is not None and args.preset in ("russell_norvig", "frozen_lake"):
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
    if args.method == "value":
        V, pi, info = value_iteration(mdp, theta=args.theta)
    elif args.method == "policy":
        V, pi, info = policy_iteration(mdp, theta=args.theta)
    elif args.method == "modified":
        V, pi, info = modified_policy_iteration(mdp, theta=args.theta)
    else:
        print(f"Unknown method: {args.method}", file=sys.stderr)
        sys.exit(1)
    print(f"Method: {args.method}")
    print(f"Iterations: {info['iterations']}")
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
            "iterations": info["iterations"],
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
    for name in PRESETS:
        print(f"  {name}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="rl-solver", description="MDP & RL toolkit")
    sub = p.add_subparsers(dest="command", required=True)

    def add_mdp_args(sp):
        sp.add_argument("--preset", choices=list(PRESETS.keys()), help="Use a preset MDP")
        sp.add_argument("--grid", help="Custom gridworld: ROWS,COLS")
        sp.add_argument("--gamma", type=float, default=None, help="Discount factor")
        sp.add_argument("--slip", type=float, default=None, help="Slip probability")
        sp.add_argument("--seed", type=int, default=None, help="Random seed")

    # --- plan ---
    sp_plan = sub.add_parser("plan", help="Solve MDP with dynamic programming")
    add_mdp_args(sp_plan)
    sp_plan.add_argument("--method", choices=["value", "policy", "modified"], default="value")
    sp_plan.add_argument("--theta", type=float, default=1e-8, help="Convergence threshold")
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
                                   "nstep_sarsa", "nstep_tree", "sarsa_lambda", "q_lambda"],
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

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())