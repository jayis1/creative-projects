"""CLI for converting PGM grayscale images to Unicode Braille."""
import argparse
from pathlib import Path
from braille import read_pgm, render


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", nargs="?", help="P2/P5 PGM file")
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--invert", action="store_true", help="render bright pixels as dots")
    parser.add_argument("--dither", action="store_true", help="apply Floyd–Steinberg grayscale dithering")
    parser.add_argument("--demo", action="store_true", help="render the bundled sample")
    args = parser.parse_args()
    if args.demo:
        path = Path(__file__).parent / "examples" / "sample.pgm"
    elif args.image:
        path = Path(args.image)
    else:
        parser.error("provide an image or --demo")
    try:
        print(render(read_pgm(path), args.threshold, args.invert, args.dither))
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
