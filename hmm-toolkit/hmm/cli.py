"""Command-line interface for hmm-toolkit.

Subcommands:
  generate      Sample a sequence from an HMM model file
  viterbi       Decode most likely state path
  forward       Compute sequence log-likelihood
  train         Baum-Welch training (single sequence)
  train-multi   Baum-Welch training (multiple sequences)
  posterior     Posterior decoding
  random        Create a random HMM and save it
  uniform       Create a uniform HMM and save it
  info          Print model parameters
  classify      Classify observations against multiple models
  entropy       Print per-timestep posterior entropy
  visualize     Render ASCII visualisations
  compare       Compare two models via symmetric KL
  dwell         Print expected dwell times per state
  profile       Build a Profile HMM from a multiple sequence alignment
  cv            K-fold cross-validation for model selection
  grid          Grid search over Baum-Welch hyperparameters
  restarts      Train with multiple random restarts
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from typing import List, Optional, Sequence

from .hmm import HMM
from .algorithms import forward, backward, viterbi, baum_welch, baum_welch_multi, posterior_decode
from .sequences import (
    generate_sequence,
    save_hmm,
    load_hmm,
    save_observation_sequence,
    load_observation_sequence,
    hmm_to_dict,
    hmm_from_dict,
)
from .logging_config import get_logger, configure_logging

_log = get_logger()


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="hmm-toolkit",
        description="Hidden Markov Model toolkit — Forward/Backward/Viterbi/Baum-Welch + more",
    )
    p.add_argument("--log-level", default="WARNING",
                   choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                   help="Logging verbosity (default: WARNING)")
    sub = p.add_subparsers(dest="command", required=True)

    # generate
    gen = sub.add_parser("generate", help="Sample a sequence from an HMM model file")
    gen.add_argument("--model", required=True, help="Path to HMM JSON file")
    gen.add_argument("--length", type=int, default=20, help="Sequence length")
    gen.add_argument("--seed", type=int, default=None, help="RNG seed")
    gen.add_argument("--show-states", action="store_true", help="Also print hidden states")

    # viterbi
    vit = sub.add_parser("viterbi", help="Decode most likely state path")
    vit.add_argument("--model", required=True, help="Path to HMM JSON file")
    vit.add_argument("--obs", required=True, help="Path to observation JSON file")

    # forward
    fwd = sub.add_parser("forward", help="Compute sequence log-likelihood")
    fwd.add_argument("--model", required=True, help="Path to HMM JSON file")
    fwd.add_argument("--obs", required=True, help="Path to observation JSON file")

    # train
    train = sub.add_parser("train", help="Baum-Welch training on an observation file")
    train.add_argument("--model", required=True, help="Path to HMM JSON file (input)")
    train.add_argument("--obs", required=True, help="Path to observation JSON file")
    train.add_argument("--out", required=True, help="Path for trained HMM JSON")
    train.add_argument("--iterations", type=int, default=100)
    train.add_argument("--tol", type=float, default=1e-6)
    train.add_argument("--verbose", action="store_true")

    # train-multi
    tm = sub.add_parser("train-multi", help="Baum-Welch training on multiple observation files")
    tm.add_argument("--model", required=True, help="Path to HMM JSON file (input)")
    tm.add_argument("--obs", required=True, help="Comma-separated observation JSON files")
    tm.add_argument("--out", required=True, help="Path for trained HMM JSON")
    tm.add_argument("--iterations", type=int, default=100)
    tm.add_argument("--tol", type=float, default=1e-6)
    tm.add_argument("--verbose", action="store_true")

    # posterior
    post = sub.add_parser("posterior", help="Posterior decoding (forward-backward)")
    post.add_argument("--model", required=True)
    post.add_argument("--obs", required=True)

    # random
    rnd = sub.add_parser("random", help="Create a random HMM and save it")
    rnd.add_argument("--states", required=True, help="Comma-separated state names")
    rnd.add_argument("--symbols", required=True, help="Comma-separated symbol names")
    rnd.add_argument("--out", required=True, help="Output path")
    rnd.add_argument("--seed", type=int, default=None)

    # uniform
    uni = sub.add_parser("uniform", help="Create a uniform HMM and save it")
    uni.add_argument("--states", required=True, help="Comma-separated state names")
    uni.add_argument("--symbols", required=True, help="Comma-separated symbol names")
    uni.add_argument("--out", required=True, help="Output path")

    # info
    info = sub.add_parser("info", help="Print model parameters")
    info.add_argument("--model", required=True)

    # classify
    cls = sub.add_parser("classify", help="Classify observations against multiple models")
    cls.add_argument("--models", required=True, help="Comma-separated list of HMM JSON files")
    cls.add_argument("--obs", required=True, help="Path to observation JSON file")

    # entropy
    ent = sub.add_parser("entropy", help="Print per-timestep posterior entropy")
    ent.add_argument("--model", required=True)
    ent.add_argument("--obs", required=True)

    # visualize
    viz = sub.add_parser("visualize", help="Render ASCII visualisations")
    viz.add_argument("--model", required=True, help="Path to HMM JSON file")
    viz.add_argument("--obs", help="Path to observation JSON file (for path/heatmap)")
    viz.add_argument("--type", choices=["transition", "path", "heatmap", "entropy", "model"],
                     default="model", help="Type of visualisation")

    # compare
    cmp = sub.add_parser("compare", help="Compare two models via symmetric KL divergence")
    cmp.add_argument("--model-a", required=True)
    cmp.add_argument("--model-b", required=True)
    cmp.add_argument("--obs", required=True)

    # dwell
    dwl = sub.add_parser("dwell", help="Print expected dwell times per state")
    dwl.add_argument("--model", required=True)

    # profile
    prof = sub.add_parser("profile", help="Build a Profile HMM from a multiple sequence alignment")
    prof.add_argument("--alignment", required=True, help="Path to JSON file with MSA (list of strings)")
    prof.add_argument("--alphabet", required=True, help="Alphabet characters, e.g. ACGT")
    prof.add_argument("--out", required=True, help="Output path for profile HMM JSON")
    prof.add_argument("--threshold", type=float, default=0.5, help="Match column threshold")
    prof.add_argument("--score-seq", help="Sequence to score against the profile (log-odds)")

    # cv
    cvp = sub.add_parser("cv", help="K-fold cross-validation for model selection")
    cvp.add_argument("--symbols", required=True, help="Comma-separated symbol names")
    cvp.add_argument("--obs", required=True, help="Comma-separated observation JSON files")
    cvp.add_argument("--n-states", required=True, help="Comma-separated state counts to try")
    cvp.add_argument("--k", type=int, default=5, help="Number of folds")
    cvp.add_argument("--iterations", type=int, default=50)
    cvp.add_argument("--seed", type=int, default=42)

    # grid
    grp = sub.add_parser("grid", help="Grid search over Baum-Welch hyperparameters")
    grp.add_argument("--states", required=True, help="Comma-separated state names")
    grp.add_argument("--symbols", required=True, help="Comma-separated symbol names")
    grp.add_argument("--obs", required=True, help="Path to observation JSON file")
    grp.add_argument("--restarts", type=int, default=5)
    grp.add_argument("--iterations", type=int, default=100)
    grp.add_argument("--seed", type=int, default=0)

    # restarts
    rst = sub.add_parser("restarts", help="Train with multiple random restarts")
    rst.add_argument("--states", required=True, help="Comma-separated state names")
    rst.add_argument("--symbols", required=True, help="Comma-separated symbol names")
    rst.add_argument("--obs", required=True, help="Path to observation JSON file")
    rst.add_argument("--out", required=True, help="Output path for best model")
    rst.add_argument("--n-restarts", type=int, default=10)
    rst.add_argument("--iterations", type=int, default=100)
    rst.add_argument("--seed", type=int, default=0)

    return p


def _print_matrix(name: str, mat: Sequence[Sequence[float]], row_labels, col_labels) -> None:
    print(f"\n{name}:")
    header = "        " + " ".join(f"{c:>10}" for c in col_labels)
    print(header)
    for rl, row in zip(row_labels, mat):
        vals = " ".join(f"{v:>10.6f}" for v in row)
        print(f"  {str(rl):>6} {vals}")


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def cmd_generate(args) -> int:
    hmm = load_hmm(args.model)
    states, obs = generate_sequence(hmm, args.length, seed=args.seed)
    print("Observations:", " ".join(obs))
    if args.show_states:
        print("States:     ", " ".join(states))
    return 0


def cmd_viterbi(args) -> int:
    hmm = load_hmm(args.model)
    obs_symbols = load_observation_sequence(args.obs)
    obs = hmm.observation_sequence(obs_symbols)
    path, logp = viterbi(hmm, obs)
    if not path:
        print("Impossible sequence — no valid path.")
        return 1
    print("Most likely states:", " ".join(hmm.states[i] for i in path))
    print(f"Log-probability: {logp:.6f}")
    return 0


def cmd_forward(args) -> int:
    hmm = load_hmm(args.model)
    obs_symbols = load_observation_sequence(args.obs)
    obs = hmm.observation_sequence(obs_symbols)
    _, _, ll = forward(hmm, obs)
    print(f"Log-likelihood: {ll:.6f}")
    return 0


def cmd_train(args) -> int:
    hmm = load_hmm(args.model)
    obs_symbols = load_observation_sequence(args.obs)
    obs = hmm.observation_sequence(obs_symbols)
    final_ll, iters = baum_welch(
        hmm, obs, iterations=args.iterations, tol=args.tol, verbose=args.verbose
    )
    save_hmm(hmm, args.out)
    print(f"Training completed in {iters} iterations, final log-likelihood: {final_ll:.6f}")
    print(f"Trained model saved to {args.out}")
    return 0


def cmd_train_multi(args) -> int:
    hmm = load_hmm(args.model)
    obs_paths = [p.strip() for p in args.obs.split(",")]
    obs_list = []
    for p in obs_paths:
        syms = load_observation_sequence(p)
        obs_list.append(hmm.observation_sequence(syms))
    final_ll, iters = baum_welch_multi(
        hmm, obs_list, iterations=args.iterations, tol=args.tol, verbose=args.verbose
    )
    save_hmm(hmm, args.out)
    print(f"Multi-sequence training: {iters} iterations, final log-likelihood: {final_ll:.6f}")
    print(f"Trained model saved to {args.out}")
    return 0


def cmd_posterior(args) -> int:
    hmm = load_hmm(args.model)
    obs_symbols = load_observation_sequence(args.obs)
    obs = hmm.observation_sequence(obs_symbols)
    path, gamma = posterior_decode(hmm, obs)
    print("Posterior-decoded states:", " ".join(hmm.states[i] for i in path))
    print("\nPosterior probabilities:")
    header = "  t   " + " ".join(f"{s:>10}" for s in hmm.states)
    print(header)
    for t, row in enumerate(gamma):
        vals = " ".join(f"{v:>10.6f}" for v in row)
        print(f"  {t:>3}  {vals}")
    return 0


def cmd_random(args) -> int:
    states = [s.strip() for s in args.states.split(",")]
    symbols = [s.strip() for s in args.symbols.split(",")]
    hmm = HMM.random(states, symbols, seed=args.seed)
    save_hmm(hmm, args.out)
    print(f"Random HMM with {len(states)} states and {len(symbols)} symbols saved to {args.out}")
    return 0


def cmd_uniform(args) -> int:
    states = [s.strip() for s in args.states.split(",")]
    symbols = [s.strip() for s in args.symbols.split(",")]
    hmm = HMM.uniform(states, symbols)
    save_hmm(hmm, args.out)
    print(f"Uniform HMM with {len(states)} states and {len(symbols)} symbols saved to {args.out}")
    return 0


def cmd_info(args) -> int:
    from .viz import format_model
    hmm = load_hmm(args.model)
    print(format_model(hmm))
    return 0


def cmd_classify(args) -> int:
    from .analysis import classify_sequence
    model_paths = [p.strip() for p in args.models.split(",")]
    models = [load_hmm(p) for p in model_paths]
    obs_symbols = load_observation_sequence(args.obs)
    obs = models[0].observation_sequence(obs_symbols)
    best_idx, best_name, best_ll = classify_sequence(models, obs, model_names=model_paths)
    print(f"Best model: {best_name} (index {best_idx})")
    print(f"Log-likelihood: {best_ll:.6f}")
    return 0


def cmd_entropy(args) -> int:
    from .analysis import state_entropy
    hmm = load_hmm(args.model)
    obs_symbols = load_observation_sequence(args.obs)
    obs = hmm.observation_sequence(obs_symbols)
    entropies = state_entropy(hmm, obs)
    print("Per-timestep posterior entropy (nats):")
    for t, h in enumerate(entropies):
        print(f"  t={t:>3}: {h:.6f}")
    avg = sum(entropies) / len(entropies) if entropies else 0.0
    print(f"\nAverage entropy: {avg:.6f}")
    return 0


def cmd_visualize(args) -> int:
    from .viz import (transition_diagram, viterbi_path_visualization,
                      posterior_heatmap, entropy_sparkline, format_model)
    hmm = load_hmm(args.model)
    if args.type == "transition":
        print(transition_diagram(hmm))
    elif args.type == "model":
        print(format_model(hmm))
    elif args.type in ("path", "heatmap", "entropy"):
        if not args.obs:
            print("--obs is required for path/heatmap/entropy visualisation", file=sys.stderr)
            return 1
        obs_symbols = load_observation_sequence(args.obs)
        if args.type == "path":
            print(viterbi_path_visualization(hmm, obs_symbols))
        elif args.type == "heatmap":
            print(posterior_heatmap(hmm, obs_symbols))
        elif args.type == "entropy":
            print(entropy_sparkline(hmm, obs_symbols))
    return 0


def cmd_compare(args) -> int:
    from .analysis import symmetric_kl
    hmm_a = load_hmm(args.model_a)
    hmm_b = load_hmm(args.model_b)
    obs_symbols = load_observation_sequence(args.obs)
    obs = hmm_a.observation_sequence(obs_symbols)
    kl = symmetric_kl(hmm_a, hmm_b, obs)
    print(f"Symmetric KL divergence: {kl:.6f}")
    return 0


def cmd_dwell(args) -> int:
    from .analysis import expected_state_dwell_time
    hmm = load_hmm(args.model)
    dwell = expected_state_dwell_time(hmm)
    print("Expected state dwell times:")
    for s, d in zip(hmm.states, dwell):
        print(f"  {s:>10}: {d:.2f} steps")
    return 0


def cmd_profile(args) -> int:
    from .profile import build_profile_hmm
    with open(args.alignment, "r", encoding="utf-8") as f:
        data = json.load(f)
    alignment = data if isinstance(data, list) else data.get("alignment", [])
    alphabet = list(args.alphabet)
    ph = build_profile_hmm(alignment, alphabet, threshold=args.threshold)
    print(f"Profile HMM: {ph}")
    print(f"  Match columns: {ph.match_columns}")
    print(f"  States: {ph.state_labels}")
    # Save
    prof_data = {
        "alphabet": ph.alphabet,
        "match_columns": ph.match_columns,
        "A": ph.A,
        "B": ph.B,
        "pi": ph.pi,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(prof_data, f, indent=2)
    print(f"  Saved to {args.out}")
    if args.score_seq:
        score = ph.log_odds_score(list(args.score_seq))
        ll = ph.log_likelihood(list(args.score_seq))
        print(f"\n  Sequence: {args.score_seq}")
        print(f"  Log-likelihood: {ll:.4f}")
        print(f"  Log-odds score: {score:.4f}")
    return 0


def cmd_cv(args) -> int:
    from .training import k_fold_cross_validation, summarize_cv_results
    symbols = [s.strip() for s in args.symbols.split(",")]
    obs_paths = [p.strip() for p in args.obs.split(",")]
    # Load all observation sequences
    all_obs = []
    for p in obs_paths:
        syms = load_observation_sequence(p)
        # Build a temp HMM just for index conversion
        tmp = HMM(["x"], symbols, [[1.0]], [[1.0 / len(symbols)] * len(symbols)], [1.0])
        all_obs.append(tmp.observation_sequence(syms))
    n_states_list = [int(x) for x in args.n_states.split(",")]
    results = k_fold_cross_validation(
        [], symbols, all_obs,
        n_states_options=n_states_list,
        k=args.k, iterations=args.iterations, seed=args.seed,
    )
    summary = summarize_cv_results(results)
    print("Cross-Validation Results:")
    print(f"{'n_states':>10} {'mean_train_ll':>15} {'mean_val_ll':>15} {'n_folds':>8}")
    for ns in sorted(summary):
        s = summary[ns]
        print(f"{ns:>10} {s['mean_train_ll']:>15.4f} {s['mean_val_ll']:>15.4f} {int(s['n_folds']):>8}")
    # Recommend
    best_ns = max(summary, key=lambda ns: summary[ns]["mean_val_ll"])
    print(f"\nRecommended: {best_ns} states (highest mean validation LL)")
    return 0


def cmd_grid(args) -> int:
    from .training import grid_search
    states = [s.strip() for s in args.states.split(",")]
    symbols = [s.strip() for s in args.symbols.split(",")]
    obs_symbols = load_observation_sequence(args.obs)
    tmp = HMM(states, symbols,
              [[1.0 / len(states)] * len(states)] * len(states),
              [[1.0 / len(symbols)] * len(symbols)] * len(states),
              [1.0 / len(states)] * len(states))
    obs = tmp.observation_sequence(obs_symbols)
    results = grid_search(states, symbols, obs,
                          n_restarts=args.restarts,
                          iterations=args.iterations, seed=args.seed)
    print("Grid Search Results:")
    print(f"{'smooth':>12} {'tol':>12} {'best_ll':>15} {'restart':>8}")
    for r in results:
        print(f"{r['smooth']:>12.2e} {r['tol']:>12.2e} {r['best_ll']:>15.4f} {r['restart_idx']:>8}")
    best = max(results, key=lambda r: r["best_ll"])
    print(f"\nBest: smooth={best['smooth']:.2e}, tol={best['tol']:.2e}, ll={best['best_ll']:.4f}")
    return 0


def cmd_restarts(args) -> int:
    from .training import train_with_restarts
    states = [s.strip() for s in args.states.split(",")]
    symbols = [s.strip() for s in args.symbols.split(",")]
    obs_symbols = load_observation_sequence(args.obs)
    tmp = HMM(states, symbols,
              [[1.0 / len(states)] * len(states)] * len(states),
              [[1.0 / len(symbols)] * len(symbols)] * len(states),
              [1.0 / len(states)] * len(states))
    obs = tmp.observation_sequence(obs_symbols)
    best_hmm, best_ll, best_idx = train_with_restarts(
        states, symbols, obs,
        n_restarts=args.n_restarts,
        iterations=args.iterations, seed=args.seed,
    )
    save_hmm(best_hmm, args.out)
    print(f"Best restart: #{best_idx}, log-likelihood: {best_ll:.6f}")
    print(f"Saved to {args.out}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.log_level)
    handlers = {
        "generate": cmd_generate,
        "viterbi": cmd_viterbi,
        "forward": cmd_forward,
        "train": cmd_train,
        "train-multi": cmd_train_multi,
        "posterior": cmd_posterior,
        "random": cmd_random,
        "uniform": cmd_uniform,
        "info": cmd_info,
        "classify": cmd_classify,
        "entropy": cmd_entropy,
        "visualize": cmd_visualize,
        "compare": cmd_compare,
        "dwell": cmd_dwell,
        "profile": cmd_profile,
        "cv": cmd_cv,
        "grid": cmd_grid,
        "restarts": cmd_restarts,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())