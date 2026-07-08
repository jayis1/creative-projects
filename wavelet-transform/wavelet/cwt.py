"""
Continuous Wavelet Transform (CWT).

Unlike the discrete wavelet transform (which produces critically sampled
coefficients), the CWT computes wavelet coefficients at every scale and
every time position, providing a highly redundant but information-rich
time-scale representation (scalogram).

Implemented mother wavelets:
  - **Morlet** (Gabor wavelet): complex, good for oscillatory signals
  - **Mexican Hat** (Ricker / 2nd derivative of Gaussian): real, good
    for peak/edge detection
  - **Paul** (order m): complex, good for phase analysis
  - **DOG** (Derivative of Gaussian, order m): generalization of Mexican Hat

The CWT is computed via direct convolution in the time domain with periodic
boundary extension.  Scales are geometrically spaced.

References
----------
Torrence & Compo (1998), "A Practical Guide to Wavelet Analysis",
*Bull. Amer. Meteor. Soc.*, 79(1), 61-78.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

__all__ = [
    "Morlet",
    "MexicanHat",
    "Paul",
    "DOG",
    "ContinuousWavelet",
    "cwt",
    "icwt",
    "CWTResult",
]


# -------------------------------------------------------------------------
# Mother wavelets
# -------------------------------------------------------------------------
class ContinuousWavelet:
    """Base class for continuous wavelet mother functions."""

    name: str = "base"
    complex: bool = False
    fourier_period_factor: float = 1.0  # factor converting scale to Fourier period

    def __call__(self, t: float, scale: float) -> complex:
        """Evaluate the mother wavelet at dimensionless time ``t / scale``.

        ``t`` is the time offset from the wavelet centre, ``scale`` is the
        dilation.  The function is evaluated at the dimensionless argument
        ``x = t / scale``.
        """
        raise NotImplementedError

    def e_folding_time(self, scale: float) -> float:
        """Decorrelation time (e-folding time) for wavelet at ``scale``."""
        return scale * math.sqrt(2)


class Morlet(ContinuousWavelet):
    """Morlet wavelet (Gabor wavelet): plane wave modulated by a Gaussian.

    ψ(t) = π^(-1/4) · exp(i·ω₀·t) · exp(-t²/2)

    with ω₀ = 6 (default), which makes the wavelet approximately
    admissible (zero mean) and provides a good time-frequency trade-off.
    """

    name = "morlet"
    complex = True
    # Fourier period ≈ 4π / ω₀ · scale for Morlet with ω₀=6
    fourier_period_factor = 4 * math.pi / 6.0

    def __init__(self, omega0: float = 6.0) -> None:
        self.omega0 = omega0
        self.fourier_period_factor = 4 * math.pi / omega0

    def __call__(self, t: float, scale: float) -> complex:
        x = t / scale
        norm = math.pi ** -0.25 / math.sqrt(scale)
        # exp(-x²/2) Gaussian envelope, exp(i ω₀ x) plane wave
        return norm * complex(
            math.cos(self.omega0 * x) * math.exp(-0.5 * x * x),
            math.sin(self.omega0 * x) * math.exp(-0.5 * x * x),
        )


class MexicanHat(ContinuousWavelet):
    """Mexican Hat wavelet (Ricker wavelet = 2nd derivative of Gaussian).

    ψ(t) = (2/√3 · π^(-1/4)) · (1 - t²) · exp(-t²/2)
    """

    name = "mexhat"
    complex = False
    # Fourier period ≈ 2π / √(5/4) · scale for Mexican hat
    fourier_period_factor = 2 * math.pi / math.sqrt(2.5)

    def __call__(self, t: float, scale: float) -> complex:
        x = t / scale
        norm = 2.0 / (math.sqrt(3) * math.pi ** 0.25) / math.sqrt(scale)
        val = norm * (1 - x * x) * math.exp(-0.5 * x * x)
        return complex(val, 0.0)


class Paul(ContinuousWavelet):
    """Paul wavelet of order ``m`` (default m=4).

    Complex wavelet well-suited for phase analysis.
    """

    name = "paul"
    complex = True
    # Fourier period factor for Paul(m): 4π/(2m+1)
    fourier_period_factor = 4 * math.pi / 9.0  # for m=4

    def __init__(self, m: int = 4) -> None:
        if m < 1:
            raise ValueError("Paul wavelet order m must be >= 1")
        self.m = m
        self.name = f"paul{m}"
        self.fourier_period_factor = 4 * math.pi / (2 * m + 1)

    def __call__(self, t: float, scale: float) -> complex:
        x = t / scale
        m = self.m
        # Paul wavelet: ψ_m(t) = 2^m · i^m · m! / √π(2m)! · (1 - it)^(-(m+1))
        # We use the real-valued form of the (1-it)^(-(m+1)) term
        norm = (2 ** m * math.factorial(m) /
                (math.sqrt(math.pi) * math.factorial(2 * m)) /
                math.sqrt(scale))
        # (1 - ix)^(-(m+1)) = [(1+ix)/(1+x²)]^(m+1) · ... 
        # Magnitude: (1 + x²)^(-(m+1)/2)
        # Phase: (m+1) · arctan(x)
        mag = (1 + x * x) ** (-(m + 1) / 2.0)
        phase = (m + 1) * math.atan(x)
        return norm * mag * complex(math.cos(phase), math.sin(phase))


class DOG(ContinuousWavelet):
    """Derivative of Gaussian wavelet of order ``m`` (default m=2 = Mexican Hat).

    For m=1: ψ(t) = t · exp(-t²/2)  (1st derivative, anti-symmetric)
    For m=2: ψ(t) = (1 - t²) · exp(-t²/2)  (Mexican Hat)
    For m=4: 3rd polynomial times Gaussian, etc.
    """

    name = "dog"
    complex = False

    def __init__(self, m: int = 2) -> None:
        if m < 1:
            raise ValueError("DOG order m must be >= 1")
        self.m = m
        self.name = f"dog{m}"
        # Fourier period factor: 2π / √(m + 0.5)
        self.fourier_period_factor = 2 * math.pi / math.sqrt(m + 0.5)

    def __call__(self, t: float, scale: float) -> complex:
        x = t / scale
        m = self.m
        # Hermite polynomial H_m(x) · exp(-x²/2) / √scale
        # H_1(x) = 2x, H_2(x) = 4x²-2 → normalize
        # Use the standard DOG definitions:
        if m == 1:
            norm = 1.0 / math.sqrt(math.pi) / math.sqrt(scale)
            val = norm * x * math.exp(-0.5 * x * x)
        elif m == 2:
            norm = 2.0 / (math.sqrt(3) * math.pi ** 0.25) / math.sqrt(scale)
            val = norm * (1 - x * x) * math.exp(-0.5 * x * x)
        elif m == 4:
            norm = math.sqrt(15.0 / 16.0) / (math.pi ** 0.25) / math.sqrt(scale)
            # 4th derivative of Gaussian: (x^4 - 6x^2 + 3) * exp(-x^2/2)
            val = norm * (x ** 4 - 6 * x * x + 3) * math.exp(-0.5 * x * x)
        elif m == 6:
            norm = math.sqrt(105.0 / 32.0) / (math.pi ** 0.25) / math.sqrt(scale)
            val = norm * (x ** 6 - 15 * x ** 4 + 45 * x * x - 15) * math.exp(-0.5 * x * x)
        else:
            # General case via Hermite polynomial recurrence
            from math import factorial as fac
            h0, h1 = 1.0, 2.0 * x
            for k in range(2, m + 1):
                h0, h1 = h1, 2.0 * x * h1 - 2.0 * k * h0
            val = h1 * math.exp(-0.5 * x * x) / math.sqrt(scale)
        return complex(val, 0.0)


# -------------------------------------------------------------------------
# CWT computation
# -------------------------------------------------------------------------
@dataclass
class CWTResult:
    """Result of a CWT decomposition (scalogram)."""

    coefficients: List[List[complex]] = field(default_factory=list)
    scales: List[float] = field(default_factory=list)
    wavelet_name: str = ""
    input_length: int = 0
    dt: float = 1.0
    dj: float = 0.125
    # For reconstruction
    c0: float = 0.0  # reconstruction constant (depends on wavelet)

    @property
    def n_scales(self) -> int:
        return len(self.scales)

    @property
    def real(self) -> list[list[float]]:
        """Return the real part of the scalogram (power/amplitude)."""
        return [[c.real for c in row] for row in self.coefficients]

    @property
    def imag(self) -> list[list[float]]:
        return [[c.imag for c in row] for row in self.coefficients]

    @property
    def power(self) -> list[list[float]]:
        """Return the wavelet power |W|²."""
        return [[(c.real ** 2 + c.imag ** 2) for c in row]
                for row in self.coefficients]


def _default_scales(n: int, dt: float, dj: float,
                    wavelet: ContinuousWavelet,
                    s0: float | None = None) -> list[float]:
    """Generate geometrically spaced scales.

    The smallest scale s0 is chosen so that the Fourier period ≈ 2·dt
    (Nyquist).  Each subsequent scale is multiplied by 2^dj.
    """
    if s0 is None:
        # Smallest resolvable scale: Fourier period = 2*dt
        # period = fourier_period_factor * scale → scale = period / factor
        s0 = 2 * dt / wavelet.fourier_period_factor
    # Largest scale: such that the wavelet spans the whole signal
    # J = dj * log2(n * dt / s0) / 4  (heuristic from Torrence & Compo)
    j_max = int(math.floor(math.log2(n * dt / s0) / dj))
    scales = [s0 * (2 ** (j * dj)) for j in range(j_max + 1)]
    return scales


def cwt(signal: list[float],
        wavelet: ContinuousWavelet | str | None = None,
        scales: list[float] | None = None,
        dt: float = 1.0,
        dj: float = 0.125) -> CWTResult:
    """Compute the Continuous Wavelet Transform of a 1-D signal.

    Parameters
    ----------
    signal : input signal (real-valued)
    wavelet : mother wavelet (Morlet, MexicanHat, Paul, DOG) or name string.
              Default: Morlet(omega0=6).
    scales : list of scales to use.  If None, auto-generated geometrically.
    dt : sampling interval (for scale interpretation)
    dj : scale spacing in log2 units (for auto-scale generation)

    Returns
    -------
    CWTResult with .coefficients[s][t] = wavelet coefficient at scale s, time t.
    """
    if wavelet is None:
        wavelet = Morlet()
    elif isinstance(wavelet, str):
        wavelet = _str_to_wavelet(wavelet)

    n = len(signal)
    if n == 0:
        raise ValueError("Cannot compute CWT of empty signal")

    if scales is None:
        scales = _default_scales(n, dt, dj, wavelet)

    coefficients: list[list[complex]] = []
    for scale in scales:
        row: list[complex] = [0.0j] * n
        # Wavelet half-width (in samples): ~5*scale/dt is enough for Morlet
        half_width = int(math.ceil(5 * scale / dt))
        for t in range(n):
            acc = 0.0 + 0.0j
            for lag in range(-half_width, half_width + 1):
                idx = (t - lag) % n  # periodic boundary
                w = wavelet(lag * dt, scale)
                acc += signal[idx] * w.conjugate() if wavelet.complex else signal[idx] * complex(w.real, 0)
            # Normalization: dt / scale (Torrence & Compo)
            row[t] = acc * (dt / scale)
        coefficients.append(row)

    # Reconstruction constant (for Morlet, c0 ≈ 0.776)
    c0 = _reconstruction_constant(wavelet)

    return CWTResult(
        coefficients=coefficients,
        scales=list(scales),
        wavelet_name=wavelet.name,
        input_length=n,
        dt=dt,
        dj=dj,
        c0=c0,
    )


def icwt(result: CWTResult) -> list[float]:
    """Inverse Continuous Wavelet Transform (approximate reconstruction).

    Uses the Torrence & Compo reconstruction formula:

        x[t] = (dj · dt^(1/2)) / (c0 · ψ₀(0)) · Σ_j W(s_j, t) / √s_j

    For real wavelets, only the real part of W is used.
    """
    n = result.input_length
    if n == 0:
        return []
    dj = result.dj
    dt = result.dt
    c0 = result.c0
    # ψ₀(0) for Morlet = π^(-1/4); for MexicanHat ≈ 0.867
    psi0 = _psi_at_zero(result.wavelet_name)

    reconstructed = [0.0] * n
    for j, scale in enumerate(result.scales):
        row = result.coefficients[j]
        weight = dj * math.sqrt(dt) / (c0 * psi0) / math.sqrt(scale)
        for t in range(n):
            reconstructed[t] += (row[t].real) * weight

    return reconstructed


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------
def _str_to_wavelet(name: str) -> ContinuousWavelet:
    name = name.strip().lower()
    if name in ("morlet", "morl"):
        return Morlet()
    if name in ("mexhat", "mexican", "ricker", "mexicanhat"):
        return MexicanHat()
    if name.startswith("paul"):
        try:
            m = int(name[4:]) if len(name) > 4 else 4
        except ValueError:
            m = 4
        return Paul(m)
    if name.startswith("dog"):
        try:
            m = int(name[3:]) if len(name) > 3 else 2
        except ValueError:
            m = 2
        return DOG(m)
    raise ValueError(f"Unknown continuous wavelet '{name}'. "
                     f"Supported: morlet, mexhat, paulN, dogN")


def _reconstruction_constant(wavelet: ContinuousWavelet) -> float:
    """Reconstruction constant C_δ for the wavelet (Torrence & Compo Table 1)."""
    if isinstance(wavelet, Morlet):
        return 0.776
    if isinstance(wavelet, MexicanHat):
        return 3.541
    if isinstance(wavelet, Paul):
        return 1.079  # for m=4
    if isinstance(wavelet, DOG):
        return 3.541 if wavelet.m == 2 else 1.965
    return 1.0


def _psi_at_zero(name: str) -> float:
    """Value of the mother wavelet at t=0 (for reconstruction normalization)."""
    if name.startswith("morlet"):
        return math.pi ** -0.25
    if name.startswith("mexhat"):
        return 2.0 / (math.sqrt(3) * math.pi ** 0.25)
    if name.startswith("paul"):
        return 1.0  # Paul(0) normalized
    if name.startswith("dog"):
        return 2.0 / (math.sqrt(3) * math.pi ** 0.25)
    return 1.0