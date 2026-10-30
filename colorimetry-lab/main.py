"""Command-line colorimetry conversions and perceptual comparison."""
import argparse
import json

from colorimetry import delta_e76, rgb_to_lab, srgb_to_xyz


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert and compare sRGB colors")
    parser.add_argument("r", nargs="?", type=float, help="red channel, 0..1")
    parser.add_argument("g", nargs="?", type=float, help="green channel, 0..1")
    parser.add_argument("b", nargs="?", type=float, help="blue channel, 0..1")
    parser.add_argument("--compare", nargs=3, type=float, metavar=("R", "G", "B"),
                        help="compare this color to the positional color with Delta E 1976")
    args = parser.parse_args()
    if args.r is None and args.g is None and args.b is None:
        rgb = (1.0, 0.0, 0.0)
    elif None in (args.r, args.g, args.b):
        parser.error("provide all three channels or none for the red demo")
    else:
        rgb = (args.r, args.g, args.b)
    try:
        result = {"srgb": rgb, "xyz_d65": srgb_to_xyz(rgb), "lab_d65": rgb_to_lab(rgb)}
        if args.compare is not None:
            other = tuple(args.compare)
            result["comparison"] = {"srgb": other, "lab_d65": rgb_to_lab(other),
                                    "delta_e_1976": delta_e76(rgb_to_lab(rgb), rgb_to_lab(other))}
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
