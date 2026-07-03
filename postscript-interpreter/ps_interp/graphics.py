"""Graphics state and canvas for PostScript rendering.

Implements the PostScript imaging model primitives:
  - current path (moveto, lineto, curveto, closepath)
  - CTM (current transformation matrix) via 2×3 affine matrices
  - graphics state stack (gsave/grestore)
  - stroke / fill with current color and linewidth
  - clipping path
  - SVG and PPM (raw pixmap) raster output
"""

import math
import struct
from .errors import PSTypeError, PSRangeCheck


class Matrix:
    """2×3 affine transformation matrix [a b c d e f].
    Point transform:  x' = a*x + c*y + e
                      y' = b*x + d*y + f
    """
    __slots__ = ("a", "b", "c", "d", "e", "f")
    def __init__(self, a=1, b=0, c=0, d=1, e=0, f=0):
        self.a, self.b, self.c, self.d, self.e, self.f = a, b, c, d, e, f

    @staticmethod
    def identity():
        return Matrix(1, 0, 0, 1, 0, 0)

    @staticmethod
    def translation(tx, ty):
        return Matrix(1, 0, 0, 1, tx, ty)

    @staticmethod
    def scaling(sx, sy):
        return Matrix(sx, 0, 0, sy, 0, 0)

    @staticmethod
    def rotation(deg):
        r = math.radians(deg)
        c, s = math.cos(r), math.sin(r)
        return Matrix(c, s, -s, c, 0, 0)

    def multiply(self, other):
        """Return self * other (other applied first)."""
        a = self.a * other.a + self.c * other.b
        b = self.b * other.a + self.d * other.b
        c = self.a * other.c + self.c * other.d
        d = self.b * other.c + self.d * other.d
        e = self.a * other.e + self.c * other.f + self.e
        f = self.b * other.e + self.d * other.f + self.f
        return Matrix(a, b, c, d, e, f)

    def transform(self, x, y):
        return (self.a * x + self.c * y + self.e,
                self.b * x + self.d * y + self.f)

    def invert(self):
        det = self.a * self.d - self.b * self.c
        if abs(det) < 1e-15:
            raise PSTypeError("Singular matrix (cannot invert)")
        inv_det = 1.0 / det
        a = self.d * inv_det
        b = -self.b * inv_det
        c = -self.c * inv_det
        d = self.a * inv_det
        e = -(a * self.e + c * self.f)
        f = -(b * self.e + d * self.f)
        return Matrix(a, b, c, d, e, f)

    def copy(self):
        return Matrix(self.a, self.b, self.c, self.d, self.e, self.f)

    def to_list(self):
        return [self.a, self.b, self.c, self.d, self.e, self.f]

    @staticmethod
    def from_list(lst):
        if len(lst) != 6:
            raise PSRangeCheck("Matrix requires 6 elements")
        return Matrix(*lst)

    def __eq__(self, other):
        if not isinstance(other, Matrix):
            return False
        return self.to_list() == other.to_list()

    def __repr__(self):
        return f"Matrix[{self.a:.3f} {self.b:.3f} {self.c:.3f} {self.d:.3f} {self.e:.3f} {self.f:.3f}]"


class SubPath:
    """A subpath: list of points plus a flag whether it's closed."""
    __slots__ = ("points", "closed", "start")
    def __init__(self, start):
        self.points = [start]
        self.closed = False
        self.start = start

    def add(self, pt):
        self.points.append(pt)

    def close(self):
        self.closed = True


class Path:
    """A PostScript current path consisting of subpaths."""
    __slots__ = ("subpaths", "current")
    def __init__(self):
        self.subpaths = []
        self.current = None

    def moveto(self, x, y):
        sp = SubPath((x, y))
        self.subpaths.append(sp)
        self.current = sp

    def lineto(self, x, y):
        if self.current is None:
            self.moveto(x, y)
            return
        self.current.add((x, y))

    def curveto(self, x1, y1, x2, y2, x3, y3):
        if self.current is None:
            self.moveto(x1, y1)
        # cubic bezier approximated by line segments
        self._bezier(self.current.points[-1], (x1, y1), (x2, y2), (x3, y3))

    def _bezier(self, p0, p1, p2, p3, steps=24):
        for i in range(1, steps + 1):
            t = i / steps
            mt = 1 - t
            x = mt*mt*mt*p0[0] + 3*mt*mt*t*p1[0] + 3*mt*t*t*p2[0] + t*t*t*p3[0]
            y = mt*mt*mt*p0[1] + 3*mt*mt*t*p1[1] + 3*mt*t*t*p2[1] + t*t*t*p3[1]
            self.current.add((x, y))

    def closepath(self):
        if self.current is not None and not self.current.closed:
            self.current.closed = True

    def is_empty(self):
        return not self.subpaths

    def clear(self):
        self.subpaths = []
        self.current = None

    def copy(self):
        p = Path()
        for sp in self.subpaths:
            nsp = SubPath(sp.start)
            nsp.points = list(sp.points)
            nsp.closed = sp.closed
            p.subpaths.append(nsp)
            if sp is self.current:
                p.current = nsp
        return p


class GraphicsState:
    """Full graphics state snapshot for gsave/grestore."""
    __slots__ = ("ctm", "color", "linewidth", "linecap", "linejoin",
                 "miterlimit", "dash", "dash_offset", "font",
                 "path", "clip", "flatness", "fill_overprint",
                 "stroke_overprint")
    def __init__(self):
        self.ctm = Matrix.identity()
        self.color = (0.0, 0.0, 0.0)        # gray
        self.linewidth = 1.0
        self.linecap = 0
        self.linejoin = 0
        self.miterlimit = 10.0
        self.dash = None
        self.dash_offset = 0
        self.font = None
        self.path = Path()
        self.clip = None
        self.flatness = 1.0
        self.fill_overprint = False
        self.stroke_overprint = False

    def copy(self):
        g = GraphicsState()
        g.ctm = self.ctm.copy()
        g.color = self.color
        g.linewidth = self.linewidth
        g.linecap = self.linecap
        g.linejoin = self.linejoin
        g.miterlimit = self.miterlimit
        g.dash = self.dash
        g.dash_offset = self.dash_offset
        g.font = self.font
        g.path = self.path.copy()
        g.clip = self.clip.copy() if self.clip else None
        g.flatness = self.flatness
        g.fill_overprint = self.fill_overprint
        g.stroke_overprint = self.stroke_overprint
        return g


class Canvas:
    """Raster canvas for PPM output.  Simple scanline z-buffer-less painter."""
    def __init__(self, width, height):
        self.width = width
        self.height = height
        # pixels stored as flat bytearray of RGB triplets, white background
        self.pixels = bytearray([255, 255, 255] * (width * height))

    def set_pixel(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            idx = (y * self.width + x) * 3
            self.pixels[idx]     = color[0]
            self.pixels[idx + 1] = color[1]
            self.pixels[idx + 2] = color[2]

    def get_pixel(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            idx = (y * self.width + x) * 3
            return (self.pixels[idx], self.pixels[idx+1], self.pixels[idx+2])
        return (0, 0, 0)

    def fill_rect(self, x0, y0, x1, y1, color):
        if x1 < x0: x0, x1 = x1, x0
        if y1 < y0: y0, y1 = y1, y0
        for y in range(max(0, int(y0)), min(self.height, int(y1))):
            row = y * self.width
            for x in range(max(0, int(x0)), min(self.width, int(x1))):
                idx = (row + x) * 3
                self.pixels[idx]     = color[0]
                self.pixels[idx + 1] = color[1]
                self.pixels[idx + 2] = color[2]

    def draw_line(self, x0, y0, x1, y1, color, width=1):
        """Bresenham line."""
        x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self._plot_thick(x0, y0, color, width)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy; x0 += sx
            if e2 < dx:
                err += dx; y0 += sy

    def _plot_thick(self, x, y, color, w):
        if w <= 1:
            self.set_pixel(x, y, color)
        else:
            r = w // 2
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if dx*dx + dy*dy <= r*r:
                        self.set_pixel(x + dx, y + dy, color)

    def fill_polygon(self, points, color):
        """Scanline polygon fill."""
        if len(points) < 3:
            return
        ys = [p[1] for p in points]
        y_min = max(0, int(math.floor(min(ys))))
        y_max = min(self.height - 1, int(math.ceil(max(ys))))
        n = len(points)
        for y in range(y_min, y_max + 1):
            yc = y + 0.5
            xs = []
            for i in range(n):
                x0, y0 = points[i]
                x1, y1 = points[(i + 1) % n]
                if y0 == y1:
                    continue
                if (y0 <= yc < y1) or (y1 <= yc < y0):
                    t = (yc - y0) / (y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                x0 = max(0, int(math.floor(xs[k])))
                x1 = min(self.width - 1, int(math.ceil(xs[k + 1])))
                for x in range(x0, x1 + 1):
                    self.set_pixel(x, y, color)

    def to_ppm(self) -> bytes:
        """Return raw PPM (P6) bytes."""
        header = f"P6\n{self.width} {self.height}\n255\n".encode('ascii')
        return header + bytes(self.pixels)

    def to_pgm(self) -> bytes:
        """Return raw PGM (P5) grayscale."""
        gray = bytearray(self.width * self.height)
        for i in range(self.width * self.height):
            r = self.pixels[i*3]; g = self.pixels[i*3+1]; b = self.pixels[i*3+2]
            gray[i] = (r // 3 + g // 3 + b // 3 + (r + g + b) % 3)
        header = f"P5\n{self.width} {self.height}\n255\n".encode('ascii')
        return header + bytes(gray)


def gray_to_rgb(gray):
    g = max(0, min(255, int(round((1 - gray) * 255))))
    return (g, g, g)