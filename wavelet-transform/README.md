# wavelet-transform

A from-scratch wavelet transform toolkit implementing the Discrete Wavelet Transform (DWT), Maximal Overlap DWT (MODWT), wavelet packet decomposition, threshold-based denoising, and signal compression — all in pure Python (stdlib only, no numpy/scipy required).

## Features

- **5 wavelet families**: Haar, Daubechies (db1–db4), Symlet (sym2–sym5), Coiflet (coif1–coif3), Biorthogonal (bior1.1, bior1.3, bior1.5, bior2.2, bior2.4, bior3.1, bior3.3)
- **1-D DWT**: Single-level and multilevel decomposition/reconstruction with periodic boundary extension
- **2-D DWT**: Separable 2-D wavelet decomposition (rows then columns) for image processing
- **MODWT**: Maximal Overlap DWT — translation-invariant, non-decimated transform
- **Wavelet Packets**: Full binary tree decomposition with best-basis selection (Shannon entropy cost)
- **Denoising**: Soft/hard/garrote/firm thresholding with 4 threshold estimation methods (VisuShrink/universal, SureShrink/SURE, BayesShrink, Minimax)
- **Compression**: Wavelet-based signal compression with run-length encoding and binary serialization
- **Quality metrics**: Energy, entropy, MSE, RMSE, SNR, PSNR, MAE
- **CLI**: 8-subcommand argparse CLI (info, decompose, denoise, compress, decompress, packets, visualize, benchmark)
- **Pure Python**: No external dependencies — uses only the standard library

## How It Works

### Filter Convention

The implementation uses:
- **Decomposition**: convolution + downsample — `out[i] = Σ_j filt[j] · signal[(2i − j) mod n]`
- **Reconstruction**: upsample + cross-correlation — `out[m] = Σ_j filt[j] · up[(m + j) mod N]` where `up[k] = a[k//2]` if k is even, 0 if k is odd

For orthogonal wavelets, this means `rec_lo = dec_lo` and `rec_hi = dec_hi` (same filters for both directions). For biorthogonal wavelets, the reconstruction filters are the time-reversed PyWavelets rec filters.

All filter coefficients are verified against PyWavelets reference values and produce perfect reconstruction (roundtrip error < 1e-15).

### DWT (Mallat Algorithm)

The multilevel DWT recursively decomposes the approximation coefficients:
```
signal → [A₁, D₁] → [A₂, D₂, D₁] → [A₃, D₃, D₂, D₁] → ...
```
Reconstruction reverses the process, tracking the signal length at each level for correct reconstruction with periodic boundaries.

### MODWT

The MODWT is similar to the DWT but:
- Does not decimate (output length = input length at every level)
- Upsamples the filters by 2^(j-1) at level j instead of downsampling the signal
- Is translation-invariant
- Uses filters scaled by 1/√2

### Wavelet Packets

The wavelet packet transform decomposes *both* the approximation and detail at each level, producing a full binary tree of 2^level subbands. The best-basis algorithm uses dynamic programming with Shannon entropy as the cost function to select the optimal subset of nodes.

### Denoising Pipeline

1. Forward DWT (or MODWT for translation-invariant denoising)
2. Estimate noise σ from finest-level detail coefficients via MAD (Median Absolute Deviation)
3. Compute threshold using the selected method (universal, SURE, Bayes, minimax)
4. Apply thresholding function (soft/hard/garrote) to detail coefficients
5. Inverse DWT to reconstruct the denoised signal

### Compression Pipeline

1. Forward DWT
2. Soft-threshold detail coefficients (keep only the largest k%)
3. Run-length encode the sparse coefficient arrays
4. Serialize to a compact binary format (struct-packed)

## Installation

```bash
cd wavelet-transform
pip install -e .
```

## Usage

### Python API

```python
from wavelet import wavelet, DWT, MODWT, WaveletPacket, denoise1d, compress1d, decompress1d

# Create a wavelet
w = wavelet("db4")

# 1-D DWT
dwt = DWT(w)
result = dwt.decompose(signal, level=4)
reconstructed = dwt.reconstruct(result)

# MODWT (translation-invariant)
mod = MODWT(w)
result = mod.decompose(signal, level=4)
reconstructed = mod.reconstruct(result)

# Wavelet packets with best-basis selection
wp = WaveletPacket(w)
result = wp.decompose(signal, level=3)
best = wp.best_basis(result)

# Denoising
denoised = denoise1d(noisy_signal, wavelet="db4", threshold_method="bayes")

# Compression
compressed = compress1d(signal, wavelet="db4", keep_ratio=0.3)
reconstructed = decompress1d(compressed)
```

### CLI

```bash
# Show wavelet filter info
wavelet-transform info -w db4

# Decompose a signal
wavelet-transform decompose -s chirp -n 256 -w db4 -l 4

# Denoise a signal
wavelet-transform denoise -s sine -n 256 -w db4 --method bayes -t soft

# Compress a signal
wavelet-transform compress -s sine -n 256 -w db4 --keep-ratio 0.3 -o compressed.bin

# Decompress
wavelet-transform decompress -i compressed.bin -o reconstructed.json

# Wavelet packet decomposition with best basis
wavelet-transform packets -s sine -n 128 -w db4 -l 4 --best-basis

# ASCII visualization
wavelet-transform visualize -s chirp -n 64 -w haar -l 3

# Benchmark
wavelet-transform benchmark -n 512 -i 10
```

## Supported Wavelets

| Family | Names | Filter Length | Vanishing Moments |
|--------|-------|---------------|-------------------|
| Haar | haar, db1 | 2 | 1 |
| Daubechies | db1, db2, db3, db4 | 2, 4, 6, 8 | 1–4 |
| Symlet | sym2, sym3, sym4, sym5 | 4, 6, 8, 10 | 2–5 |
| Coiflet | coif1, coif2, coif3 | 6, 12, 18 | 1–3 |
| Biorthogonal | bior1.1, bior1.3, bior1.5, bior2.2, bior2.4, bior3.1, bior3.3 | varies | varies |

## Thresholding Methods

| Method | Description |
|--------|-------------|
| Universal (VisuShrink) | T = σ√(2 ln n) — simple, universal threshold |
| SURE (SureShrink) | Minimizes Stein's Unbiased Risk Estimate |
| Bayes (BayesShrink) | Adapts to subband signal variance: T = σ²/σ_signal |
| Minimax | Minimax risk threshold |

## Quality Metrics

- **Energy**: Σ|xᵢ|²
- **Entropy**: Shannon entropy of normalized |x|²
- **MSE**: Mean Squared Error
- **RMSE**: Root Mean Squared Error
- **SNR**: Signal-to-Noise Ratio (dB)
- **PSNR**: Peak Signal-to-Noise Ratio (dB)

## License

MIT