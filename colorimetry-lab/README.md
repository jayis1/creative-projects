# Colorimetry Lab

A dependency-free Python toolkit for converting gamma-encoded sRGB into linear-light D65 XYZ and CIE L*a*b*. It makes the transfer-function and reference-white choices explicit so small color experiments are reproducible.

## How it works

Each sRGB channel is decoded with the IEC 61966-2-1 piecewise transfer curve, then multiplied by the standard 3×3 sRGB-to-XYZ matrix. XYZ is normalized to the D65 reference white. XYZ-to-Lab uses the CIE piecewise cube-root function, with its linear branch near black to avoid instability. The implementation rejects non-finite and out-of-domain inputs rather than silently clipping values.

This is distinct from the repository's color-quantizer: that project reduces image palettes, while this one performs colorimetric coordinate conversion and exposes the underlying numerical transforms.

## Usage

Requires Python 3.10+; no third-party packages.

```sh
python3 main.py --help
python3 main.py
python3 main.py 0 1 0
```

With no channels, the CLI demonstrates sRGB red. Example output (rounded here only for readability):

```json
{
  "srgb": [1.0, 0.0, 0.0],
  "xyz_d65": [0.4124564, 0.2126729, 0.0193339],
  "lab_d65": [53.2408, 80.0925, 67.2032]
}
```

Library use:

```python
from colorimetry import rgb_to_lab, delta_e76
red = rgb_to_lab((1.0, 0.0, 0.0))
blue = rgb_to_lab((0.0, 0.0, 1.0))
print(delta_e76(red, blue))
```

## Phase 2: perceptual comparisons

The CLI now supports an output-affecting comparison mode; it emits the second color's Lab coordinates and Euclidean CIE76 distance alongside the first color's conversion. Before this phase there was no `--compare` option; now this command runs successfully:

```sh
python3 main.py 1 0 0 --compare 0 0 1
```

CIE76 is useful for simple comparisons but is not perceptually uniform in all regions; use a newer formula where that precision is required.

## Known Issues (Resolved)

- `delta_e76` could return positive infinity when subtracting two individually finite but extreme Lab coordinates overflowed. The root cause was unchecked floating-point subtraction and squaring. The function now detects non-finite differences/results and raises `ValueError`; regression test: `test_delta_e76_rejects_unrepresentable_distance` (observed failing before the fix and passing afterward).

## Limitations

Inputs are normalized sRGB, not 8-bit integer RGB; no ICC profiles, chromatic adaptation, CIEDE2000, or gamut mapping are included. XYZ input is D65-relative and nonnegative. Floating-point distances beyond the representable range are rejected.

## Development

Run from this directory with `python3 -m unittest -v`.
