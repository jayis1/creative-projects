"""Command-line tools for geohash cells."""
import argparse
import json
from .geohash import decode, encode, neighbors, cell_size


def main(argv=None):
    parser = argparse.ArgumentParser(description="Encode coordinates or inspect a geohash cell")
    sub = parser.add_subparsers(dest="command", required=True)
    enc = sub.add_parser("encode", help="encode latitude and longitude")
    enc.add_argument("latitude", type=float)
    enc.add_argument("longitude", type=float)
    enc.add_argument("--precision", type=int, default=8)
    dec = sub.add_parser("decode", help="decode a geohash to its bounding cell")
    dec.add_argument("code")
    near = sub.add_parser("neighbors", help="list adjacent cells and approximate angular size")
    near.add_argument("code")
    args = parser.parse_args(argv)
    try:
        if args.command == "encode":
            print(encode(args.latitude, args.longitude, args.precision))
        elif args.command == "decode":
            b = decode(args.code)
            print(json.dumps({"south": b.south, "west": b.west, "north": b.north, "east": b.east}, indent=2))
        else:
            height, width = cell_size(args.code)
            print(json.dumps({"neighbors": neighbors(args.code), "height_degrees": height, "width_degrees": width}, indent=2))
    except ValueError as exc:
        parser.error(str(exc))

if __name__ == "__main__":
    main()
