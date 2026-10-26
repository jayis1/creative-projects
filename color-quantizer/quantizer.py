"""Dependency-free PPM color quantizer using median-cut palette construction."""
from __future__ import annotations
import argparse
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Image:
    width: int
    height: int
    pixels: tuple[tuple[int, int, int], ...]

    def __post_init__(self):
        if self.width <= 0 or self.height <= 0 or len(self.pixels) != self.width * self.height:
            raise ValueError("dimensions must be positive and match pixel count")
        if any(len(p) != 3 or any(not 0 <= c <= 255 for c in p) for p in self.pixels):
            raise ValueError("pixels must be RGB triples in 0..255")

def read_ppm(path: str | Path) -> Image:
    """Read binary P6 PPM files, supporting comments and arbitrary whitespace."""
    data = Path(path).read_bytes()
    i, tokens = 0, []
    while len(tokens) < 4:
        while i < len(data) and data[i] in b" \t\r\n": i += 1
        if i < len(data) and data[i] == 35:
            while i < len(data) and data[i] not in b"\r\n": i += 1
            continue
        start = i
        while i < len(data) and data[i] not in b" \t\r\n#": i += 1
        if start == i: raise ValueError("malformed PPM header")
        tokens.append(data[start:i])
    if tokens[0] != b"P6": raise ValueError("expected binary P6 PPM")
    try: width, height, maximum = map(int, tokens[1:])
    except ValueError as exc: raise ValueError("invalid numeric PPM header") from exc
    if width <= 0 or height <= 0 or maximum != 255: raise ValueError("dimensions must be positive and maxval 255")
    # P6 header terminates with one whitespace delimiter; do not eat pixel bytes that happen to be whitespace.
    if i >= len(data) or data[i] not in b" \t\r\n": raise ValueError("missing pixel-data delimiter")
    i += 1
    raw = data[i:]
    if len(raw) != width * height * 3: raise ValueError("pixel data size does not match dimensions")
    return Image(width, height, tuple(tuple(raw[j:j+3]) for j in range(0, len(raw), 3)))

def write_ppm(image: Image, path: str | Path) -> None:
    Path(path).write_bytes(f"P6\n{image.width} {image.height}\n255\n".encode() + bytes(c for p in image.pixels for c in p))

def median_cut(pixels, count):
    if not 1 <= count <= 256: raise ValueError("palette size must be 1..256")
    boxes = [list(pixels)]
    while len(boxes) < count:
        candidates = [(max(max(p[k] for p in b)-min(p[k] for p in b) for k in range(3)), i) for i,b in enumerate(boxes) if len(b) > 1]
        if not candidates: break
        _, bi = max(candidates)
        box = boxes.pop(bi)
        channel = max(range(3), key=lambda k: max(p[k] for p in box)-min(p[k] for p in box))
        box.sort(key=lambda p: p[channel])
        mid = len(box)//2
        boxes.extend((box[:mid], box[mid:]))
    return tuple(tuple(sum(p[k] for p in b)//len(b) for k in range(3)) for b in boxes)

def quantize(image: Image, colors=8, dither=False) -> Image:
    palette = median_cut(image.pixels, colors)
    out = list(image.pixels)
    if dither:
        work = [list(map(float,p)) for p in image.pixels]
        for y in range(image.height):
            for x in range(image.width):
                idx = y*image.width+x
                old = work[idx]
                new = min(palette, key=lambda p: sum((old[k]-p[k])**2 for k in range(3)))
                out[idx] = new
                err = [old[k]-new[k] for k in range(3)]
                for dx,dy,w in ((1,0,7/16),(-1,1,3/16),(0,1,5/16),(1,1,1/16)):
                    nx,ny=x+dx,y+dy
                    if 0<=nx<image.width and ny<image.height:
                        dest=work[ny*image.width+nx]
                        for k in range(3): dest[k]=min(255,max(0,dest[k]+err[k]*w))
    else:
        out = [min(palette, key=lambda q: sum((p[k]-q[k])**2 for k in range(3))) for p in image.pixels]
    return Image(image.width,image.height,tuple(out))

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input"); parser.add_argument("output"); parser.add_argument("-n","--colors",type=int,default=8); parser.add_argument("--dither",action="store_true")
    args=parser.parse_args(argv)
    try: write_ppm(quantize(read_ppm(args.input),args.colors,args.dither),args.output)
    except (OSError,ValueError) as exc: parser.error(str(exc))
    return 0
if __name__ == "__main__": raise SystemExit(main())
