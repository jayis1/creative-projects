"""Unicode-aware paragraph line breaking with greedy and balanced strategies."""
from __future__ import annotations
import argparse
import unicodedata


def _width(text: str) -> int:
    """Measure terminal columns: combining marks zero, wide characters two."""
    return sum(0 if unicodedata.combining(ch) else 2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def _words(text: str, width: int) -> list[str]:
    if width < 1:
        raise ValueError("width must be a positive integer")
    words = text.split()
    for word in words:
        if _width(word) > width:
            raise ValueError(f"word exceeds line width: {word!r}")
    return words


def greedy_wrap(text: str, width: int) -> list[str]:
    """Wrap words greedily while respecting a positive display-width limit."""
    words = _words(text, width)
    lines, current = [], ""
    for word in words:
        candidate = word if not current else current + " " + word
        if current and _width(candidate) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def balanced_wrap(text: str, width: int) -> list[str]:
    """Minimize squared unused width via dynamic programming (O(n²))."""
    words = _words(text, width)
    n = len(words)
    if not n:
        return []
    # dp[i] is minimum remaining raggedness for words starting at i.
    costs = [float("inf")] * (n + 1)
    costs[n] = 0.0
    ends = [0] * n
    for i in range(n - 1, -1, -1):
        used = 0
        for j in range(i, n):
            used += _width(words[j]) + (1 if j > i else 0)
            if used > width:
                break
            penalty = 0 if j == n - 1 else (width - used) ** 2
            cost = penalty + costs[j + 1]
            if cost < costs[i]:
                costs[i], ends[i] = cost, j + 1
    result, i = [], 0
    while i < n:
        end = ends[i]
        result.append(" ".join(words[i:end]))
        i = end
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text", nargs="?", default="A small paragraph can be laid out cleanly without breaking words.")
    parser.add_argument("-w", "--width", type=int, default=24)
    parser.add_argument("--demo", action="store_true", help="run the built-in sample")
    parser.add_argument("--balanced", action="store_true", help="minimize raggedness instead of greedy wrapping")
    args = parser.parse_args(argv)
    text = "A small paragraph can be laid out cleanly without breaking words." if args.demo else args.text
    try:
        lines = balanced_wrap(text, args.width) if args.balanced else greedy_wrap(text, args.width)
        print("\n".join(lines))
    except ValueError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
