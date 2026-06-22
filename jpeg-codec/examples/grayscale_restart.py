"""Example: Grayscale encoding and restart markers.

Demonstrates grayscale JPEG encoding with restart markers for
error-resilient decoding.
"""

import numpy as np
from jpeg_codec import encode, decode, get_info
from jpeg_codec.metrics import psnr


def main():
    # Create a grayscale test image (checkerboard pattern)
    img = np.zeros((64, 64), dtype=np.uint8)
    for y in range(64):
        for x in range(64):
            if (x // 8 + y // 8) % 2 == 0:
                img[y, x] = 200
            else:
                img[y, x] = 50

    # Encode with restart markers every 4 MCUs
    jpeg = encode(img, quality=85, restart_interval=4)
    print(f"Grayscale image: {img.shape}")
    print(f"JPEG size:       {len(jpeg)} bytes")

    # Inspect restart interval
    info = get_info(jpeg)
    print(f"Components:      {info.num_components}")
    print(f"Restart interval: {info.restart_interval} MCUs")

    # Decode and verify quality
    recon = decode(jpeg)
    p = psnr(img, recon)
    print(f"PSNR:            {p:.2f} dB")
    print(f"Shape match:     {recon.shape == img.shape}")


if __name__ == "__main__":
    main()