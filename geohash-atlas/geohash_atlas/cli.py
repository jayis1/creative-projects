"""Command-line tools for geohash cells."""
import argparse
import json
from .geohash import decode, encode


def main(argv=None):
    parser = argparse.ArgumentParser(description="Encode coordinates or inspect a geohash cell")
    sub = parser.add_subparsers(dest="command", required=True)
    enc = sub.add_parser("encode", help="encode latitude and longitude")
    enc.add_argument("latitude", type=float)
    enc.add_argument("longitude", type=float)
    enc.add_argument("--precision", type=int, default=8)
    dec = sub.add_parser("decode", help="decode a geohash to its bounding cell")
    dec.add_argument("code")
    args = parser.parse_args(argv)
    try:
        if args.command == "encode":
            print(encode(args.latitude, args.longitude, args.precision))
        else:
            b = decode(args.code)
            print(json.dumps({"south": b.south, "west": b.west, "north": b.north, "east": b.east}, indent=2))
    except ValueError as exc:
        parser.error(str(exc))

if __name__ == "__main__":
    main()
