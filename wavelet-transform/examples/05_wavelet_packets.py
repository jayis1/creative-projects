"""Example: Wavelet packet decomposition and best-basis selection.

Wavelet packets decompose both the approximation AND detail at each level,
producing a full binary tree.  The best-basis algorithm selects the
optimal subset of nodes to represent the signal with minimal entropy.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wavelet import WaveletPacket, generate, DWT
from wavelet.utils import energy, entropy


def main():
    n = 256
    signal = generate("doppler", n)

    wp = WaveletPacket("db4")
    result = wp.decompose(signal, level=4)

    print(f"Wavelet Packet Decomposition (doppler signal, n={n})")
    print(f"  Wavelet: db4, level: {result['level']}")
    print(f"  Total packets: {len(result['packets'])}")
    print()

    # Show all packets with their energy
    print(f"  {'Path':>8s} {'N':>5s} {'Energy':>12s} {'Entropy':>10s}")
    print("  " + "-" * 38)

    for path in sorted(result["packets"].keys(), key=lambda p: (len(p), p)):
        coeffs = result["packets"][path]
        e = energy(coeffs)
        ent = entropy(coeffs)
        label = path or "root"
        print(f"  {label:>8s} {len(coeffs):>5d} {e:>12.4f} {ent:>10.4f}")

    # Best basis selection
    best = wp.best_basis(result)
    print(f"\n  Best basis ({len(best)} nodes): {best}")

    # Compare: full packet tree vs standard DWT
    dwt = DWT("db4")
    dwt_result = dwt.decompose(signal, level=4)
    dwt_energy = sum(energy(d) for d in dwt_result.details) + energy(dwt_result.approx)
    print(f"\n  Standard DWT uses {len(dwt_result.details) + 1} bands (fixed)")
    print(f"  Best-basis uses {len(best)} adaptive bands")


if __name__ == "__main__":
    main()