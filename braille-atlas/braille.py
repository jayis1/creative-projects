"""Turn small grayscale images into Unicode Braille art, using only the stdlib."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PGM:
    width: int
    height: int
    maximum: int
    pixels: tuple[int, ...]


def read_pgm(path: str | Path) -> PGM:
    """Read binary or ASCII PGM (P5/P2), rejecting malformed and oversized files."""
    data = Path(path).read_bytes()
    if len(data) > 16_000_000:
        raise ValueError("PGM exceeds 16 MB limit")
    tokens: list[bytes] = []
    i = 0
    while i < len(data) and len(tokens) < 4:
        if data[i] in b" \t\r\n":
            i += 1
        elif data[i] == 35:  # PGM comment
            while i < len(data) and data[i] not in b"\r\n":
                i += 1
        else:
            start = i
            while i < len(data) and data[i] not in b" \t\r\n#":
                i += 1
            tokens.append(data[start:i])
    if len(tokens) != 4 or tokens[0] not in (b"P2", b"P5"):
        raise ValueError("expected P2/P5 PGM header")
    try:
        width, height, maximum = map(int, tokens[1:])
    except ValueError as exc:
        raise ValueError("invalid PGM dimensions or maximum") from exc
    if width < 1 or height < 1 or width * height > 1_000_000 or not 1 <= maximum <= 65535:
        raise ValueError("PGM dimensions or maximum outside supported range")
    if tokens[0] == b"P2":
        rest = data[i:].split(b"#", 1)[0].split()
        if len(rest) != width * height:
            raise ValueError("wrong number of PGM pixels")
        try:
            pixels = tuple(map(int, rest))
        except ValueError as exc:
            raise ValueError("invalid PGM pixel") from exc
    else:
        if i >= len(data) or data[i] not in b" \t\r\n":
            raise ValueError("missing PGM binary separator")
        i += 2 if data[i:i+2] == b"\r\n" else 1
        count = width * height
        step = 1 if maximum < 256 else 2
        raw = data[i:]
        if len(raw) != count * step:
            raise ValueError("wrong number of PGM binary pixels")
        pixels = tuple(raw) if step == 1 else tuple(int.from_bytes(raw[j:j+2], "big") for j in range(0, len(raw), 2))
    if any(p < 0 or p > maximum for p in pixels):
        raise ValueError("pixel outside declared grayscale range")
    return PGM(width, height, maximum, pixels)


def render(image: PGM, threshold: float = 0.5, invert: bool = False, dither: bool = False) -> str:
    """Render 2x4 pixel blocks; optionally apply Floyd–Steinberg error diffusion."""
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0 and 1")
    # Unicode Braille dot layout: columns top-to-bottom are 1,2,3,7 and 4,5,6,8.
    bits = ((0, 0, 1), (0, 1, 2), (0, 2, 4), (1, 0, 8),
            (1, 1, 16), (1, 2, 32), (0, 3, 64), (1, 3, 128))
    # Floyd–Steinberg diffusion makes grayscale gradients survive the 1-bit output.
    samples = [value / image.maximum for value in image.pixels]
    if dither:
        for y in range(image.height):
            for x in range(image.width):
                index = y * image.width + x
                old = samples[index]
                new = 0.0 if old < threshold else 1.0
                error = old - new
                samples[index] = new
                for dx, dy, weight in ((1, 0, 7 / 16), (-1, 1, 3 / 16), (0, 1, 5 / 16), (1, 1, 1 / 16)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < image.width and ny < image.height:
                        ni = ny * image.width + nx
                        samples[ni] = min(1.0, max(0.0, samples[ni] + error * weight))
    rows = []
    for y in range(0, image.height, 4):
        line = []
        for x in range(0, image.width, 2):
            mask = 0
            for dx, dy, bit in bits:
                px, py = x + dx, y + dy
                if px < image.width and py < image.height:
                    dark = samples[py * image.width + px] < threshold
                    if dark != invert:
                        mask |= bit
            line.append(chr(0x2800 + mask))
        rows.append("".join(line).rstrip("\u2800"))
    return "\n".join(rows)
