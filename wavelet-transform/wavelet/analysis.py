"""
Coefficient analysis tools for wavelet transforms.

Provides per-scale statistics, energy distribution, wavelet variance,
scale-to-scale correlation, and comparison between different wavelet
decompositions — useful for feature extraction and signal characterization.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

from .dwt import DWTResult
from .modwt import MODWTResult

__all__ = [
    "ScaleStats",
    "scale_statistics",
    "energy_distribution",
    "wavelet_variance",
    "scale_correlation",
    "compare_wavelets",
    "AnalysisResult",
]


@dataclass
class ScaleStats:
    """Statistics for a single scale's coefficients."""

    level: int = 0
    n: int = 0
    mean: float = 0.0
    std: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0
    energy: float = 0.0
    entropy: float = 0.0
    l1_norm: float = 0.0
    l2_norm: float = 0.0
    kurtosis: float = 0.0
    skewness: float = 0.0
    n_nonzero: int = 0
    sparsity: float = 0.0  # fraction of zero (or near-zero) coefficients


def _entropy(coeffs: list[float]) -> float:
    """Shannon entropy of normalized |coeff|²."""
    if not coeffs:
        return 0.0
    s = sum(abs(c) ** 2 for c in coeffs)
    if s == 0:
        return 0.0
    ent = 0.0
    for c in coeffs:
        p = (c ** 2) / s
        if p > 0:
            ent -= p * math.log2(p)
    return ent


def _moments(coeffs: list[float]) -> tuple[float, float, float, float]:
    """Return (mean, std, skewness, kurtosis_excess) of the coefficients."""
    n = len(coeffs)
    if n == 0:
        return 0.0, 0.0, 0.0, 0.0
    mean = sum(coeffs) / n
    var = sum((c - mean) ** 2 for c in coeffs) / n
    std = math.sqrt(var) if var > 0 else 0.0
    if std == 0:
        return mean, 0.0, 0.0, 0.0
    skew = sum(((c - mean) / std) ** 3 for c in coeffs) / n
    kurt = sum(((c - mean) / std) ** 4 for c in coeffs) / n - 3.0  # excess kurtosis
    return mean, std, skew, kurt


def scale_statistics(
    result: DWTResult | MODWTResult,
    threshold: float = 1e-15,
) -> list[ScaleStats]:
    """Compute detailed statistics for each scale of a wavelet decomposition.

    Parameters
    ----------
    result : DWTResult or MODWTResult from a decomposition
    threshold : absolute value below which a coefficient is counted as "zero"

    Returns a list of ScaleStats, one per detail level + one for the
    approximation (last entry).
    """
    stats: list[ScaleStats] = []
    all_coeffs = list(result.details) + [result.approx]
    for level, coeffs in enumerate(all_coeffs):
        n = len(coeffs)
        if n == 0:
            stats.append(ScaleStats(level=level, n=0))
            continue
        mean, std, skew, kurt = _moments(coeffs)
        e = sum(c * c for c in coeffs)
        ent = _entropy(coeffs)
        l1 = sum(abs(c) for c in coeffs)
        l2 = math.sqrt(e)
        n_nonzero = sum(1 for c in coeffs if abs(c) > threshold)
        sparsity = 1.0 - (n_nonzero / n) if n > 0 else 0.0
        stats.append(ScaleStats(
            level=level, n=n, mean=mean, std=std,
            min_val=min(coeffs), max_val=max(coeffs),
            energy=e, entropy=ent, l1_norm=l1, l2_norm=l2,
            kurtosis=kurt, skewness=skew,
            n_nonzero=n_nonzero, sparsity=sparsity,
        ))
    return stats


def energy_distribution(result: DWTResult | MODWTResult) -> list[float]:
    """Return the fraction of total energy at each scale.

    Returns a list summing to 1.0 (approx): [E_detail_1/N, ..., E_detail_L/N, E_approx/N]
    where N is the total energy across all scales.
    """
    energies = []
    total = 0.0
    for d in result.details:
        e = sum(c * c for c in d)
        energies.append(e)
        total += e
    e_approx = sum(c * c for c in result.approx)
    energies.append(e_approx)
    total += e_approx
    if total == 0:
        return [0.0] * len(energies)
    return [e / total for e in energies]


def wavelet_variance(result: MODWTResult | DWTResult,
                     n: int | None = None) -> list[float]:
    """Estimate the wavelet variance (power) at each scale.

    The wavelet variance is defined as the variance of the detail
    coefficients at each scale (Percival & Walden, 2000).  For the MODWT,
    this is an unbiased estimator of the spectral power at the
    corresponding frequency band.

    Returns a list of variances, one per detail level.
    """
    variances = []
    for d in result.details:
        nd = len(d)
        if nd == 0:
            variances.append(0.0)
            continue
        mean = sum(d) / nd
        var = sum((c - mean) ** 2 for c in d) / nd
        variances.append(var)
    return variances


def scale_correlation(result: DWTResult | MODWTResult) -> list[list[float]]:
    """Compute the cross-correlation matrix between scales.

    Returns a symmetric L×L matrix where entry [i][j] is the Pearson
    correlation between detail coefficients at scales i and j (upsampled
    to the same length if needed).
    """
    n_scales = len(result.details)
    if n_scales == 0:
        return []
    # Upsample all details to the maximum length
    max_len = max(len(d) for d in result.details)
    upsampled = []
    for d in result.details:
        if len(d) == max_len:
            upsampled.append(list(d))
        else:
            # Linear interpolation upsampling
            ratio = max_len / len(d)
            up = []
            for i in range(max_len):
                src_idx = i / ratio
                lo = int(src_idx)
                hi = min(lo + 1, len(d) - 1)
                frac = src_idx - lo
                up.append(d[lo] * (1 - frac) + d[hi] * frac)
            upsampled.append(up)

    # Compute correlation matrix
    corr = [[0.0] * n_scales for _ in range(n_scales)]
    for i in range(n_scales):
        for j in range(i, n_scales):
            c = _pearson_corr(upsampled[i], upsampled[j])
            corr[i][j] = c
            corr[j][i] = c
    return corr


def _pearson_corr(x: list[float], y: list[float]) -> float:
    """Pearson correlation coefficient between two equal-length series."""
    n = len(x)
    if n != len(y) or n == 0:
        return 0.0
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    dx = math.sqrt(sum((xi - mx) ** 2 for xi in x))
    dy = math.sqrt(sum((yi - my) ** 2 for yi in y))
    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)


@dataclass
class AnalysisResult:
    """Comprehensive analysis of a wavelet decomposition."""
    stats: List[ScaleStats] = field(default_factory=list)
    energy_dist: List[float] = field(default_factory=list)
    wavelet_var: List[float] = field(default_factory=list)
    scale_corr: List[List[float]] = field(default_factory=list)
    total_energy: float = 0.0
    n_scales: int = 0

    def summary(self) -> str:
        """Return a formatted text summary of the analysis."""
        lines = [
            f"Wavelet Analysis Summary ({self.n_scales} scales)",
            "=" * 50,
            f"Total energy: {self.total_energy:.6f}",
            "",
            f"{'Scale':>6} {'N':>6} {'Mean':>10} {'Std':>10} "
            f"{'Energy':>12} {'Entropy':>10} {'Sparsity':>10}",
            "-" * 70,
        ]
        for s in self.stats:
            lines.append(
                f"{s.level:>6} {s.n:>6} {s.mean:>10.4f} {s.std:>10.4f} "
                f"{s.energy:>12.6f} {s.entropy:>10.4f} {s.sparsity:>10.2%}"
            )
        lines.append("")
        lines.append("Energy distribution: " +
                     ", ".join(f"{e:.4f}" for e in self.energy_dist))
        lines.append("Wavelet variance:    " +
                     ", ".join(f"{v:.6f}" for v in self.wavelet_var))
        return "\n".join(lines)


def compare_wavelets(signal: list[float],
                     wavelet_names: list[str],
                     level: int | None = None) -> dict[str, AnalysisResult]:
    """Compare wavelet decompositions of the same signal across wavelet families.

    Returns a dict mapping wavelet name → AnalysisResult.
    """
    from .dwt import DWT
    results: dict[str, AnalysisResult] = {}
    for wname in wavelet_names:
        try:
            dwt = DWT(wname)
            decomp = dwt.decompose(signal, level)
            analysis = analyze(decomp)
            results[wname] = analysis
        except (ValueError, Exception):
            continue
    return results


def analyze(result: DWTResult | MODWTResult) -> AnalysisResult:
    """Run a comprehensive analysis of a wavelet decomposition."""
    stats = scale_statistics(result)
    edist = energy_distribution(result)
    wvar = wavelet_variance(result)
    scorr = scale_correlation(result)
    total = sum(s.energy for s in stats)
    return AnalysisResult(
        stats=stats, energy_dist=edist, wavelet_var=wvar,
        scale_corr=scorr, total_energy=total, n_scales=len(result.details),
    )