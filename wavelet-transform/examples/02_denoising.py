"""Example: Denoising with different methods and transforms.

Compares DWT, MODWT, and cycle-spinning denoising on noisy signals.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wavelet import (
    generate, add_noise, denoise1d, cycle_spin_denoise,
    Threshold, soft, hard, garrote,
    DWT, MODWT, wavelet,
)
from wavelet.utils import snr, mse


def main():
    # Generate a blocks signal (good for denoising demos)
    n = 512
    clean = generate("blocks", n)
    noisy = add_noise(clean, 0.5, seed=42)

    noisy_snr = snr(clean, noisy)
    print(f"Clean signal: blocks (n={n})")
    print(f"Noisy signal SNR: {noisy_snr:.2f} dB\n")

    # Compare denoising methods
    print(f"{'Method':<20} {'Transform':<15} {'Wavelet':<10} {'SNR (dB)':<10} {'MSE':<12}")
    print("-" * 67)

    for wname in ["haar", "db4"]:
        for method in [Threshold.UNIVERSAL, Threshold.BAYES, Threshold.SURE]:
            for transform in ["dwt", "modwt"]:
                denoised = denoise1d(noisy, wavelet=wname,
                                     threshold_method=method,
                                     transform=transform)
                s = snr(clean, denoised)
                m = mse(clean, denoised)
                print(f"{method.value:<20} {transform:<15} {wname:<10} {s:<10.2f} {m:<12.6f}")

    # Cycle-spinning denoising (best for artifact reduction)
    print()
    for n_shifts in [4, 8, 16, 32]:
        denoised = cycle_spin_denoise(noisy, "db4",
                                      threshold_method=Threshold.BAYES,
                                      n_shifts=n_shifts)
        s = snr(clean, denoised)
        m = mse(clean, denoised)
        print(f"{'bayes (cycle-spin)':<20} {'dwt+spin':<15} {'db4':<10} "
              f"{s:<10.2f} {m:<12.6f}  ({n_shifts} shifts)")


if __name__ == "__main__":
    main()