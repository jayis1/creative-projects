"""Command-line interface for hmm-toolkit."""

from __future__ import annotations

import argparse
import json
import math
import sys
from typing import List, Optional, Sequence

from .hmm import HMM
from .algorithms import forward, backward, viterbi, baum_welch, posterior_decode
from .sequences import (
    generate_sequence,
    save_hmm,
    load_hmm,
    save_observation_sequence,
    load_observation_sequence,
    hmm_to_dict,
    hmm_from_dict,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="hmm-toolkit",
        description="Hidden Markov Model toolkit (Forward/Backward/Viterbi/Baum-Welch)",
    )
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

    # posterior
    post = sub.add_parser("posterior", help="Posterior decoding (forward-backward)")
    post.add_argument("--model", required=True)
    post.add_argument("--obs", required=True)

    # create random
    rnd = sub.add_parser("random", help="Create a random HMM and save it")
    rnd.add_argument("--states", required=True, help="Comma-separated state names")
    rnd.add_argument("--symbols", required=True, help="Comma-separated symbol names")
    rnd.add_argument("--out", required=True, help="Output path")
    rnd.add_argument("--seed", type=int, default=None)

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

    return p


def _print_matrix(name: str, mat: Sequence[Sequence[float]], row_labels, col_labels) -> None:
    print(f"\n{name}:")
    header = "        " + " ".join(f"{c:>10}" for c in col_labels)
    print(header)
    for rl, row in zip(row_labels, mat):
        vals = " ".join(f"{v:>10.6f}" for v in row)
        print(f"  {str(rl):>6} {vals}")


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


def cmd_info(args) -> int:
    hmm = load_hmm(args.model)
    print(repr(hmm))
    _print_matrix("Transition matrix A", hmm.A, hmm.states, hmm.states)
    _print_matrix("Emission matrix B", hmm.B, hmm.states, hmm.symbols)
    print("\nInitial distribution pi:")
    for s, p in zip(hmm.states, hmm.pi):
        print(f"  {s:>10}: {p:.6f}")
    return 0


def cmd_classify(args) -> int:
    from .analysis import classify_sequence
    model_paths = [p.strip() for p in args.models.split(",")]
    models = [load_hmm(p) for p in model_paths]
    obs_symbols = load_observation_sequence(args.obs)
    # use the first model to convert symbols to indices (assume same symbol set)
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


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "generate": cmd_generate,
        "viterbi": cmd_viterbi,
        "forward": cmd_forward,
        "train": cmd_train,
        "posterior": cmd_posterior,
        "random": cmd_random,
        "info": cmd_info,
        "classify": cmd_classify,
        "entropy": cmd_entropy,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())