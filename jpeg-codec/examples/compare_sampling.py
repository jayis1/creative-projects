"""Example: Compare chroma subsampling modes.

Compares 4:4:4, 4:2:2, 4:2:0, and 4:1:1 subsampling at the same
quality level, showing the trade-off between color fidelity and
compression ratio.
"""

import numpy as np
from jpeg_codec import encode, decode
from jpeg_codec.metrics import quality_report


def main():
    # Create an image with sharp color transitions
    img = np.zeros((128, 128, 3), dtype=np.uint8)
    img[:64, :64] = [255, 0, 0]       # Red quadrant
    img[:64, 64:] = [0, 255, 0]       # Green quadrant
    img[64:, :64] = [0, 0, 255]       # Blue quadrant
    img[64:, 64:] = [255, 255, 0]     # Yellow quadrant

    modes = ["4:4:4", "4:2:2", "4:2:0", "4:1:1"]

    print(f"{'Mode':>7} | {'PSNR (dB)':>10} | {'SSIM':>7} | "
          f"{'Size':>7} | {'Ratio':>7}")
    print("-" * 55)

    for mode in modes:
        jpeg = encode(img, quality=85, sampling=mode)
        recon = decode(jpeg)
        report = quality_report(img, recon, img.nbytes, len(jpeg))
        print(
            f"{mode:>7} | "
            f"{report['psnr_db']:10.2f} | "
            f"{report['ssim']:7.4f} | "
            f"{report['compressed_bytes']:7d} | "
            f"{report['compression_ratio']:7.2f}"
        )


if __name__ == "__main__":
    main()