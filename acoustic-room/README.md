# Acoustic Room

Predict early room reflections with the image-source method. This dependency-free simulator turns a rectangular room, source, and listener position into a sampled impulse response and a list of reflected arrival paths.

## Quick start

```sh
python3 main.py
```

Observed example:

```text
room=(6, 5, 3) m, order=2, arrivals=125
time (ms)   amplitude     image
   10.51     0.27735   (0, 0, 0)
   13.67     0.19069   (0, 0, -1)
   13.67     0.19069   (0, 0, 1)
   14.58     0.17889   (0, -1, 0)
   15.70     0.16609   (-1, 0, 0)
```

Run `python3 main.py --summary --absorption 0.1 0.3 0.2 0.4 0.5 0.6` to estimate Sabine RT60 using six wall-specific energy absorption coefficients (ordered X0, X1, Y0, Y1, Z0, Z1). `--summary` prints the estimate and number of early arrivals; the estimate assumes a diffuse field and is a rough room-level metric. Generate machine-readable arrivals with `python3 main.py --order 3 --json`; make the room 8×6×3 metres with `--room 8 6 3`.

## How it works

A rectangular room is mirrored across each wall. Every mirrored source is an image source; its distance to the receiver gives propagation time. The image-grid index determines the number of reflections on each axis, whose wall energy losses attenuate the path. The paths are sorted by time and accumulated into a discrete impulse response. The response is currently exposed by the Python API; the CLI prints its arrival list.

## Options and API

`--source X Y Z`, `--receiver X Y Z`, `--order N`, `--duration SECONDS`, `--rate HZ`, and `--json` configure the simulation. Defaults are bounded for a quick run. In Python, import `Room` and `impulse_response` from `main`; it returns `(samples, arrivals)`.

## Tests

Run `python3 -m unittest -v` in this directory.

## Known Issues (Resolved)

- Signed image indices previously used the wrong mirrored-source coordinate for negative and positive tiles; `test_negative_image_uses_near_wall_absorption` now checks the negative image's actual path.
- Per-wall attenuation previously chose the wall from parity rather than travel direction, so near-wall coefficients could be wrong; `test_negative_image_uses_near_wall_absorption` and `test_two_bounces_attenuate_by_both_opposing_walls` verify near-wall selection and alternating losses across two surfaces.

The image-source model remains an idealized approximation; see Limitations.

## Limitations

This is a geometric-acoustics approximation for rectangular rooms. It does not model frequency-dependent absorption, diffraction, directional sources, or late diffuse reverberation. Sample accumulation uses nearest-sample impulses.
