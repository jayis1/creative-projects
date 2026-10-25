# Linebreak Lab

A zero-dependency paragraph composer that turns words into terminal-sized lines. Unlike a toy wrapper, it measures combining marks and full-width East Asian characters and rejects unbreakable words instead of silently overflowing the requested measure.

## Quick start

```sh
python3 linebreak.py --demo
```

## How it works

Greedy mode appends words while the measured display width fits. Balanced mode uses dynamic programming to minimize the sum of squared unused columns (the final line has no raggedness penalty). This is O(n²) in word count and intentionally chooses paragraph-wide quality over streaming output.

## Usage

```sh
python3 linebreak.py -w 18 "A paragraph to lay out neatly"
python3 linebreak.py --balanced -w 18 "A paragraph to lay out neatly"
```

Whitespace is normalized, words are never split, combining marks occupy zero columns and East Asian wide/full-width characters occupy two.

## Limitations

Terminal-specific emoji grapheme widths and language-specific line-breaking rules are not modeled. Balanced mode has quadratic worst-case time and is intended for bounded paragraphs, not arbitrarily long documents.
