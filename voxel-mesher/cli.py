"""Command-line JSON-to-OBJ interface for voxel-mesher."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mesher import VoxelModel


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Greedy-mesh a sparse voxel JSON file")
    parser.add_argument("input", help="JSON object with a 'voxels' array")
    parser.add_argument("-o", "--output", help="OBJ output path (default: stdout)")
    parser.add_argument("--stats", action="store_true", help="write mesh counts to stderr")
    parser.add_argument("--format", choices=("obj", "stl"), default="obj", help="mesh format (default: obj)")
    args = parser.parse_args(argv)
    try:
        with Path(args.input).open(encoding="utf-8") as source:
            payload = json.load(source)
        if not isinstance(payload, dict) or not isinstance(payload.get("voxels"), list):
            raise ValueError("input must be an object containing a 'voxels' array")
        model = VoxelModel(payload["voxels"])
        mesh = model.to_stl(name=Path(args.input).stem) if args.format == "stl" else model.to_obj()
        if args.output:
            Path(args.output).write_text(mesh, encoding="utf-8")
        else:
            sys.stdout.write(mesh)
        if args.stats:
            print(f"voxels={len(model.voxels)} unit_faces={len(model.faces())} quads={len(model.greedy_faces())}", file=sys.stderr)
        return 0
    except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
        print(f"voxel-mesher: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
