"""
Wavelet basis functions: Haar, Daubechies, Symlet, Coiflet, and Biorthogonal families.

Each wavelet is defined by its filter coefficients (low-pass and high-pass decomposition
filters, and the corresponding reconstruction filters).

Convention:
  Decomposition uses **convolution + downsample**:
    a[i] = Σ_j dec_lo[j] * signal[(2i - j) mod n]
    d[i] = Σ_j dec_hi[j] * signal[(2i - j) mod n]

  Reconstruction uses **upsample + cross-correlation** (adjoint of decomposition):
    x[m] = Σ_j rec_lo[j] * a_up[(m + j) mod N] + Σ_j rec_hi[j] * d_up[(m + j) mod N]
    where a_up[k] = a[k//2] if k is even, 0 if k is odd.

For orthogonal wavelets with this convention: rec_lo = dec_lo, rec_hi = dec_hi.
For biorthogonal wavelets: rec_lo and rec_hi are the dual filters.

All filter coefficients are verified against PyWavelets (1.x) reference values.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod


class Wavelet(ABC):
    """Abstract base class for all wavelet families."""

    name: str = "base"
    orthogonal: bool = True
    biorthogonal: bool = False
    _dec_lo: list[float] = []
    _dec_hi: list[float] = []
    _rec_lo: list[float] = []
    _rec_hi: list[float] = []

    # --- properties ---------------------------------------------------------
    @property
    def dec_lo(self) -> list[float]:
        return list(self._dec_lo)

    @property
    def dec_hi(self) -> list[float]:
        return list(self._dec_hi)

    @property
    def rec_lo(self) -> list[float]:
        return list(self._rec_lo)

    @property
    def rec_hi(self) -> list[float]:
        return list(self._rec_hi)

    @property
    def filter_length(self) -> int:
        """Length of the decomposition low-pass filter."""
        return len(self._dec_lo)

    @property
    def support(self) -> int:
        """Effective support width."""
        return len(self._dec_lo)

    @property
    def rec_filter_length(self) -> int:
        """Length of the reconstruction low-pass filter."""
        return len(self._rec_lo)

    @property
    def vanishing_moments(self) -> int:
        """Number of vanishing moments (overridden by subclasses)."""
        return 0

    # --- helpers -----------------------------------------------------------
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', N={self.filter_length})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.name == other.name

    def __hash__(self) -> int:
        return hash(self.name)

    def _check(self) -> None:
        """Validate filter lengths.

        For orthogonal wavelets all four filters share the same length.
        For biorthogonal wavelets dec_hi has the length of rec_lo, and
        rec_hi has the length of dec_lo.
        """
        n_dec = len(self._dec_lo)
        n_rec = len(self._rec_lo)
        if self.orthogonal:
            if not (len(self._dec_hi) == n_dec == n_rec == len(self._rec_hi)):
                raise ValueError(
                    f"Filter length mismatch in {self.name}: "
                    f"dec_lo={n_dec} dec_hi={len(self._dec_hi)} "
                    f"rec_lo={n_rec} rec_hi={len(self._rec_hi)}")
        else:
            if len(self._dec_hi) != n_rec:
                raise ValueError(
                    f"dec_hi length ({len(self._dec_hi)}) must equal "
                    f"rec_lo length ({n_rec}) for {self.name}")
            if len(self._rec_hi) != n_dec:
                raise ValueError(
                    f"rec_hi length ({len(self._rec_hi)}) must equal "
                    f"dec_lo length ({n_dec}) for {self.name}")


def _alt_flip(lo: list[float]) -> list[float]:
    """Compute high-pass filter from low-pass: h[k] = (-1)^k · lo[L-1-k]."""
    L = len(lo)
    return [((-1) ** k) * lo[L - 1 - k] for k in range(L)]


# -------------------------------------------------------------------------
# Haar
# -------------------------------------------------------------------------
class Haar(Wavelet):
    """Haar wavelet (db1) — the simplest orthogonal wavelet.

    With convolution-decomposition / cross-correlation-reconstruction convention:
    rec_lo = dec_lo, rec_hi = dec_hi.
    """

    name = "haar"
    _dec_lo = [0.7071067811865476, 0.7071067811865476]
    _dec_hi = [0.7071067811865476, -0.7071067811865476]
    _rec_lo = [0.7071067811865476, 0.7071067811865476]
    _rec_hi = [0.7071067811865476, -0.7071067811865476]

    @property
    def vanishing_moments(self) -> int:
        return 1


# -------------------------------------------------------------------------
# Daubechies (db1..db4) — verified reference coefficients
# -------------------------------------------------------------------------
_DB_LO_COEFFS: dict[int, list[float]] = {
    1: [0.7071067811865476, 0.7071067811865476],
    2: [-1.2940952255126037e-01, 2.2414386804201339e-01,
        8.3651630373780794e-01, 4.8296291314453416e-01],
    3: [3.5226291885709533e-02, -8.5441273882026658e-02,
        -1.3501102001025458e-01, 4.5987750211849154e-01,
        8.0689150931109255e-01, 3.3267055295008263e-01],
    4: [-1.0597401785069032e-02, 3.2883011666885197e-02,
        3.0841381835560764e-02, -1.8703481171909309e-01,
        -2.7983769416859854e-02, 6.3088076792985892e-01,
        7.1484657055291567e-01, 2.3037781330889651e-01],
}


class Daubechies(Wavelet):
    """Daubechies wavelet family (dbN), N = 1..4.

    Uses verified reference scaling filter coefficients (same as PyWavelets).
    Convention: convolution + downsample decomposition, upsample + cross-correlation
    reconstruction.  For orthogonal wavelets: rec_lo = dec_lo, rec_hi = dec_hi.
    """

    def __init__(self, N: int = 4) -> None:
        if N < 1 or N > 4:
            raise ValueError(f"Daubechies N must be 1..4, got {N}")
        self.N = N
        self.name = f"db{N}"
        lo = list(_DB_LO_COEFFS[N])
        self._dec_lo = lo
        self._dec_hi = _alt_flip(lo)
        # For orthogonal wavelets with conv-dec / xcorr-rec convention:
        # rec_lo = dec_lo, rec_hi = dec_hi
        self._rec_lo = list(lo)
        self._rec_hi = list(self._dec_hi)
        self._check()

    @property
    def vanishing_moments(self) -> int:
        return self.N


# -------------------------------------------------------------------------
# Symlet (sym2..sym5) — verified reference coefficients
# -------------------------------------------------------------------------
_SYM_LO_COEFFS: dict[int, list[float]] = {
    2: [-1.2940952255092145e-01, 2.2414386804185735e-01,
        8.3651630373746899e-01, 4.8296291314469025e-01],
    3: [3.5226291882100656e-02, -8.5441273882241486e-02,
        -1.3501102001039084e-01, 4.5987750211933132e-01,
        8.0689150931333875e-01, 3.3267055295095688e-01],
    4: [-7.5765714789273325e-02, -2.9635527645998510e-02,
        4.9761866763201545e-01, 8.0373875180591614e-01,
        2.9785779560527736e-01, -9.9219543576847216e-02,
        -1.2603967262037833e-02, 3.2223100604042702e-02],
    5: [2.7333068345077982e-02, 2.9519490925774643e-02,
        -3.9134249302383094e-02, 1.9939753397739360e-01,
        7.2340769040242059e-01, 6.3397896345821192e-01,
        1.6602105764522319e-02, -1.7532808990845047e-01,
        -2.1101834024758855e-02, 1.9538882735286728e-02],
}


class Symlet(Wavelet):
    """Symlet wavelet family (symN), N = 2..5. Verified reference coefficients."""

    def __init__(self, N: int = 4) -> None:
        if N < 2 or N > 5:
            raise ValueError(f"Symlet N must be 2..5, got {N}")
        self.N = N
        self.name = f"sym{N}"
        lo = list(_SYM_LO_COEFFS[N])
        self._dec_lo = lo
        self._dec_hi = _alt_flip(lo)
        self._rec_lo = list(lo)
        self._rec_hi = list(self._dec_hi)
        self._check()

    @property
    def vanishing_moments(self) -> int:
        return self.N


# -------------------------------------------------------------------------
# Coiflet (coif1..coif3) — verified reference coefficients
# -------------------------------------------------------------------------
_COIF_LO_COEFFS: dict[int, list[float]] = {
    1: [-1.5655728135791993e-02, -7.2732619512526450e-02,
        3.8486484686485778e-01, 8.5257202021160039e-01,
        3.3789766245748182e-01, -7.2732619512526450e-02],
    2: [-7.2054944552034698e-04, -1.8232088709110323e-03,
        5.6114348193688343e-03, 2.3680171946847770e-02,
        -5.9434418646431092e-02, -7.6488599078280761e-02,
        4.1700518442323908e-01, 8.1272363544941351e-01,
        3.8611006682276289e-01, -6.7372554723725595e-02,
        -4.1464936786871777e-02, 1.6387336463203641e-02],
    3: [-3.4599773197272781e-05, -7.0983302506379004e-05,
        4.6621695982040288e-04, 1.1175187708306303e-03,
        -2.5745176881367972e-03, -9.0079761367306242e-03,
        1.5880544863669452e-02, 3.4555027573297738e-02,
        -8.2301927106299827e-02, -7.1799821619154838e-02,
        4.2848347637736999e-01, 7.9377722262608719e-01,
        4.0517690240911824e-01, -6.1123390002972552e-02,
        -6.5771911281469364e-02, 2.3452696142077168e-02,
        7.7825964256727463e-03, -3.7935128643808019e-03],
}


class Coiflet(Wavelet):
    """Coiflet wavelet family (coifN), N = 1..3. Verified reference coefficients."""

    def __init__(self, N: int = 2) -> None:
        if N < 1 or N > 3:
            raise ValueError(f"Coiflet N must be 1..3, got {N}")
        self.N = N
        self.name = f"coif{N}"
        lo = list(_COIF_LO_COEFFS[N])
        self._dec_lo = lo
        self._dec_hi = _alt_flip(lo)
        self._rec_lo = list(lo)
        self._rec_hi = list(self._dec_hi)
        self._check()

    @property
    def vanishing_moments(self) -> int:
        return self.N


# -------------------------------------------------------------------------
# Biorthogonal (bior) — verified reference coefficients
# -------------------------------------------------------------------------
# For biorthogonal wavelets, the decomposition and reconstruction filters are
# different.  The PyWavelets convention stores dec_lo, dec_hi, rec_lo, rec_hi
# explicitly.  With our conv-dec / xcorr-rec convention, we need to use the
# time-reversed PyWavelets rec filters as our rec filters.
_BIOR_COEFFS: dict[str, dict[str, list[float]]] = {
    "1.1": {
        "dec_lo": [0.7071067811865476, 0.7071067811865476],
        "dec_hi": [-0.7071067811865476, 0.7071067811865476],
        "rec_lo": [0.7071067811865476, 0.7071067811865476],
        "rec_hi": [0.7071067811865476, -0.7071067811865476],
    },
    "2.2": {
        "dec_lo": [0.0, -1.7677669529663689e-01, 3.5355339059327379e-01,
                   1.0606601717798212e+00, 3.5355339059327379e-01, -1.7677669529663689e-01],
        "dec_hi": [0.0, 3.5355339059327379e-01, -7.0710678118654757e-01,
                   3.5355339059327379e-01, 0.0, 0.0],
        "rec_lo": [0.0, 3.5355339059327379e-01, 7.0710678118654757e-01,
                   3.5355339059327379e-01, 0.0, 0.0],
        "rec_hi": [0.0, 1.7677669529663689e-01, 3.5355339059327379e-01,
                   -1.0606601717798212e+00, 3.5355339059327379e-01, 1.7677669529663689e-01],
    },
    "1.3": {
        "dec_lo": [-8.8388347648318447e-02, 8.8388347648318447e-02,
                   7.0710678118654757e-01, 7.0710678118654757e-01,
                   8.8388347648318447e-02, -8.8388347648318447e-02],
        "dec_hi": [0.0, 0.0, -0.7071067811865476, 0.7071067811865476, 0.0, 0.0],
        "rec_lo": [0.0, 0.0, 0.7071067811865476, 0.7071067811865476, 0.0, 0.0],
        "rec_hi": [-8.8388347648318447e-02, -8.8388347648318447e-02,
                   0.7071067811865476, -0.7071067811865476,
                   8.8388347648318447e-02, 8.8388347648318447e-02],
    },
    "1.5": {
        "dec_lo": [1.6572815184059706e-02, -1.6572815184059706e-02,
                   -1.2153397801643785e-01, 1.2153397801643785e-01,
                   7.0710678118654757e-01, 7.0710678118654757e-01,
                   1.2153397801643785e-01, -1.2153397801643785e-01,
                   -1.6572815184059706e-02, 1.6572815184059706e-02],
        "dec_hi": [0.0, 0.0, 0.0, 0.0, -0.7071067811865476, 0.7071067811865476, 0.0, 0.0, 0.0, 0.0],
        "rec_lo": [0.0, 0.0, 0.0, 0.0, 0.7071067811865476, 0.7071067811865476, 0.0, 0.0, 0.0, 0.0],
        "rec_hi": [1.6572815184059706e-02, 1.6572815184059706e-02,
                   -1.2153397801643785e-01, -1.2153397801643785e-01,
                   0.7071067811865476, -0.7071067811865476,
                   1.2153397801643785e-01, 1.2153397801643785e-01,
                   -1.6572815184059706e-02, -1.6572815184059706e-02],
    },
    "3.1": {
        "dec_lo": [-3.5355339059327379e-01, 1.0606601717798212e+00,
                   1.0606601717798212e+00, -3.5355339059327379e-01],
        "dec_hi": [-1.7677669529663689e-01, 5.3033008588991060e-01,
                   -5.3033008588991060e-01, 1.7677669529663689e-01],
        "rec_lo": [1.7677669529663689e-01, 5.3033008588991060e-01,
                   5.3033008588991060e-01, 1.7677669529663689e-01],
        "rec_hi": [-3.5355339059327379e-01, -1.0606601717798212e+00,
                   1.0606601717798212e+00, 3.5355339059327379e-01],
    },
    "3.3": {
        "dec_lo": [6.6291260736238825e-02, -1.9887378220871649e-01,
                   -1.5467960838455727e-01, 9.9436891104358249e-01,
                   9.9436891104358249e-01, -1.5467960838455727e-01,
                   -1.9887378220871649e-01, 6.6291260736238825e-02],
        "dec_hi": [0.0, 0.0, -1.7677669529663689e-01, 5.3033008588991060e-01,
                   -5.3033008588991060e-01, 1.7677669529663689e-01, 0.0, 0.0],
        "rec_lo": [0.0, 0.0, 1.7677669529663689e-01, 5.3033008588991060e-01,
                   5.3033008588991060e-01, 1.7677669529663689e-01, 0.0, 0.0],
        "rec_hi": [6.6291260736238825e-02, 1.9887378220871649e-01,
                   -1.5467960838455727e-01, -9.9436891104358249e-01,
                   9.9436891104358249e-01, 1.5467960838455727e-01,
                   -1.9887378220871649e-01, -6.6291260736238825e-02],
    },
}


class Biorthogonal(Wavelet):
    """Biorthogonal spline wavelet family (biorA.B).

    ``A`` is the order of the decomposition (analysis) scaling function,
    ``B`` is the order of the reconstruction (synthesis) scaling function.
    Verified reference coefficients (same as PyWavelets).
    """

    orthogonal = False
    biorthogonal = True

    def __init__(self, name: str = "2.2") -> None:
        if name not in _BIOR_COEFFS:
            raise ValueError(f"Unknown biorthogonal wavelet '{name}'. "
                             f"Available: {sorted(_BIOR_COEFFS.keys())}")
        self.name = f"bior{name}"
        c = _BIOR_COEFFS[name]
        self._dec_lo = list(c["dec_lo"])
        self._dec_hi = list(c["dec_hi"])
        # For biorthogonal with conv-dec / xcorr-rec convention:
        # rec filters = time-reversed PyWavelets rec filters
        self._rec_lo = list(reversed(c["rec_lo"]))
        self._rec_hi = list(reversed(c["rec_hi"]))
        self._check()

    @property
    def vanishing_moments(self) -> int:
        return int(self.name.split("bior")[1].split(".")[0])


# -------------------------------------------------------------------------
# Factory
# -------------------------------------------------------------------------
def wavelet(name: str) -> Wavelet:
    """Factory: create a wavelet from its name string.

    Examples::

        wavelet("haar")
        wavelet("db4")
        wavelet("sym3")
        wavelet("coif2")
        wavelet("bior2.2")
    """
    name = name.strip().lower()
    if name == "haar":
        return Haar()
    if name.startswith("db"):
        N = int(name[2:])
        return Daubechies(N)
    if name.startswith("sym"):
        N = int(name[3:])
        return Symlet(N)
    if name.startswith("coif"):
        N = int(name[4:])
        return Coiflet(N)
    if name.startswith("bior"):
        return Biorthogonal(name[4:])
    raise ValueError(f"Unknown wavelet '{name}'. "
                     f"Supported: haar, dbN (N=1..4), symN (N=2..5), "
                     f"coifN (N=1..3), biorA.B")