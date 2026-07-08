"""
Command-line interface for the wavelet-transform toolkit.

Subcommands:
  decompose    - Decompose a signal (1-D)
  reconstruct   - Reconstruct from decomposition
  denoise       - Denoise a signal
  compress      - Compress a signal
  decompress    - Decompress a signal
  packets       - Wavelet packet decomposition
  visualize     - ASCII visualization of coefficients
  benchmark     - Benchmark transform speed
  info          - Show wavelet info
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time

from .wavelets import wavelet, Wavelet, Haar, Daubechies, Symlet, Coiflet, Biorthogonal
from .dwt import DWT
from .modwt import MODWT
from .packets import WaveletPacket
from .threshold import Threshold, soft, hard, garrote
from .denoise import denoise1d, denoise2d
from .compress import compress1d, decompress1d, serialize, deserialize, CompressedSignal
from .utils import energy, entropy, mse, psnr, snr, rmse


def _generate_signal(kind: str, n: int, noise: float = 0.0) -> list[float]:
    """Generate a test signal."""
    random.seed(42)
    sig = []
    for i in range(n):
        t = i / n
        if kind == "sine":
            val = math.sin(2 * math.pi * 4 * t)
        elif kind == "chirp":
            val = math.sin(2 * math.pi * (1 + 10 * t) * t)
        elif kind == "square":
            val = 1.0 if math.sin(2 * math.pi * 4 * t) > 0 else -1.0
        elif kind == "pulse":
            val = 1.0 if n // 3 < i < 2 * n // 3 else 0.0
        elif kind == "ramp":
            val = t
        elif kind == "step":
            val = 0.0 if i < n // 2 else 1.0
        else:
            val = math.sin(2 * math.pi * 4 * t) + 0.3 * math.sin(2 * math.pi * 16 * t)
        if noise > 0:
            val += random.gauss(0, noise)
        sig.append(val)
    return sig


def _print_coeffs(coeffs: list[float], prefix: str = "") -> None:
    """Print coefficients in a compact form."""
    line = ", ".join(f"{c:.4f}" for c in coeffs[:20])
    if len(coeffs) > 20:
        line += ", ..."
    print(f"  {prefix}[{len(coeffs)}]: {line}")


def _ascii_bar(value: float, max_val: float, width: int = 40) -> str:
    """Generate an ASCII bar for a coefficient value."""
    if max_val == 0:
        return ""
    scaled = int(abs(value) / max_val * width)
    if value > 0:
        return "+" * scaled
    elif value < 0:
        return "-" * scaled
    return ""


def cmd_info(args):
    """Show wavelet information."""
    w = wavelet(args.wavelet)
    print(f"Wavelet: {w.name}")
    print(f"  Filter length: {w.filter_length}")
    print(f"  Vanishing moments: {w.vanishing_moments}")
    print(f"  Orthogonal: {w.orthogonal}")
    print(f"  Biorthogonal: {w.biorthogonal}")
    print(f"  Decomposition low-pass:  {[f'{c:.6f}' for c in w.dec_lo]}")
    print(f"  Decomposition high-pass: {[f'{c:.6f}' for c in w.dec_hi]}")
    print(f"  Reconstruction low-pass: {[f'{c:.6f}' for c in w.rec_lo]}")
    print(f"  Reconstruction high-pass:{[f'{c:.6f}' for c in w.rec_hi]}")
    # Check orthogonality
    if w.orthogonal:
        s = sum(c * c for c in w.dec_lo)
        print(f"  Filter energy (should be 1.0): {s:.6f}")


def cmd_decompose(args):
    """Decompose a signal."""
    sig = _generate_signal(args.signal, args.length, args.noise)
    dwt = DWT(args.wavelet)
    result = dwt.decompose(sig, args.level)
    print(f"Decomposition of {args.signal} signal (n={args.length}), wavelet={args.wavelet}")
    print(f"  Level: {result.level}")
    print(f"  Approximation [{len(result.approx)}]:")
    _print_coeffs(result.approx, "  approx = ")
    for i, detail in enumerate(result.details):
        print(f"  Level {i+1} detail [{len(detail)}]:")
        _print_coeffs(detail, f"  d{i+1} = ")
    if args.json:
        data = {"wavelet": args.wavelet, "level": result.level,
                "approx": result.approx, "details": result.details}
        with open(args.json, "w") as f:
            json.dump(data, f, indent=2)
        print(f"  Saved to {args.json}")


def cmd_denoise(args):
    """Denoise a signal."""
    random.seed(42)
    clean = _generate_signal(args.signal, args.length, 0.0)
    noisy = _generate_signal(args.signal, args.length, args.noise)
    method = Threshold(args.method)
    func = {"soft": soft, "hard": hard, "garrote": garrote}[args.threshold_func]
    denoised = denoise1d(noisy, args.wavelet, args.level, method, func, args.transform)
    print(f"Denoising {args.signal} signal (n={args.length}), noise σ={args.noise}")
    print(f"  Wavelet: {args.wavelet}, level: {args.level}, method: {args.method}")
    print(f"  Threshold function: {args.threshold_func}")
    print(f"  Transform: {args.transform}")
    print(f"  Noisy signal SNR:    {snr(clean, noisy):.2f} dB")
    print(f"  Denoised signal SNR: {snr(clean, denoised):.2f} dB")
    print(f"  Denoised MSE: {mse(clean, denoised):.6f}")
    print(f"  Noisy MSE:   {mse(clean, noisy):.6f}")


def cmd_compress(args):
    """Compress a signal."""
    sig = _generate_signal(args.signal, args.length, args.noise)
    compressed = compress1d(sig, args.wavelet, args.level,
                            threshold=args.threshold, keep_ratio=args.keep_ratio)
    print(f"Compressing {args.signal} signal (n={args.length})")
    print(f"  Wavelet: {args.wavelet}, level: {compressed.level}")
    print(f"  Total coefficients: {compressed.n_coeffs_total}")
    print(f"  Non-zero coefficients: {compressed.n_coeffs_kept}")
    print(f"  Sparsity: {compressed.sparsity:.2%}")
    print(f"  Compression ratio: {compressed.compression_ratio:.1f}x")
    # Reconstruct and measure error
    recon = decompress1d(compressed)
    print(f"  Reconstruction MSE: {mse(sig, recon):.6f}")
    print(f"  Reconstruction PSNR: {psnr(sig, recon):.2f} dB")
    if args.output:
        data = serialize(compressed)
        with open(args.output, "wb") as f:
            f.write(data)
        print(f"  Compressed size: {len(data)} bytes (saved to {args.output})")


def cmd_decompress(args):
    """Decompress a signal from a file."""
    with open(args.input, "rb") as f:
        data = f.read()
    compressed = deserialize(data)
    print(f"Decompressing from {args.input}")
    print(f"  Wavelet: {compressed.wavelet_name}")
    print(f"  Original length: {compressed.input_length}")
    print(f"  Level: {compressed.level}")
    print(f"  Non-zero coefficients: {compressed.n_coeffs_kept}/{compressed.n_coeffs_total}")
    signal = decompress1d(compressed)
    print(f"  Reconstructed {len(signal)} samples")
    if args.output:
        with open(args.output, "w") as f:
            json.dump(signal, f)
        print(f"  Saved to {args.output}")


def cmd_packets(args):
    """Wavelet packet decomposition."""
    sig = _generate_signal(args.signal, args.length, args.noise)
    wp = WaveletPacket(args.wavelet)
    result = wp.decompose(sig, args.level)
    print(f"Wavelet packet decomposition of {args.signal} signal (n={args.length})")
    print(f"  Wavelet: {args.wavelet}, level: {result['level']}")
    print(f"  Total packets: {len(result['packets'])}")
    for path in sorted(result["packets"].keys(), key=lambda p: (len(p), p)):
        coeffs = result["packets"][path]
        print(f"    {path or 'root':>6s} [{len(coeffs):3d}]: "
              f"energy={energy(coeffs):.4f}, entropy={entropy(coeffs):.4f}")
    if args.best_basis:
        selected = wp.best_basis(result)
        print(f"  Best basis ({len(selected)} nodes): {selected}")


def cmd_visualize(args):
    """ASCII visualization of DWT coefficients."""
    sig = _generate_signal(args.signal, args.length, args.noise)
    dwt = DWT(args.wavelet)
    result = dwt.decompose(sig, args.level)
    print(f"Visualization of {args.signal} signal DWT (wavelet={args.wavelet})")
    all_coeffs = result.details + [result.approx]
    max_val = max((abs(c) for d in all_coeffs for c in d), default=1.0)
    print(f"Max coefficient magnitude: {max_val:.4f}")
    print()
    labels = [f"D{i+1}" for i in range(len(result.details))] + ["A"]
    for label, coeffs in zip(labels, all_coeffs):
        print(f"{label} [{len(coeffs):3d}]:")
        for c in coeffs[:30]:
            bar = _ascii_bar(c, max_val, 30)
            print(f"  {c:8.4f} |{bar}")
        if len(coeffs) > 30:
            print(f"  ... ({len(coeffs) - 30} more)")
        print()


def cmd_benchmark(args):
    """Benchmark transform speed."""
    print(f"Benchmarking wavelet transforms (n={args.length})")
    for wname in ["haar", "db4", "sym4", "coif2"]:
        w = wavelet(wname)
        sig = [math.sin(2 * math.pi * 4 * i / args.length) for i in range(args.length)]
        # DWT
        dwt = DWT(w)
        t0 = time.perf_counter()
        for _ in range(args.iterations):
            result = dwt.decompose(sig)
        t1 = time.perf_counter()
        dwt_time = (t1 - t0) / args.iterations * 1000
        # Verify reconstruction
        recon = dwt.reconstruct(result)
        err = mse(sig, recon)
        print(f"  {wname:6s} DWT:  {dwt_time:7.2f} ms/iter, reconstruction MSE: {err:.2e}")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="wavelet-transform",
        description="Wavelet transform toolkit: DWT, MODWT, packets, denoising, compression")
    parser.add_argument("--version", action="version", version="wavelet-transform 1.0.0")
    sub = parser.add_subparsers(dest="command", required=True)

    # info
    p = sub.add_parser("info", help="Show wavelet filter information")
    p.add_argument("--wavelet", "-w", default="db4", help="Wavelet name (default: db4)")
    p.set_defaults(func=cmd_info)

    # decompose
    p = sub.add_parser("decompose", help="Decompose a signal")
    p.add_argument("--signal", "-s", default="sine",
                   choices=["sine", "chirp", "square", "pulse", "ramp", "step", "multi"],
                   help="Signal type (default: sine)")
    p.add_argument("--length", "-n", type=int, default=256, help="Signal length")
    p.add_argument("--wavelet", "-w", default="db4")
    p.add_argument("--level", "-l", type=int, default=None)
    p.add_argument("--noise", type=float, default=0.0, help="Noise std dev")
    p.add_argument("--json", help="Save results to JSON file")
    p.set_defaults(func=cmd_decompose)

    # denoise
    p = sub.add_parser("denoise", help="Denoise a signal")
    p.add_argument("--signal", "-s", default="sine")
    p.add_argument("--length", "-n", type=int, default=256)
    p.add_argument("--wavelet", "-w", default="db4")
    p.add_argument("--level", "-l", type=int, default=None)
    p.add_argument("--noise", type=float, default=0.3, help="Noise std dev")
    p.add_argument("--method", "-m", default="bayes",
                   choices=["universal", "sure", "bayes", "minimax"])
    p.add_argument("--threshold-func", "-t", default="soft",
                   choices=["soft", "hard", "garrote"])
    p.add_argument("--transform", default="dwt", choices=["dwt", "modwt"])
    p.set_defaults(func=cmd_denoise)

    # compress
    p = sub.add_parser("compress", help="Compress a signal")
    p.add_argument("--signal", "-s", default="sine")
    p.add_argument("--length", "-n", type=int, default=256)
    p.add_argument("--wavelet", "-w", default="db4")
    p.add_argument("--level", "-l", type=int, default=None)
    p.add_argument("--threshold", type=float, default=None)
    p.add_argument("--keep-ratio", type=float, default=None, help="Fraction to keep")
    p.add_argument("--noise", type=float, default=0.0)
    p.add_argument("--output", "-o", help="Save compressed to file")
    p.set_defaults(func=cmd_compress)

    # decompress
    p = sub.add_parser("decompress", help="Decompress a signal from file")
    p.add_argument("--input", "-i", required=True, help="Compressed file")
    p.add_argument("--output", "-o", help="Save reconstructed signal to JSON")
    p.set_defaults(func=cmd_decompress)

    # packets
    p = sub.add_parser("packets", help="Wavelet packet decomposition")
    p.add_argument("--signal", "-s", default="sine")
    p.add_argument("--length", "-n", type=int, default=256)
    p.add_argument("--wavelet", "-w", default="db4")
    p.add_argument("--level", "-l", type=int, default=3)
    p.add_argument("--noise", type=float, default=0.0)
    p.add_argument("--best-basis", "-b", action="store_true")
    p.set_defaults(func=cmd_packets)

    # visualize
    p = sub.add_parser("visualize", help="ASCII visualization of coefficients")
    p.add_argument("--signal", "-s", default="sine")
    p.add_argument("--length", "-n", type=int, default=64)
    p.add_argument("--wavelet", "-w", default="db4")
    p.add_argument("--level", "-l", type=int, default=3)
    p.add_argument("--noise", type=float, default=0.0)
    p.set_defaults(func=cmd_visualize)

    # benchmark
    p = sub.add_parser("benchmark", help="Benchmark transform speed")
    p.add_argument("--length", "-n", type=int, default=1024)
    p.add_argument("--iterations", "-i", type=int, default=10)
    p.set_defaults(func=cmd_benchmark)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()