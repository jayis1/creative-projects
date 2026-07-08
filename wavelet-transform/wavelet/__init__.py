"""
wavelet-transform: A from-scratch wavelet transform toolkit.

Provides Discrete Wavelet Transform (DWT), Maximal Overlap DWT (MODWT),
wavelet packet decomposition, 1-D and 2-D transforms, threshold-based
denoising, and signal compression — all in pure Python (stdlib only).
"""

from .wavelets import Wavelet, Haar, Daubechies, Symlet, Coiflet, Biorthogonal, wavelet
from .dwt import DWT
from .modwt import MODWT
from .packets import WaveletPacket
from .threshold import Threshold, soft, hard, garrote, firm
from .denoise import denoise1d, denoise2d
from .compress import compress1d, decompress1d, serialize, deserialize
from .utils import energy, entropy, psnr, mse, snr

__version__ = "1.0.0"

__all__ = [
    "Wavelet", "Haar", "Daubechies", "Symlet", "Coiflet", "Biorthogonal", "wavelet",
    "DWT", "MODWT", "WaveletPacket",
    "Threshold", "soft", "hard", "garrote", "firm",
    "denoise1d", "denoise2d",
    "compress1d", "decompress1d",
    "energy", "entropy", "psnr", "mse", "snr",
]