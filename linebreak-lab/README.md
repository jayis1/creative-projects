# Linebreak Lab

A zero-dependency paragraph composer that turns words into terminal-sized lines. Unlike a toy wrapper, it measures combining marks and full-width East Asian characters and rejects unbreakable words instead of silently overflowing the requested measure.

## Quick start

```sh
python3 linebreak.py --demo
```

## How it works

The initial layout strategy greedily appends each word while its measured display width fits. Whitespace is normalized, and words are never split. Unicode combining marks occupy zero columns; East Asian wide/full-width characters occupy two.

## Usage

```sh
python3 linebreak.py -w 18 "A paragraph to lay out neatly"
```

## Limitations

This baseline strategy can leave ragged lines; the enhancement phase will add an optimized strategy. It does not account for terminal-specific emoji grapheme widths or language-specific line-breaking rules.
