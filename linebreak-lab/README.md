# Linebreak Lab

A zero-dependency paragraph composer that turns words into terminal-sized lines. It measures combining marks and full-width East Asian characters and rejects unbreakable words instead of silently overflowing the requested measure.

## Quick start

```sh
python3 linebreak.py --demo
python3 -m unittest -v test_linebreak.py
```

## How it works

Greedy mode appends words while measured display width fits. Balanced mode uses dynamic programming to minimize squared unused columns (the final line has no raggedness penalty). It runs in O(n²) time for n words.

## Usage

```sh
python3 linebreak.py -w 18 "A paragraph to lay out neatly"
python3 linebreak.py --balanced -w 18 "A paragraph to lay out neatly"
```

Whitespace is normalized; words are never split. Combining marks count as zero columns and East Asian wide/full-width characters as two.

## Limitations

Terminal-specific emoji grapheme widths and language-specific line-breaking rules are not modeled. Balanced mode has quadratic worst-case time and is intended for bounded paragraphs.

## Known Issues (Resolved)

- Balanced layout initialized all dynamic-programming states with zero, causing a candidate with nonzero raggedness never to replace the default endpoint. `test_balanced_respects_width_and_preserves_words` reproduced over-width lines before the fix; initializing unreachable costs to infinity fixes it.

## Testing and edge cases

Four unittest cases cover empty and single-word paragraphs, width preservation, Unicode width, invalid widths, and oversized words.
