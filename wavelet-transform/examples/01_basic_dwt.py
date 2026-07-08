"""Example: Basic DWT decomposition and reconstruction.

Demonstrates the core wavelet transform workflow:
  1. Generate a test signal
  2. Decompose with DWT
  3. Reconstruct
  4. Verify perfect reconstruction
"""
import math
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wavelet import DWT, wavelet, generate
from wavelet.utils import mse, snr


def main():
    # Generate a multi-tone test signal
    n = 256
    signal = generate("multi", n)

    print(f"Signal: multi-tone (n={n})")
    print(f"  Energy: {sum(s*s for s in signal):.4f}")

    # Try different wavelets
    for wname in ["haar", "db4", "db8", "sym4", "coif2"]:
        w = wavelet(wname)
        dwt = DWT(w)

        # Decompose
        result = dwt.decompose(signal, level=4)
        print(f"\n{wname} decomposition:")
        print(f"  Level: {result.level}")
        print(f"  Approximation: {len(result.approx)} coefficients")
        for i, detail in enumerate(result.details):
            print(f"  Detail D{i+1}: {len(detail)} coefficients")

        # Reconstruct
        recon = dwt.reconstruct(result)
        error = mse(signal, recon)
        max_err = max(abs(s - r) for s, r in zip(signal, recon))
        print(f"  Reconstruction MSE: {error:.2e}")
        print(f"  Max abs error: {max_err:.2e}")


if __name__ == "__main__":
    main()