#!/usr/bin/env python3
"""Command-line tool: encode/decode JPEG files using jpeg-codec.

Usage
-----
Encode a PNG/PPM to JPEG:
    python -m jpeg_codec.cli encode input.png output.jpg [--quality 85] [--sampling 4:2:0]

Decode a JPEG to PNG:
    python -m jpeg_codec.cli decode input.jpg output.png

Round-trip test with quality metrics:
    python -m jpeg_codec.cli roundtrip input.png [--quality 85] [--sampling 4:2:0] [--metrics]

Inspect JPEG structure:
    python -m jpeg_codec.cli info input.jpg

Quality sweep across multiple quality levels:
    python -m jpeg_codec.cli sweep input.png --qualities 10,25,50,75,90,95

Benchmark encode/decode throughput:
    python -m jpeg_codec.cli bench input.png [--runs 5]

Compare subsampling modes:
    python -m jpeg_codec.cli compare input.png [--quality 85]

Use a config file:
    python -m jpeg_codec.cli encode input.png output.jpg --config settings.json

Global options:
    -v, --verbose   Enable debug logging
"""

import argparse
import sys
import os
import json
import numpy as np

# We need to load/save images.  Try PIL first, fall back to a simple PPM
# reader/writer for environments without PIL.
try:
    from PIL import Image
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

from .logging_setup import setup_logging


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


def _load_config_if_provided(args) -> dict:
    """Load config from --config file if provided, merge with CLI args."""
    config_kwargs = {}
    if hasattr(args, "config") and args.config:
        from .config import load_config
        cfg = load_config(args.config)
        config_kwargs = cfg.to_dict()
    # CLI args override config file.
    if hasattr(args, "quality") and args.quality is not None:
        config_kwargs["quality"] = args.quality
    if hasattr(args, "sampling") and args.sampling is not None:
        config_kwargs["sampling"] = args.sampling
    if hasattr(args, "comment") and args.comment is not None:
        config_kwargs["comment"] = args.comment
    if hasattr(args, "restart") and args.restart is not None:
        config_kwargs["restart_interval"] = args.restart
    return config_kwargs


def cmd_encode(args):
    from jpeg_codec import encode_image
    img = _load_image(args.input)
    kwargs = _load_config_if_provided(args)
    data = encode_image(img, **kwargs)
    with open(args.output, "wb") as f:
        f.write(data)
    orig_size = os.path.getsize(args.input)
    jpeg_size = len(data)
    ratio = orig_size / jpeg_size if jpeg_size else 0
    print(f"Encoded {args.input} -> {args.output}")
    print(f"  Original: {orig_size} bytes")
    print(f"  JPEG:     {jpeg_size} bytes")
    print(f"  Ratio:    {ratio:.2f}:1")
    q = kwargs.get("quality", 85)
    s = kwargs.get("sampling", "4:2:0")
    print(f"  Quality:  {q}, Sampling: {s}")
    if kwargs.get("comment"):
        print(f"  Comment:  {kwargs['comment']}")


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
    from jpeg_codec.metrics import quality_report
    orig = _load_image(args.input)
    kwargs = _load_config_if_provided(args)
    jpeg_data = encode_image(orig, **kwargs)
    recon = decode_image(jpeg_data)
    orig_size = orig.nbytes
    print(f"Round-trip: {args.input}")
    q = kwargs.get("quality", 85)
    s = kwargs.get("sampling", "4:2:0")
    print(f"  Quality:  {q}, Sampling: {s}")
    print(f"  Original: {orig_size} bytes")
    print(f"  JPEG:     {len(jpeg_data)} bytes")

    if args.metrics:
        report = quality_report(orig, recon, orig_size, len(jpeg_data))
        print(f"  MSE:      {report['mse']:.2f}")
        print(f"  RMSE:     {report['rmse']:.2f}")
        print(f"  PSNR:     {report['psnr_db']:.2f} dB")
        print(f"  SSIM:     {report['ssim']:.4f}")
        print(f"  Ratio:    {report['compression_ratio']:.2f}:1")
        print(f"  BPP:      {report['bits_per_pixel']:.2f}")
    else:
        from jpeg_codec.metrics import psnr
        p = psnr(orig, recon)
        ratio = orig_size / len(jpeg_data)
        print(f"  PSNR:     {p:.2f} dB")
        print(f"  Ratio:    {ratio:.2f}:1")

    if args.output:
        _save_image(args.output, recon)
        print(f"  Saved:    {args.output}")


def cmd_info(args):
    from jpeg_codec.info import get_info
    with open(args.input, "rb") as f:
        data = f.read()
    info = get_info(data)

    print(f"File: {args.input}")
    print(f"  Size:       {info.file_size} bytes")
    print(f"  Dimensions: {info.width}x{info.height}")
    print(f"  Components: {info.num_components}")
    print(f"  Process:    {info.encoding_process}")
    print(f"  Sampling:   {info.sampling_string}")
    if info.jfif_version:
        print(f"  JFIF:       {info.jfif_version[0]}.{info.jfif_version[1]}")
    if info.density_units:
        units_str = {1: "DPI", 2: "DPCM"}.get(info.density_units, "unknown")
        print(f"  Density:    {info.x_density}x{info.y_density} {units_str}")
    if info.comment:
        print(f"  Comment:    {info.comment}")
    if info.restart_interval:
        print(f"  Restart:    every {info.restart_interval} MCUs")
    print(f"  Q tables:   {list(info.quant_tables.keys())}")
    print(f"  DC Huffman: {list(info.huffman_dc_tables.keys())}")
    print(f"  AC Huffman: {list(info.huffman_ac_tables.keys())}")
    print(f"  Markers:")
    for name, offset in info.markers:
        print(f"    {name:12s} at offset {offset}")


def cmd_sweep(args):
    from jpeg_codec.benchmark import quality_sweep
    img = _load_image(args.input)
    qualities = [int(q) for q in args.qualities.split(",")]
    results = quality_sweep(img, qualities=qualities, sampling=args.sampling)
    print(f"Quality |  PSNR (dB) | SSIM    |  Size  |   Ratio  |   BPP")
    print(f"--------|------------|---------|--------|----------|--------")
    for r in results:
        print(
            f"  {r['quality']:5d} | "
            f"{r['psnr_db']:10.2f} | "
            f"{r['ssim']:.4f}  | "
            f"{r['compressed_bytes']:6d} | "
            f"{r['compression_ratio']:8.2f} | "
            f"{r['bits_per_pixel']:6.2f}"
        )


def cmd_bench(args):
    from jpeg_codec.benchmark import benchmark
    img = _load_image(args.input)
    result = benchmark(img, quality=args.quality, sampling=args.sampling,
                       runs=args.runs)
    print(f"Benchmark: {args.input}")
    print(f"  Image:        {result['image_size']}")
    print(f"  Quality:      {result['quality']}")
    print(f"  Sampling:     {result['sampling']}")
    print(f"  Encode:       {result['encode_time_s']:.4f}s "
          f"({result['encode_mpix_per_s']:.2f} Mpix/s)")
    print(f"  Decode:       {result['decode_time_s']:.4f}s "
          f"({result['decode_mpix_per_s']:.2f} Mpix/s)")
    print(f"  Compressed:   {result['compressed_bytes']} bytes")
    print(f"  Ratio:        {result['compression_ratio']:.2f}:1")


def cmd_compare(args):
    from jpeg_codec.benchmark import compare_sampling
    img = _load_image(args.input)
    results = compare_sampling(img, quality=args.quality)
    if not results:
        print("Cannot compare sampling modes for grayscale images.")
        return
    print(f"Sampling |  PSNR (dB) | SSIM    |  Size  |   Ratio")
    print(f"---------|------------|---------|--------|----------")
    for r in results:
        print(
            f"  {r['sampling']:5s} | "
            f"{r['psnr_db']:10.2f} | "
            f"{r['ssim']:.4f}  | "
            f"{r['compressed_bytes']:6d} | "
            f"{r['compression_ratio']:8.2f}"
        )


def cmd_config_show(args):
    """Display the default or loaded config."""
    from jpeg_codec.config import EncodingConfig, load_config
    if args.config:
        cfg = load_config(args.config)
    else:
        cfg = EncodingConfig()
    print(json.dumps(cfg.to_dict(), indent=2))


def cmd_config_init(args):
    """Create a default config file."""
    from jpeg_codec.config import EncodingConfig, save_config
    cfg = EncodingConfig(
        quality=args.quality,
        sampling=args.sampling,
        comment=args.comment,
    )
    save_config(cfg, args.output)
    print(f"Config saved to {args.output}")


def main():
    parser = argparse.ArgumentParser(
        prog="jpeg_codec.cli",
        description="From-scratch JPEG encoder/decoder with quality metrics",
        epilog="Use -v for verbose (debug) output.",
    )
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    # --- encode ---
    p_enc = sub.add_parser("encode", help="Encode image to JPEG")
    p_enc.add_argument("input")
    p_enc.add_argument("output")
    p_enc.add_argument("--quality", type=int, default=None,
                       help="Quality 1-100 (default: 85)")
    p_enc.add_argument("--sampling", default=None,
                       choices=["4:4:4", "4:2:2", "4:2:0", "4:1:1"],
                       help="Chroma subsampling (default: 4:2:0)")
    p_enc.add_argument("--comment", default=None,
                       help="Comment to embed in COM marker")
    p_enc.add_argument("--restart", type=int, default=None,
                       help="Restart interval in MCUs (0=disabled)")
    p_enc.add_argument("--config", default=None,
                       help="Path to config file (JSON/YAML/TOML)")
    p_enc.set_defaults(func=cmd_encode)

    # --- decode ---
    p_dec = sub.add_parser("decode", help="Decode JPEG to image")
    p_dec.add_argument("input")
    p_dec.add_argument("output")
    p_dec.set_defaults(func=cmd_decode)

    # --- roundtrip ---
    p_rt = sub.add_parser("roundtrip", help="Encode then decode, report metrics")
    p_rt.add_argument("input")
    p_rt.add_argument("--output", default=None,
                      help="Save reconstructed image to this path")
    p_rt.add_argument("--quality", type=int, default=None)
    p_rt.add_argument("--sampling", default=None,
                      choices=["4:4:4", "4:2:2", "4:2:0", "4:1:1"])
    p_rt.add_argument("--comment", default=None)
    p_rt.add_argument("--restart", type=int, default=None)
    p_rt.add_argument("--config", default=None)
    p_rt.add_argument("--metrics", action="store_true",
                      help="Show full quality report (PSNR, SSIM, MSE, BPP)")
    p_rt.set_defaults(func=cmd_roundtrip)

    # --- info ---
    p_info = sub.add_parser("info", help="Show JPEG metadata and marker structure")
    p_info.add_argument("input")
    p_info.set_defaults(func=cmd_info)

    # --- sweep ---
    p_sweep = sub.add_parser("sweep", help="Quality sweep across multiple levels")
    p_sweep.add_argument("input")
    p_sweep.add_argument("--qualities", default="10,25,50,75,90,95",
                         help="Comma-separated quality values")
    p_sweep.add_argument("--sampling", default="4:2:0",
                         choices=["4:4:4", "4:2:2", "4:2:0", "4:1:1"])
    p_sweep.set_defaults(func=cmd_sweep)

    # --- bench ---
    p_bench = sub.add_parser("bench", help="Benchmark encode/decode speed")
    p_bench.add_argument("input")
    p_bench.add_argument("--quality", type=int, default=85)
    p_bench.add_argument("--sampling", default="4:2:0",
                         choices=["4:4:4", "4:2:2", "4:2:0", "4:1:1"])
    p_bench.add_argument("--runs", type=int, default=3,
                         help="Number of benchmark runs (median is used)")
    p_bench.set_defaults(func=cmd_bench)

    # --- compare ---
    p_cmp = sub.add_parser("compare", help="Compare subsampling modes")
    p_cmp.add_argument("input")
    p_cmp.add_argument("--quality", type=int, default=85)
    p_cmp.set_defaults(func=cmd_compare)

    # --- config ---
    p_cfg = sub.add_parser("config", help="Config file management")
    cfg_sub = p_cfg.add_subparsers(dest="config_command", required=True)
    p_cfg_show = cfg_sub.add_parser("show", help="Show current config")
    p_cfg_show.add_argument("--config", default=None)
    p_cfg_show.set_defaults(func=cmd_config_show)
    p_cfg_init = cfg_sub.add_parser("init", help="Create a default config file")
    p_cfg_init.add_argument("output", help="Output config file path")
    p_cfg_init.add_argument("--quality", type=int, default=85)
    p_cfg_init.add_argument("--sampling", default="4:2:0",
                            choices=["4:4:4", "4:2:2", "4:2:0", "4:1:1"])
    p_cfg_init.add_argument("--comment", default=None)
    p_cfg_init.set_defaults(func=cmd_config_init)

    args = parser.parse_args()

    if args.verbose:
        setup_logging(level=10)  # DEBUG level

    args.func(args)


if __name__ == "__main__":
    main()