# Color Quantizer

A dependency-free P6 PPM color reduction tool. It builds a palette with median cut, maps pixels to nearest colors, and can apply Floyd–Steinberg error diffusion. This image-processing algorithm project is distinct from the repository's simulation, solver, and codec projects.

## Quick start

Run `python3 quantizer.py input.ppm output.ppm --colors 8`. Add `--dither` for error diffusion. PPM support is binary P6 with max channel value 255.

## How it works

Median cut repeatedly splits the color box with greatest channel range at its median, then averages each box into a palette color. Each source pixel is assigned to the nearest palette entry by squared RGB distance. Dithering diffuses quantization error across neighboring pixels.

## Examples

`python3 quantizer.py examples/sample.ppm /tmp/reduced.ppm -n 4 --dither`

## Tests

`python3 -m unittest discover -s tests -v`

## Enhancements

Phase 2 adds robust P6 parsing, configurable palette sizes, and optional Floyd–Steinberg dithering.

## Known Issues (Resolved)

None confirmed in the initial implementation; regression review is performed in the bug-hunt phase.
