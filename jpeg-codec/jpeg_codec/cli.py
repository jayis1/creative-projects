#!/usr/bin/env python3
"""Command-line tool: encode/decode JPEG files using jpeg-codec.

Usage
-----
Encode a PNG/PPM to JPEG:
    python -m jpeg_codec.cli encode input.png output.jpg [--quality 80] [--sampling 4:2:0]

Decode a JPEG to PNG:
    python -m jpeg_codec.cli decode input.jpg output.png

Round-trip test:
    python -m jpeg_codec.cli roundtrip input.png [--quality 80] [--sampling 4:2:0]

Info:
    python -m jpeg_codec.cli info input.jpg
"""

import argparse
import sys
import os
import numpy as np

# We need to load/save images.  Try PIL first, fall back to a simple PPM
# reader/writer for environments without PIL.
try:
    from PIL import Image
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


def _load_image(path: str) -> np.ndarray:
    """Load an image as uint8 numpy array (HxWx3 or HxW)."""
    if _HAS_PIL:
        img = Image.open(path)
        if img.mode == "RGB":
            return np.array(img)
        elif img.mode == "L":
            return np.array(img)
        else:
            return np.array(img.convert("RGB"))
    else:
        return _load_ppm(path)


def _save_image(path: str, arr: np.ndarray):
    """Save an image array."""
    if _HAS_PIL:
        if arr.ndim == 2:
            Image.fromarray(arr, mode="L").save(path)
        else:
            Image.fromarray(arr, mode="RGB").save(path)
    else:
        _save_ppm(path, arr)


def _load_ppm(path: str) -> np.ndarray:
    """Minimal PPM (P6) / PGM (P5) reader."""
    with open(path, "rb") as f:
        magic = f.readline().strip()
        if magic == b"P6":
            # Skip comments.
            line = f.readline()
            while line.startswith(b"#"):
                line = f.readline()
            w, h = map(int, line.split())
            maxval = int(f.readline())
            data = f.read(w * h * 3)
            return np.frombuffer(data, dtype=np.uint8).reshape(h, w, 3)
        elif magic == b"P5":
            line = f.readline()
            while line.startswith(b"#"):
                line = f.readline()
            w, h = map(int, line.split())
            maxval = int(f.readline())
            data = f.read(w * h)
            return np.frombuffer(data, dtype=np.uint8).reshape(h, w)
        else:
            raise ValueError(f"Unsupported format: {magic}")


def _save_ppm(path: str, arr: np.ndarray):
    """Minimal PPM/PGM writer."""
    with open(path, "wb") as f:
        if arr.ndim == 2:
            h, w = arr.shape
            f.write(f"P5\n{w} {h}\n255\n".encode())
            f.write(arr.tobytes())
        else:
            h, w, _ = arr.shape
            f.write(f"P6\n{w} {h}\n255\n".encode())
            f.write(arr.tobytes())


def _psnr(a: np.ndarray, b: np.ndarray) -> float:
    """Compute PSNR between two uint8 images."""
    a = a.astype(np.float64)
    b = b.astype(np.float64)
    mse = np.mean((a - b) ** 2)
    if mse == 0:
        return float("inf")
    return 10 * np.log10(255 ** 2 / mse)


def cmd_encode(args):
    from jpeg_codec import encode_image
    img = _load_image(args.input)
    data = encode_image(img, quality=args.quality, sampling=args.sampling)
    with open(args.output, "wb") as f:
        f.write(data)
    orig_size = os.path.getsize(args.input)
    jpeg_size = len(data)
    ratio = orig_size / jpeg_size if jpeg_size else 0
    print(f"Encoded {args.input} -> {args.output}")
    print(f"  Original: {orig_size} bytes")
    print(f"  JPEG:     {jpeg_size} bytes")
    print(f"  Ratio:    {ratio:.2f}:1")
    print(f"  Quality:  {args.quality}, Sampling: {args.sampling}")


def cmd_decode(args):
    from jpeg_codec import decode_image
    with open(args.input, "rb") as f:
        data = f.read()
    img = decode_image(data)
    _save_image(args.output, img)
    print(f"Decoded {args.input} -> {args.output}")
    print(f"  Shape: {img.shape}, dtype: {img.dtype}")


def cmd_roundtrip(args):
    from jpeg_codec import encode_image, decode_image
    orig = _load_image(args.input)
    jpeg_data = encode_image(orig, quality=args.quality, sampling=args.sampling)
    recon = decode_image(jpeg_data)
    psnr = _psnr(orig, recon)
    print(f"Round-trip: {args.input}")
    print(f"  Quality:  {args.quality}, Sampling: {args.sampling}")
    print(f"  Original: {os.path.getsize(args.input)} bytes")
    print(f"  JPEG:     {len(jpeg_data)} bytes")
    print(f"  PSNR:     {psnr:.2f} dB")


def cmd_info(args):
    with open(args.input, "rb") as f:
        data = f.read()
    print(f"File: {args.input}")
    print(f"  Size: {len(data)} bytes")
    soi = data[:2] == b'\xff\xd8'
    eoi = data[-2:] == b'\xff\xd9'
    print(f"  SOI:  {'yes' if soi else 'no'}")
    print(f"  EOI:  {'yes' if eoi else 'no'}")
    # Walk markers.
    i = 2
    while i < len(data) - 1:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = (data[i] << 8) | data[i + 1]
        names = {
            0xFFE0: "APP0 (JFIF)", 0xFFDB: "DQT", 0xFFC0: "SOF0",
            0xFFC4: "DHT", 0xFFDA: "SOS", 0xFFD9: "EOI",
        }
        name = names.get(marker, f"0x{marker:04X}")
        print(f"  Marker {name} at offset {i}")
        if marker == 0xFFDA:
            break
        if marker == 0xFFD9:
            break
        length = (data[i + 2] << 8) | data[i + 3]
        i += 2 + length


def main():
    parser = argparse.ArgumentParser(
        prog="jpeg_codec.cli",
        description="From-scratch JPEG encoder/decoder",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_enc = sub.add_parser("encode", help="Encode image to JPEG")
    p_enc.add_argument("input")
    p_enc.add_argument("output")
    p_enc.add_argument("--quality", type=int, default=50)
    p_enc.add_argument("--sampling", default="4:2:0",
                       choices=["4:4:4", "4:2:2", "4:2:0", "4:1:1"])
    p_enc.set_defaults(func=cmd_encode)

    p_dec = sub.add_parser("decode", help="Decode JPEG to image")
    p_dec.add_argument("input")
    p_dec.add_argument("output")
    p_dec.set_defaults(func=cmd_decode)

    p_rt = sub.add_parser("roundtrip", help="Encode then decode, report PSNR")
    p_rt.add_argument("input")
    p_rt.add_argument("--quality", type=int, default=50)
    p_rt.add_argument("--sampling", default="4:2:0",
                      choices=["4:4:4", "4:2:2", "4:2:0", "4:1:1"])
    p_rt.set_defaults(func=cmd_roundtrip)

    p_info = sub.add_parser("info", help="Show JPEG marker structure")
    p_info.add_argument("input")
    p_info.set_defaults(func=cmd_info)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()