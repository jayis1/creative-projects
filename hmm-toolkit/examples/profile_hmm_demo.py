"""Example: Profile HMM for biological motif detection.

Builds a Profile HMM from a small DNA multiple sequence alignment,
then scores new sequences against the profile using log-odds scoring.
"""

from __future__ import annotations

from hmm.profile import build_profile_hmm


def main() -> None:
    print("=== Profile HMM — Biological Motif Detection ===\n")

    # A small multiple sequence alignment (MSA) of a DNA motif
    # Columns with gaps indicate insertions/deletions
    alignment = [
        "ATGCGTAC",
        "AT-CGTAC",
        "A-GCGTAC",
        "ATGCGTAC",
        "ATGCG-AC",
        "AT-CGTAC",
        "A-GCGTAC",
        "ATGCGTAC",
    ]

    alphabet = list("ACGT")
    print(f"Alignment ({len(alignment)} sequences):")
    for seq in alignment:
        print(f"  {seq}")

    # Build the Profile HMM
    ph = build_profile_hmm(alignment, alphabet, threshold=0.5)
    print(f"\n{ph}")
    print(f"  Match columns: {ph.match_columns}")
    print(f"  State labels: {ph.state_labels}")

    # Score some sequences (ungapped only — Profile HMM scores raw sequences)
    test_seqs = [
        "ATGCGTAC",   # matches the motif
        "ATGCGTAA",   # close match (last base differs)
        "GGGGCCCC",   # unrelated
        "ATGGGGAC",   # has an insertion-like stretch
        "ATGCG",      # partial match
    ]

    print("\nLog-odds scores (higher = more similar to motif):")
    print(f"{'Sequence':>12} {'Log-likelihood':>16} {'Log-odds':>10}")
    for seq in test_seqs:
        ll = ph.log_likelihood(list(seq))
        score = ph.log_odds_score(list(seq))
        print(f"  {seq:>10} {ll:>16.4f} {score:>10.4f}")

    # Viterbi path for a matching sequence
    from hmm.profile import _ProfileWrapper
    path, logp = ph.viterbi("ATGCGTAC")
    state_path = [ph.state_labels[i] for i in path]
    print(f"\nViterbi path for ATGCGTAC:")
    print(f"  {' '.join(state_path)}")
    print(f"  Log-prob: {logp:.4f}")


if __name__ == "__main__":
    main()