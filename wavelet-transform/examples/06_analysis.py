"""Example: Coefficient analysis and wavelet comparison.

Shows how to analyze wavelet decomposition statistics and compare
different wavelet families on the same signal.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wavelet import DWT, generate, analyze, compare_wavelets


def main():
    n = 256
    signal = generate("ecg", n)

    # Decompose and analyze
    dwt = DWT("db4")
    result = dwt.decompose(signal, level=4)
    analysis = analyze(result)

    print(analysis.summary())

    # Scale correlation matrix
    print("\nScale correlation matrix:")
    corr = analysis.scale_corr
    if corr:
        header = "       " + "  ".join(f"D{i+1:>3d}" for i in range(len(corr)))
        print(header)
        for i, row in enumerate(corr):
            vals = "  ".join(f"{v:6.3f}" for v in row)
            print(f"  D{i+1:>3d}  {vals}")

    # Compare wavelet families
    print("\n\nWavelet Comparison on ECG signal:")
    print(f"{'Wavelet':<10} {'Total Energy':>14} {'N Scales':>10} "
          f"{'Approx Energy':>14} {'Detail Energy':>14}")
    print("-" * 66)

    comparison = compare_wavelets(signal, ["haar", "db2", "db4", "db8", "sym4", "coif2"], level=4)
    for name, a in comparison.items():
        detail_e = sum(s.energy for s in a.stats[:-1])
        approx_e = a.stats[-1].energy if a.stats else 0
        print(f"{name:<10} {a.total_energy:>14.6f} {a.n_scales:>10d} "
              f"{approx_e:>14.6f} {detail_e:>14.6f}")


if __name__ == "__main__":
    main()