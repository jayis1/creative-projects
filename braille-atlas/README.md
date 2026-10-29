# Braille Atlas

A dependency-free converter from grayscale PGM images to compact Unicode Braille. It packs each 2×4 pixel tile into one terminal cell, making tiny monochrome images inspectable in a shell without image libraries.

## How it works

The P2/P5 Portable Graymap parser validates dimensions and sample ranges, then the renderer maps the 2×4 samples to the Unicode Braille dot bit layout. Pixels below a configurable normalized grayscale threshold are raised as dots; incomplete edge tiles are padded as blank.

## Usage

From this directory:

```sh
python3 cli.py --demo
python3 cli.py examples/sample.pgm --threshold 0.4
python3 cli.py photo.pgm --invert
python3 cli.py photo.pgm --dither
python3 cli.py photo.pgm --width 80
```

The optional `--width` flag rescales the input with nearest-neighbor sampling while preserving its aspect ratio, so large images can fit a terminal. Input is limited to 16 MB and one million pixels. PGM is a simple portable grayscale format; convert other formats externally.

## Changelog

- Added nearest-neighbor resizing via `--width` and validation for directly constructed PGM images.
- Initial implementation supports ASCII P2 and binary P5 PGM, threshold selection, and inversion.
- Added optional Floyd–Steinberg error diffusion for grayscale gradients; the default threshold renderer remains unchanged.

## Known Issues (Resolved)

- P2 pixel data previously failed when a comment appeared after a pixel value on the same line. `test_ascii_pgm` now covers inline-comment parsing and confirms all samples are retained.

## Limitations

No color image decoding, resizing, or automatic contrast enhancement; output depends on a terminal/font with Braille glyph support.
