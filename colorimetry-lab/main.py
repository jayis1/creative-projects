"""Command-line colorimetry conversions."""
import argparse
import json

from colorimetry import rgb_to_lab, srgb_to_xyz


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert sRGB colors to CIE Lab and XYZ")
    parser.add_argument("r", nargs="?", type=float, help="red channel, 0..1")
    parser.add_argument("g", nargs="?", type=float, help="green channel, 0..1")
    parser.add_argument("b", nargs="?", type=float, help="blue channel, 0..1")
    args = parser.parse_args()
    if args.r is None and args.g is None and args.b is None:
        rgb = (1.0, 0.0, 0.0)
    elif None in (args.r, args.g, args.b):
        parser.error("provide all three channels or none for the red demo")
    else:
        rgb = (args.r, args.g, args.b)
    try:
        result = {"srgb": rgb, "xyz_d65": srgb_to_xyz(rgb), "lab_d65": rgb_to_lab(rgb)}
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
