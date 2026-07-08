"""Example: Continuous Wavelet Transform (CWT) scalogram.

Shows how to compute a CWT scalogram and visualize it as ASCII art.
The CWT provides time-scale (time-frequency) information.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wavelet import cwt, icwt, generate
from wavelet.utils import mse


def main():
    # A chirp signal is ideal for CWT (frequency changes over time)
    n = 256
    signal = generate("chirp", n)

    # Compute CWT with Morlet wavelet
    result = cwt(signal, "morlet", dt=1.0, dj=0.25)

    print(f"CWT Scalogram (Morlet wavelet)")
    print(f"  Signal: chirp (n={n})")
    print(f"  Scales: {result.n_scales} ({result.scales[0]:.3f} to {result.scales[-1]:.3f})")
    print()

    # ASCII scalogram
    power = result.power
    max_power = max(p for row in power for p in row)
    chars = " .:-=+*#%@"

    # Print scale axis on the left, time on horizontal
    scale_step = max(1, len(power) // 25)
    time_step = max(1, n // 70)

    print("  Scale  |  Time →")
    print("  ------ +" + "-" * 70)

    for si in range(0, len(power), scale_step):
        row = power[si]
        line = ""
        for ti in range(0, n, time_step):
            level = int(row[ti] / max_power * (len(chars) - 1))
            line += chars[max(0, min(len(chars) - 1, level))]
        print(f"  {result.scales[si]:6.2f} |{line}")

    # Reconstruction
    recon = icwt(result)
    err = mse(signal, recon)
    print(f"\n  Reconstruction MSE: {err:.6f}")

    # Also try Mexican Hat (real wavelet, good for peak detection)
    print("\n  --- Mexican Hat CWT ---")
    result_mh = cwt(signal, "mexhat", dt=1.0, dj=0.25)
    print(f"  Scales: {result_mh.n_scales}")
    recon_mh = icwt(result_mh)
    print(f"  Reconstruction MSE: {mse(signal, recon_mh):.6f}")


if __name__ == "__main__":
    main()