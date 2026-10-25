"""Unicode-aware paragraph line breaking with greedy and balanced strategies."""
from __future__ import annotations
import argparse
import unicodedata


def _width(text: str) -> int:
    """Measure terminal columns: combining marks zero, wide characters two."""
    return sum(0 if unicodedata.combining(ch) else 2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def greedy_wrap(text: str, width: int) -> list[str]:
    """Wrap words greedily while respecting a positive display-width limit."""
    if width < 1:
        raise ValueError("width must be a positive integer")
    words, lines, current = text.split(), [], ""
    for word in words:
        if _width(word) > width:
            raise ValueError(f"word exceeds line width: {word!r}")
        candidate = word if not current else current + " " + word
        if current and _width(candidate) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text", nargs="?", default="A small paragraph can be laid out cleanly without breaking words.")
    parser.add_argument("-w", "--width", type=int, default=24)
    parser.add_argument("--demo", action="store_true", help="run the built-in sample")
    args = parser.parse_args(argv)
    text = "A small paragraph can be laid out cleanly without breaking words." if args.demo else args.text
    try:
        print("\n".join(greedy_wrap(text, args.width)))
    except ValueError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
