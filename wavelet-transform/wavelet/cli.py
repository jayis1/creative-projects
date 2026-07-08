"""
Command-line interface for the wavelet-transform toolkit.

Subcommands:
  info         - Show wavelet filter information
  decompose    - Decompose a signal (1-D)
  denoise      - Denoise a signal
  compress     - Compress a signal
  decompress   - Decompress a signal
  packets      - Wavelet packet decomposition
  visualize    - ASCII visualization of coefficients
  benchmark    - Benchmark transform speed
  cwt          - Continuous wavelet transform (scalogram)
  analyze      - Analyze coefficient statistics
  signals      - List or plot available test signals
  config       - Generate or validate a config file
  compare      - Compare wavelets on the same signal
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
from .swt import SWT, cycle_spin_denoise
from .cwt import cwt, icwt, Morlet, MexicanHat, Paul, DOG
from .packets import WaveletPacket
from .threshold import Threshold, soft, hard, garrote, estimate_sigma
from .denoise import denoise1d, denoise2d
from .compress import compress1d, decompress1d, serialize, deserialize, CompressedSignal
from .signals import generate, list_signals
from .analysis import analyze, compare_wavelets
from .config import WaveletConfig, load_config, save_config, DEFAULT_CONFIG
from .utils import energy, entropy, mse, psnr, snr, rmse
from .logging_utils import get_logger, set_verbose

logger = get_logger("cli")


def _generate_signal(kind: str, n: int, noise: float = 0.0) -> list[float]:
    """Generate a test signal (delegates to wavelet.signals)."""
    return generate(kind, n, noise=noise, seed=42)


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
    # Check perfect reconstruction condition
    # Sum of dec_lo * rec_lo should be ~1 (at zero lag) for orthogonal
    if w.filter_length == w.rec_filter_length:
        cross = sum(a * b for a, b in zip(w.dec_lo, w.rec_lo))
        print(f"  Cross-correlation at lag 0: {cross:.6f}")


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
    clean = _generate_signal(args.signal, args.length, 0.0)
    noisy = _generate_signal(args.signal, args.length, args.noise)
    method = Threshold(args.method)
    func = {"soft": soft, "hard": hard, "garrote": garrote}[args.threshold_func]

    if args.cycle_spin:
        denoised = cycle_spin_denoise(noisy, args.wavelet, args.level,
                                      method, n_shifts=args.n_shifts)
    else:
        denoised = denoise1d(noisy, args.wavelet, args.level, method, func, args.transform)

    print(f"Denoising {args.signal} signal (n={args.length}), noise σ={args.noise}")
    print(f"  Wavelet: {args.wavelet}, level: {args.level}, method: {args.method}")
    print(f"  Threshold function: {args.threshold_func}")
    print(f"  Transform: {args.transform}")
    if args.cycle_spin:
        print(f"  Cycle spinning: {args.n_shifts} shifts")
    print(f"  Noisy signal SNR:    {snr(clean, noisy):.2f} dB")
    print(f"  Denoised signal SNR: {snr(clean, denoised):.2f} dB")
    print(f"  Denoised MSE: {mse(clean, denoised):.6f}")
    print(f"  Noisy MSE:   {mse(clean, noisy):.6f}")
    if args.output:
        with open(args.output, "w") as f:
            json.dump({"clean": clean, "noisy": noisy, "denoised": denoised}, f, indent=2)
        print(f"  Saved to {args.output}")


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
    wavelets_to_test = ["haar", "db4", "sym4", "coif2", "db8"]
    for wname in wavelets_to_test:
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

        # MODWT
        mod = MODWT(w)
        t0 = time.perf_counter()
        for _ in range(args.iterations):
            result_m = mod.decompose(sig, level=3)
        t1 = time.perf_counter()
        modwt_time = (t1 - t0) / args.iterations * 1000
        recon_m = mod.reconstruct(result_m)
        err_m = mse(sig, recon_m)
        print(f"  {wname:6s} MODWT: {modwt_time:7.2f} ms/iter, reconstruction MSE: {err_m:.2e}")


def cmd_cwt(args):
    """Continuous wavelet transform scalogram."""
    sig = _generate_signal(args.signal, args.length, args.noise)
    result = cwt(sig, args.wavelet, dt=args.dt, dj=args.dj)
    power = result.power
    print(f"CWT of {args.signal} signal (n={args.length}), wavelet={result.wavelet_name}")
    print(f"  Scales: {len(result.scales)} ({result.scales[0]:.3f} to {result.scales[-1]:.3f})")
    print(f"  Scalogram shape: {len(power)} x {len(power[0]) if power else 0}")
    # ASCII scalogram (downsampled)
    print("\n  Scalogram (ASCII, downsampled):")
    max_power = max((p for row in power for p in row), default=1.0)
    # Show every Nth scale and every Mth time
    scale_step = max(1, len(power) // 20)
    time_step = max(1, args.length // 60)
    chars = " .:-=+*#%@"
    for si in range(0, len(power), scale_step):
        row = power[si]
        line = ""
        for ti in range(0, len(row), time_step):
            level = int(row[ti] / max_power * (len(chars) - 1))
            line += chars[max(0, min(len(chars) - 1, level))]
        scale_val = result.scales[si]
        print(f"  s={scale_val:6.2f} |{line}")
    # Reconstruction
    recon = icwt(result)
    err = mse(sig, recon)
    print(f"\n  Reconstruction MSE: {err:.6f}")
    print(f"  Reconstruction SNR: {snr(sig, recon):.2f} dB")


def cmd_analyze(args):
    """Analyze coefficient statistics."""
    sig = _generate_signal(args.signal, args.length, args.noise)
    dwt = DWT(args.wavelet)
    result = dwt.decompose(sig, args.level)
    analysis = analyze(result)
    print(analysis.summary())
    # Scale correlation matrix
    print("\nScale correlation matrix:")
    corr = analysis.scale_corr
    if corr:
        header = "       " + "  ".join(f"D{i+1:>3d}" for i in range(len(corr)))
        print(header)
        for i, row in enumerate(corr):
            vals = "  ".join(f"{v:6.3f}" for v in row)
            print(f"  D{i+1:>3d}  {vals}")


def cmd_signals(args):
    """List or plot available test signals."""
    if args.list:
        print("Available signals:")
        for name in list_signals():
            print(f"  {name}")
        return
    sig = _generate_signal(args.signal, args.length, args.noise)
    print(f"Signal: {args.signal} (n={args.length}, noise={args.noise})")
    print(f"  Mean: {sum(sig)/len(sig):.4f}")
    print(f"  Energy: {energy(sig):.4f}")
    print(f"  Entropy: {entropy(sig):.4f}")
    print(f"  Min: {min(sig):.4f}, Max: {max(sig):.4f}")
    # ASCII plot
    max_val = max(abs(v) for v in sig) or 1.0
    step = max(1, len(sig) // 60)
    print("\n  ASCII plot:")
    for v in sig[::step][:60]:
        bar_len = int(abs(v) / max_val * 30)
        if v >= 0:
            print(f"  {'':>30s}|{'+' * bar_len}")
        else:
            print(f"  {'-' * bar_len:>30s}|")


def cmd_config(args):
    """Generate or validate a config file."""
    if args.generate:
        config = DEFAULT_CONFIG
        if args.wavelet:
            config.wavelet = args.wavelet
        if args.level:
            config.level = args.level
        save_config(config, args.generate)
        print(f"Config saved to {args.generate}")
        return
    if args.validate:
        config = load_config(args.validate)
        errors = config.validate()
        if errors:
            print("Config validation FAILED:")
            for e in errors:
                print(f"  ✗ {e}")
            sys.exit(1)
        else:
            print("Config validation PASSED")
            print(f"  Wavelet: {config.wavelet}")
            print(f"  Transform: {config.transform}")
            print(f"  Level: {config.level}")


def cmd_compare(args):
    """Compare wavelets on the same signal."""
    sig = _generate_signal(args.signal, args.length, args.noise)
    wavelet_names = args.wavelets.split(",")
    results = compare_wavelets(sig, wavelet_names, args.level)
    print(f"Comparing {len(results)} wavelets on {args.signal} signal (n={args.length})")
    print(f"\n{'Wavelet':<10} {'Total Energy':>14} {'N Scales':>10} "
          f"{'Approx Energy':>14} {'Detail Energy':>14}")
    print("-" * 66)
    for name, analysis in results.items():
        detail_energy = sum(s.energy for s in analysis.stats[:-1])
        approx_energy = analysis.stats[-1].energy if analysis.stats else 0
        print(f"{name:<10} {analysis.total_energy:>14.6f} {analysis.n_scales:>10d} "
              f"{approx_energy:>14.6f} {detail_energy:>14.6f}")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="wavelet-transform",
        description="Wavelet transform toolkit: DWT, MODWT, SWT, CWT, packets, "
                    "denoising, compression, analysis")
    parser.add_argument("--version", action="version", version="wavelet-transform 2.0.0")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    sub = parser.add_subparsers(dest="command", required=True)

    # info
    p = sub.add_parser("info", help="Show wavelet filter information")
    p.add_argument("--wavelet", "-w", default="db4", help="Wavelet name (default: db4)")
    p.set_defaults(func=cmd_info)

    # decompose
    p = sub.add_parser("decompose", help="Decompose a signal")
    p.add_argument("--signal", "-s", default="sine",
                   help=f"Signal type (default: sine). Use 'signals --list' to see all.")
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
    p.add_argument("--transform", default="dwt", choices=["dwt", "modwt", "swt"])
    p.add_argument("--cycle-spin", action="store_true",
                   help="Use cycle-spinning denoising (translation-invariant)")
    p.add_argument("--n-shifts", type=int, default=16,
                   help="Number of shifts for cycle spinning")
    p.add_argument("--output", "-o", help="Save results to JSON")
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

    # cwt
    p = sub.add_parser("cwt", help="Continuous wavelet transform scalogram")
    p.add_argument("--signal", "-s", default="chirp",
                   help="Signal type (chirp is good for CWT)")
    p.add_argument("--length", "-n", type=int, default=256)
    p.add_argument("--wavelet", "-w", default="morlet",
                   choices=["morlet", "mexhat", "paul", "paul4", "dog2", "dog4"])
    p.add_argument("--dt", type=float, default=1.0, help="Sampling interval")
    p.add_argument("--dj", type=float, default=0.125, help="Scale spacing (log2)")
    p.add_argument("--noise", type=float, default=0.0)
    p.set_defaults(func=cmd_cwt)

    # analyze
    p = sub.add_parser("analyze", help="Analyze coefficient statistics")
    p.add_argument("--signal", "-s", default="sine")
    p.add_argument("--length", "-n", type=int, default=256)
    p.add_argument("--wavelet", "-w", default="db4")
    p.add_argument("--level", "-l", type=int, default=None)
    p.add_argument("--noise", type=float, default=0.0)
    p.set_defaults(func=cmd_analyze)

    # signals
    p = sub.add_parser("signals", help="List or plot available test signals")
    p.add_argument("--list", action="store_true", help="List all available signals")
    p.add_argument("--signal", "-s", default="sine")
    p.add_argument("--length", "-n", type=int, default=128)
    p.add_argument("--noise", type=float, default=0.0)
    p.set_defaults(func=cmd_signals)

    # config
    p = sub.add_parser("config", help="Generate or validate a config file")
    p.add_argument("--generate", metavar="PATH",
                   help="Generate a default config file at PATH")
    p.add_argument("--validate", metavar="PATH",
                   help="Validate a config file at PATH")
    p.add_argument("--wavelet", "-w", default=None, help="Wavelet for generated config")
    p.add_argument("--level", "-l", type=int, default=None, help="Level for generated config")
    p.set_defaults(func=cmd_config)

    # compare
    p = sub.add_parser("compare", help="Compare wavelets on the same signal")
    p.add_argument("--signal", "-s", default="sine")
    p.add_argument("--length", "-n", type=int, default=256)
    p.add_argument("--wavelets", default="haar,db2,db4,db8,sym4,coif2",
                   help="Comma-separated wavelet names")
    p.add_argument("--level", "-l", type=int, default=None)
    p.add_argument("--noise", type=float, default=0.0)
    p.set_defaults(func=cmd_compare)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "verbose", False):
        set_verbose(True)
    args.func(args)


if __name__ == "__main__":
    main()