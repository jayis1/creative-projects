"""Viewport — a rectangular region of the complex plane."""
from __future__ import annotations

from typing import Optional


class Viewport:
    """A rectangular viewport of the complex plane.

    Parameters
    ----------
    center : complex
        Centre of the viewport.
    width : float
        Span along the real axis.
    height : float or None
        Span along the imaginary axis. If ``None`` or <= 0, it is set equal
        to ``width`` (square) unless ``aspect`` is given.
    aspect : float or None
        Pixel aspect ratio (width/height). If given and ``height`` is
        unspecified, the height is derived as ``width / aspect``.
    """

    def __init__(self, center, width, height=None, aspect=None):
        self.center = complex(center)
        self.width = float(width)
        if height is None or height <= 0:
            self.height = self.width if aspect is None else self.width / aspect
        else:
            self.height = float(height)

    def __repr__(self):
        return (f"Viewport(center={self.center}, width={self.width}, "
                f"height={self.height})")

    def x_range(self):
        """Return ``(x_min, x_max)`` of the real-axis span."""
        return (self.center.real - self.width / 2,
                self.center.real + self.width / 2)

    def y_range(self):
        """Return ``(y_min, y_max)`` of the imaginary-axis span."""
        return (self.center.imag - self.height / 2,
                self.center.imag + self.height / 2)

    def zoom(self, factor: float) -> "Viewport":
        """Return a new viewport zoomed by ``factor`` (<1 zooms in)."""
        return Viewport(self.center, self.width * factor,
                        self.height * factor)

    def to_dict(self):
        """Serialize to a JSON-friendly dict."""
        return {"center_re": self.center.real, "center_im": self.center.imag,
                "width": self.width, "height": self.height}

    @classmethod
    def from_dict(cls, d):
        """Deserialize from a dict produced by :meth:`to_dict`."""
        return cls(complex(d["center_re"], d["center_im"]),
                   d["width"], d.get("height"))

    def copy(self) -> "Viewport":
        """Return a shallow copy (so callers can't mutate us)."""
        return Viewport(self.center, self.width, self.height)

    def pixel_to_complex(self, col: int, row: int, width: int,
                          height: int) -> complex:
        """Map pixel ``(col, row)`` to a complex coordinate."""
        x_min, x_max = self.x_range()
        y_min, y_max = self.y_range()
        dx = (x_max - x_min) / width
        dy = (y_max - y_min) / height
        return complex(x_min + (col + 0.5) * dx,
                       y_min + (row + 0.5) * dy)

    def fit_aspect(self, pixel_aspect: float) -> "Viewport":
        """Return a new Viewport adjusted for the given pixel aspect.

        ``pixel_aspect`` is width/height.  The width is kept fixed and the
        height is adjusted so the complex-plane region matches the pixel
        aspect ratio (no stretching)."""
        plane_aspect = self.width / self.height
        if abs(plane_aspect - pixel_aspect) > 1e-9:
            return Viewport(self.center, self.width,
                            self.width / pixel_aspect)
        return self.copy()