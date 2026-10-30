#!/usr/bin/env python3
"""Generate and inspect compact binary weaving drafts."""
import argparse
import json
from pathlib import Path


def twill(size: int, step: int = 1) -> list[list[int]]:
    """Return an n-by-n cyclic twill threading; 1 means warp is over."""
    _validate(size, step)
    return [[int((row + step * col) % size < step) for col in range(size)] for row in range(size)]


def _validate(size: int, step: int) -> None:
    if not isinstance(size, int) or isinstance(size, bool) or not 2 <= size <= 64:
        raise ValueError("size must be an integer from 2 to 64")
    if not isinstance(step, int) or isinstance(step, bool) or not 1 <= step < size:
        raise ValueError("step must be an integer from 1 to size-1")


def validate_draft(draft: list[list[int]]) -> tuple[int, int]:
    """Validate rectangular binary draft, returning (rows, columns)."""
    if not isinstance(draft, list) or not draft or not all(isinstance(r, list) for r in draft):
        raise ValueError("draft must be a non-empty list of rows")
    width = len(draft[0])
    if width == 0 or any(len(row) != width for row in draft):
        raise ValueError("draft rows must have equal non-zero width")
    if any(type(cell) is not int or cell not in (0, 1) for row in draft for cell in row):
        raise ValueError("draft cells must be 0 or 1")
    if len(draft) > 256 or width > 256:
        raise ValueError("draft dimensions may not exceed 256")
    return len(draft), width


def floats(draft: list[list[int]]) -> dict[str, int]:
    """Measure longest consecutive same-face run per warp and weft."""
    rows, cols = validate_draft(draft)

    def longest(values):
        best = run = 0
        previous = None
        for value in values:
            run = run + 1 if value == previous else 1
            best = max(best, run)
            previous = value
        return best

    warp = max(longest([draft[r][c] for r in range(rows)]) for c in range(cols))
    weft = max(longest(row) for row in draft)
    return {"warp": warp, "weft": weft, "worst": max(warp, weft)}


def render(draft: list[list[int]]) -> str:
    validate_draft(draft)
    return "\n".join("".join("█" if cell else "·" for cell in row) for row in draft)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=8)
    parser.add_argument("--step", type=int, default=1)
    parser.add_argument("--json", type=Path, help="write generated draft as JSON")
    args = parser.parse_args(argv)
    try:
        draft = twill(args.size, args.step)
    except ValueError as exc:
        parser.error(str(exc))
    print(render(draft))
    print("Float lengths:", json.dumps(floats(draft), sort_keys=True))
    if args.json:
        args.json.write_text(json.dumps(draft, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
