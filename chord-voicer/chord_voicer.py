"""Generate compact, register-bounded chord voicings."""

from __future__ import annotations

import argparse
import itertools

PITCH_CLASSES = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
                 "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
                 "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
QUALITIES = {"": (0, 4, 7), "m": (0, 3, 7), "dim": (0, 3, 6),
             "aug": (0, 4, 8), "7": (0, 4, 7, 10), "m7": (0, 3, 7, 10)}


def chord_tones(symbol: str) -> tuple[int, ...]:
    """Return pitch classes for a supported chord symbol."""
    root = symbol[:2] if len(symbol) > 1 and symbol[1] in "#b" else symbol[:1]
    quality = symbol[len(root):]
    if root not in PITCH_CLASSES or quality not in QUALITIES:
        raise ValueError(f"unsupported chord: {symbol!r}")
    return tuple((PITCH_CLASSES[root] + interval) % 12 for interval in QUALITIES[quality])


def _parse_chord(symbol: str) -> tuple[tuple[int, ...], int | None]:
    """Parse a chord with an optional slash-bass pitch class."""
    if symbol.count("/") > 1:
        raise ValueError(f"unsupported chord: {symbol!r}")
    base, sep, bass = symbol.partition("/")
    tones = chord_tones(base)
    if not sep:
        return tones, None
    if bass not in PITCH_CLASSES:
        raise ValueError(f"unsupported slash bass: {bass!r}")
    bass_pc = PITCH_CLASSES[bass]
    if bass_pc not in tones:
        raise ValueError("slash bass must be a chord tone")
    return tones, bass_pc


def _candidates(symbol: str, low: int, high: int) -> list[tuple[int, ...]]:
    pcs, bass = _parse_chord(symbol)
    pools = [[note for note in range(low, high + 1) if note % 12 == pc] for pc in pcs]
    return sorted({tuple(sorted(notes)) for notes in itertools.product(*pools)
                   if len(set(notes)) == len(notes)
                   and (bass is None or min(notes) % 12 == bass)})


def voice_lead(chords: list[str], low: int = 48, high: int = 72) -> list[tuple[int, ...]]:
    """Choose successive inversions minimizing total voice movement.

    Dynamic programming evaluates all octave placements within the inclusive range.
    Chords must have equal voice counts; ties resolve lexicographically.
    """
    if not chords:
        return []
    if (not isinstance(low, int) or isinstance(low, bool)
            or not isinstance(high, int) or isinstance(high, bool)
            or low < 0 or high > 127 or low > high):
        raise ValueError("register bounds must be MIDI notes 0..127 with low <= high")
    candidates = [_candidates(chord, low, high) for chord in chords]
    if any(not options for options in candidates):
        raise ValueError("register contains no valid voicing for a chord")
    voices = len(candidates[0][0])
    if any(len(options[0]) != voices for options in candidates):
        raise ValueError("all chords must contain the same number of notes")
    costs = {option: (0, (option,)) for option in candidates[0]}
    for options in candidates[1:]:
        next_costs = {}
        for option in options:
            prev, (cost, path) = min(costs.items(), key=lambda item: (
                item[1][0] + sum(abs(a - b) for a, b in zip(item[0], option)),
                item[1][1] + (option,)))
            next_costs[option] = (cost + sum(abs(a - b) for a, b in zip(prev, option)), path + (option,))
        costs = next_costs
    return list(min(costs.values(), key=lambda value: (value[0], value[1]))[1])


def total_motion(voicings: list[tuple[int, ...]]) -> int:
    """Return summed absolute semitone travel between adjacent voicings."""
    return sum(sum(abs(a - b) for a, b in zip(left, right))
               for left, right in zip(voicings, voicings[1:]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chords", nargs="*", default=["C", "F", "G", "C"])
    parser.add_argument("--low", type=int, default=48)
    parser.add_argument("--high", type=int, default=72)
    parser.add_argument("--stats", action="store_true", help="show total semitone travel")
    args = parser.parse_args()
    voicings = voice_lead(args.chords, args.low, args.high)
    for symbol, notes in zip(args.chords, voicings):
        print(f"{symbol}: {' '.join(map(str, notes))}")
    if args.stats:
        print(f"Total motion: {total_motion(voicings)} semitones")


if __name__ == "__main__":
    main()
