"""
wavelet-transform: A from-scratch wavelet transform toolkit.

Provides Discrete Wavelet Transform (DWT), Maximal Overlap DWT (MODWT),
Stationary Wavelet Transform (SWT), Continuous Wavelet Transform (CWT),
wavelet packet decomposition, 1-D and 2-D transforms, threshold-based
denoising, signal compression, coefficient analysis, signal generation,
and boundary extension — all in pure Python (stdlib only).

Modules
-------
wavelets    : Wavelet basis functions (Haar, Daubechies, Symlet, Coiflet, Biorthogonal)
dwt         : Discrete Wavelet Transform (1-D and 2-D, multilevel)
modwt       : Maximal Overlap DWT (translation-invariant)
swt         : Stationary Wavelet Transform (à-trous) + cycle-spinning denoising
cwt         : Continuous Wavelet Transform (Morlet, Mexican Hat, Paul, DOG)
packets     : Wavelet packet decomposition with best-basis selection
threshold   : Thresholding functions and estimation methods
denoise     : 1-D and 2-D denoising pipelines
compress    : Signal compression with RLE and binary serialization
signals     : Signal generation utilities (sine, chirp, blocks, Doppler, etc.)
analysis    : Coefficient analysis (per-scale stats, energy distribution, variance)
boundary    : Boundary extension strategies (periodic, symmetric, zero, constant, reflect)
config      : Configuration file support (JSON, YAML, TOML)
utils       : Quality metrics (energy, entropy, MSE, RMSE, SNR, PSNR, MAE)
cli         : Command-line interface
logging_utils : Structured logging
"""

from .wavelets import Wavelet, Haar, Daubechies, Symlet, Coiflet, Biorthogonal, wavelet
from .dwt import DWT, DWTResult
from .modwt import MODWT, MODWTResult
from .swt import SWT, SWTResult, cycle_spin_denoise
from .cwt import (
    Morlet, MexicanHat, Paul, DOG, ContinuousWavelet,
    cwt, icwt, CWTResult,
)
from .packets import WaveletPacket
from .threshold import Threshold, soft, hard, garrote, firm
from .denoise import denoise1d, denoise2d
from .compress import compress1d, decompress1d, serialize, deserialize
from .signals import (
    sine, multi_tone, chirp, square, sawtooth, triangle,
    pulse, step, ramp, gaussian_pulse,
    white_noise, brown_noise, pink_noise,
    blocks, bumps, heavisine, doppler, ecg_like,
    add_noise, generate, list_signals,
)
from .analysis import (
    ScaleStats, AnalysisResult,
    scale_statistics, energy_distribution, wavelet_variance,
    scale_correlation, compare_wavelets, analyze,
)
from .boundary import BoundaryMode, extend_signal
from .config import WaveletConfig, DenoiseConfig, CompressConfig, load_config, save_config
from .utils import energy, entropy, psnr, mse, snr, rmse, mean_absolute_error, power
from .logging_utils import get_logger, set_log_level, set_verbose

__version__ = "2.0.0"

__all__ = [
    # Wavelets
    "Wavelet", "Haar", "Daubechies", "Symlet", "Coiflet", "Biorthogonal", "wavelet",
    # Transforms
    "DWT", "DWTResult", "MODWT", "MODWTResult",
    "SWT", "SWTResult", "cycle_spin_denoise",
    "Morlet", "MexicanHat", "Paul", "DOG", "ContinuousWavelet",
    "cwt", "icwt", "CWTResult",
    "WaveletPacket",
    # Thresholding
    "Threshold", "soft", "hard", "garrote", "firm",
    # Denoising
    "denoise1d", "denoise2d",
    # Compression
    "compress1d", "decompress1d", "serialize", "deserialize",
    # Signals
    "sine", "multi_tone", "chirp", "square", "sawtooth", "triangle",
    "pulse", "step", "ramp", "gaussian_pulse",
    "white_noise", "brown_noise", "pink_noise",
    "blocks", "bumps", "heavisine", "doppler", "ecg_like",
    "add_noise", "generate", "list_signals",
    # Analysis
    "ScaleStats", "AnalysisResult",
    "scale_statistics", "energy_distribution", "wavelet_variance",
    "scale_correlation", "compare_wavelets", "analyze",
    # Boundary
    "BoundaryMode", "extend_signal",
    # Config
    "WaveletConfig", "DenoiseConfig", "CompressConfig", "load_config", "save_config",
    # Utils
    "energy", "entropy", "psnr", "mse", "snr", "rmse", "mean_absolute_error", "power",
    # Logging
    "get_logger", "set_log_level", "set_verbose",
]