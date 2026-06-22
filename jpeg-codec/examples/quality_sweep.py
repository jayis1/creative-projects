"""Example: Quality sweep across multiple quality levels.

Shows how to evaluate PSNR and SSIM across a range of quality
settings to find the optimal quality/compression trade-off.
"""

import numpy as np
from jpeg_codec import encode, decode
from jpeg_codec.metrics import quality_report


def main():
    # Create a test image with smooth gradients and some detail
    img = np.zeros((128, 128, 3), dtype=np.uint8)
    x = np.linspace(0, 255, 128, dtype=np.float64)
    img[..., 0] = np.tile(x, (128, 1))
    img[..., 1] = np.tile(x.reshape(-1, 1), (1, 128))
    img[..., 2] = np.sin(np.linspace(0, 6 * np.pi, 128)) * 127 + 128

    qualities = [10, 25, 50, 75, 85, 90, 95]

    print(f"{'Quality':>8} | {'PSNR (dB)':>10} | {'SSIM':>7} | "
          f"{'Size':>7} | {'Ratio':>7} | {'BPP':>6}")
    print("-" * 65)

    for q in qualities:
        jpeg = encode(img, quality=q, sampling="4:2:0")
        recon = decode(jpeg)
        report = quality_report(img, recon, img.nbytes, len(jpeg))
        print(
            f"{q:8d} | "
            f"{report['psnr_db']:10.2f} | "
            f"{report['ssim']:7.4f} | "
            f"{report['compressed_bytes']:7d} | "
            f"{report['compression_ratio']:7.2f} | "
            f"{report['bits_per_pixel']:6.2f}"
        )


if __name__ == "__main__":
    main()