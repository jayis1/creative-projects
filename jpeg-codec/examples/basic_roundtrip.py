"""Example: Basic encode and decode roundtrip.

Demonstrates the simplest usage of the jpeg-codec API.
"""

import numpy as np
from jpeg_codec import encode, decode
from jpeg_codec.metrics import psnr, ssim


def main():
    # Create a smooth test image (gradient)
    x = np.linspace(0, 255, 256, dtype=np.float64)
    y = np.linspace(0, 255, 256, dtype=np.float64)
    img = np.zeros((256, 256, 3), dtype=np.uint8)
    img[..., 0] = np.tile(x, (256, 1))
    img[..., 1] = np.tile(y.reshape(-1, 1), (1, 256))
    img[..., 2] = ((img[..., 0].astype(int) + img[..., 1].astype(int)) // 2)

    # Encode at quality 85 with 4:2:0 subsampling
    jpeg_data = encode(img, quality=85, sampling="4:2:0")
    print(f"Original: {img.nbytes} bytes ({img.shape})")
    print(f"JPEG:     {len(jpeg_data)} bytes")
    print(f"Ratio:    {img.nbytes / len(jpeg_data):.2f}:1")

    # Decode back
    recon = decode(jpeg_data)
    print(f"Reconstructed: {recon.shape}")

    # Quality metrics
    p = psnr(img, recon)
    s = ssim(img, recon)
    print(f"PSNR:     {p:.2f} dB")
    print(f"SSIM:     {s:.4f}")


if __name__ == "__main__":
    main()