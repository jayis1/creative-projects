"""Example: Signal compression with wavelet thresholding.

Demonstrates compressing a signal by discarding small wavelet coefficients.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wavelet import compress1d, decompress1d, serialize, deserialize, generate
from wavelet.utils import mse, psnr


def main():
    n = 512
    signal = generate("multi", n)

    print(f"Signal compression (n={n})")
    print(f"{'Keep%':<8} {'Coeffs Kept':<14} {'Sparsity':<10} "
          f"{'Compression':<12} {'MSE':<12} {'PSNR (dB)':<10}")
    print("-" * 66)

    for keep_ratio in [1.0, 0.5, 0.3, 0.1, 0.05, 0.02, 0.01]:
        compressed = compress1d(signal, wavelet="db4",
                                keep_ratio=keep_ratio)
        recon = decompress1d(compressed)
        m = mse(signal, recon)
        p = psnr(signal, recon)
        print(f"{keep_ratio:<8.0%} {compressed.n_coeffs_kept:>6d}/{compressed.n_coeffs_total:<6d} "
              f"{compressed.sparsity:<10.2%} {compressed.compression_ratio:<12.1f}x "
              f"{m:<12.6f} {p:<10.2f}")

    # Binary serialization
    print("\n  Binary serialization:")
    compressed = compress1d(signal, wavelet="db4", keep_ratio=0.1)
    data = serialize(compressed)
    print(f"  Compressed binary size: {len(data)} bytes")
    print(f"  Original (float64):     {n * 8} bytes")
    print(f"  Space saving:           {1 - len(data)/(n*8):.1%}")

    # Verify serialization roundtrip
    restored = deserialize(data)
    recon = decompress1d(restored)
    print(f"  Serialization roundtrip MSE: {mse(signal, recon):.6f}")


if __name__ == "__main__":
    main()