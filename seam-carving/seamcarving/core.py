#!/usr/bin/env python3
"""
seamcarving/core.py — Core seam carving algorithm.

Implements content-aware image resizing via seam carving (Avidan & Shamir, 2007).
Supports:
  - Multiple energy functions: Sobel gradient, Hofer & Schmalzieg, backward/forward energy
  - Vertical and horizontal seam removal and insertion
  - Object removal via mask protection
  - Real-time energy map and seam visualization
  - PPM (P6) image I/O (no external image libraries required)

Dependencies: numpy only.
"""

from __future__ import annotations

import enum
import sys
from typing import Optional, Tuple

import numpy as np


class EnergyType(enum.Enum):
    """Available energy functions for seam computation."""

    SOBEL = "sobel"          # Sobel gradient magnitude
    GRADIENT = "gradient"    # Simple central-difference gradient
    FORWARD = "forward"      # Forward energy (Avidan et al. 2008 improvement)


# ---------------------------------------------------------------------------
# Image I/O — PPM (P6) reader/writer, no external deps
# ---------------------------------------------------------------------------

def read_ppm(path: str) -> np.ndarray:
    """Read a binary PPM (P6) file and return an (H, W, 3) uint8 array."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:2] != b"P6":
        raise ValueError(f"Not a binary PPM (P6) file: {path}")
    # Parse header: P6 <width> <height> <maxval> <binary data>
    idx = 2
    vals: list[int] = []
    while len(vals) < 3:
        # skip whitespace and comments
        while idx < len(data) and data[idx:idx+1].isspace():
            idx += 1
        if idx < len(data) and data[idx:idx+1] == b"#":
            while idx < len(data) and data[idx:idx+1] != b"\n":
                idx += 1
            continue
        start = idx
        while idx < len(data) and not data[idx:idx+1].isspace():
            idx += 1
        vals.append(int(data[start:idx]))
    idx += 1  # single whitespace after maxval
    w, h, maxval = vals
    if maxval != 255:
        raise ValueError(f"Unsupported maxval {maxval}, expected 255")
    pixels = np.frombuffer(data[idx:], dtype=np.uint8, count=h * w * 3)
    return pixels.reshape(h, w, 3).copy()


def write_ppm(path: str, img: np.ndarray) -> None:
    """Write an (H, W, 3) uint8 array as a binary PPM (P6) file."""
    if img.dtype != np.uint8:
        img = np.clip(img, 0, 255).astype(np.uint8)
    h, w = img.shape[:2]
    header = f"P6\n{w} {h}\n255\n".encode()
    with open(path, "wb") as f:
        f.write(header)
        f.write(img.tobytes())


# ---------------------------------------------------------------------------
# Energy functions
# ---------------------------------------------------------------------------

def _to_gray(img: np.ndarray) -> np.ndarray:
    """Convert RGB image to grayscale using luminance weights."""
    return (
        img[:, :, 0].astype(np.float64) * 0.299
        + img[:, :, 1].astype(np.float64) * 0.587
        + img[:, :, 2].astype(np.float64) * 0.114
    )


def _sobel_energy(gray: np.ndarray) -> np.ndarray:
    """Compute energy using Sobel operator magnitude."""
    gx = np.zeros_like(gray)
    gy = np.zeros_like(gray)
    gx[1:-1, 1:-1] = (
        -gray[:-2, :-2] - 2 * gray[:-2, 1:-1] - gray[:-2, 2:]
        + gray[2:, :-2] + 2 * gray[2:, 1:-1] + gray[2:, 2:]
    )
    gy[1:-1, 1:-1] = (
        -gray[:-2, :-2] + gray[:-2, 2:]
        - 2 * gray[1:-1, :-2] + 2 * gray[1:-1, 2:]
        - gray[2:, :-2] + gray[2:, 2:]
    )
    return np.abs(gx) + np.abs(gy)


def _gradient_energy(gray: np.ndarray) -> np.ndarray:
    """Simple central-difference gradient energy."""
    gx = np.zeros_like(gray)
    gy = np.zeros_like(gray)
    gx[:, 1:-1] = (gray[:, 2:] - gray[:, :-2]) / 2.0
    gy[1:-1, :] = (gray[2:, :] - gray[:-2, :]) / 2.0
    return np.abs(gx) + np.abs(gy)


def _forward_energy(gray: np.ndarray) -> np.ndarray:
    """
    Forward energy cost (improvement from Avidan et al. 2008).
    Accounts for the energy introduced by removing a seam, not just
    the energy at the pixel.
    """
    h, w = gray.shape
    # Compute differences
    cu = np.zeros_like(gray)
    cL = np.zeros_like(gray)
    cR = np.zeros_like(gray)

    cu[:, 1:-1] = np.abs(gray[:, 2:] - gray[:, :-2])
    cL[:, 1:-1] = np.abs(gray[:, 1:-1] - gray[:, :-2]) + cu[:, 1:-1]
    cR[:, 1:-1] = np.abs(gray[:, 1:-1] - gray[:, 2:]) + cu[:, 1:-1]

    # Accumulate via DP
    M = np.zeros_like(gray)
    M[0] = cu[0]
    for i in range(1, h):
        m_up = M[i - 1]
        m_left = np.empty_like(m_up)
        m_right = np.empty_like(m_up)
        m_left[1:] = m_up[:-1]
        m_left[0] = m_up[0]  # boundary: treat as up
        m_right[:-1] = m_up[1:]
        m_right[-1] = m_up[-1]  # boundary: treat as up

        M[i] = cu[i] + np.minimum(np.minimum(m_up, m_left), m_right)
        # Add directional costs
        # Where came from left, add cL; from right, add cR; from up, add 0
        # We need element-wise: actually M[i] should be min of:
        #   M[i-1, j-1] + cL[i,j], M[i-1,j] + cu[i,j], M[i-1,j+1] + cR[i,j]
        # Let's redo properly:
        pass

    # Redo forward energy properly with vectorized DP
    M = np.zeros((h, w), dtype=np.float64)
    M[0] = cu[0]
    for i in range(1, h):
        up = M[i - 1, :]
        left = np.empty(w)
        right = np.empty(w)
        left[0] = np.inf
        left[1:] = up[:-1]
        right[-1] = np.inf
        right[:-1] = up[1:]

        cost_up = up + cu[i]
        cost_left = left + cL[i]
        cost_right = right + cR[i]

        M[i] = np.minimum(np.minimum(cost_up, cost_left), cost_right)

    return M


# ---------------------------------------------------------------------------
# Seam Carver
# ---------------------------------------------------------------------------

class SeamCarver:
    """
    Content-aware image resizer using seam carving.

    Parameters
    ----------
    image : np.ndarray
        (H, W, C) uint8 array (C=3 for RGB, C=1 for grayscale).
    energy_type : EnergyType
        Which energy function to use for seam computation.
    protect_mask : np.ndarray, optional
        (H, W) boolean array. True = protect this pixel (high energy boost).
    remove_mask : np.ndarray, optional
        (H, W) boolean array. True = mark for removal (negative energy).

    Attributes
    ----------
    image : np.ndarray
        Current working image.
    energy : np.ndarray
        Current energy map (last computed).
    """

    PROTECT_BOOST = 1e6
    REMOVE_PENALTY = -1e6

    def __init__(
        self,
        image: np.ndarray,
        energy_type: EnergyType = EnergyType.SOBEL,
        protect_mask: Optional[np.ndarray] = None,
        remove_mask: Optional[np.ndarray] = None,
    ) -> None:
        if image.ndim != 3 or image.shape[2] not in (1, 3):
            raise ValueError(
                f"Image must be (H, W, C) with C=1 or 3, got shape {image.shape}"
            )
        if image.dtype != np.uint8:
            image = np.clip(image, 0, 255).astype(np.uint8)

        self.image = image.copy()
        self.energy_type = energy_type
        self.h, self.w = image.shape[:2]
        self.num_seams_carved = 0

        self.protect_mask = (
            protect_mask.copy() if protect_mask is not None else None
        )
        self.remove_mask = (
            remove_mask.copy() if remove_mask is not None else None
        )
        self.energy: Optional[np.ndarray] = None

    # -- energy computation -------------------------------------------------

    def _compute_energy(self) -> np.ndarray:
        """Compute the energy map for the current image."""
        gray = _to_gray(self.image) if self.image.shape[2] == 3 else self.image[:, :, 0].astype(np.float64)

        if self.energy_type == EnergyType.SOBEL:
            e = _sobel_energy(gray)
        elif self.energy_type == EnergyType.GRADIENT:
            e = _gradient_energy(gray)
        elif self.energy_type == EnergyType.FORWARD:
            e = _forward_energy(gray)
        else:
            raise ValueError(f"Unknown energy type: {self.energy_type}")

        # Apply mask modifiers
        if self.protect_mask is not None:
            e[self.protect_mask] += self.PROTECT_BOOST
        if self.remove_mask is not None:
            e[self.remove_mask] += self.REMOVE_PENALTY

        self.energy = e
        return e

    # -- seam finding (vertical seams) --------------------------------------

    def _find_vertical_seam(self) -> np.ndarray:
        """
        Find the lowest-energy vertical seam using dynamic programming.
        Returns an array of column indices, one per row (length = H).
        """
        energy = self._compute_energy()
        h, w = energy.shape
        M = energy.copy().astype(np.float64)

        for i in range(1, h):
            # Vectorized: for each pixel, take min of three above
            up = M[i - 1, :]
            left = np.empty(w)
            right = np.empty(w)
            left[0] = np.inf
            left[1:] = up[:-1]
            right[-1] = np.inf
            right[:-1] = up[1:]
            M[i] += np.minimum(np.minimum(up, left), right)

        # Backtrace
        seam = np.empty(h, dtype=np.int64)
        seam[-1] = int(np.argmin(M[-1]))
        for i in range(h - 2, -1, -1):
            j = seam[i + 1]
            # Check three neighbors above
            candidates = [j]
            if j > 0:
                candidates.append(j - 1)
            if j < w - 1:
                candidates.append(j + 1)
            seam[i] = min(candidates, key=lambda c: M[i, c])

        return seam

    def _find_horizontal_seam(self) -> np.ndarray:
        """Find the lowest-energy horizontal seam (transpose, find vertical)."""
        self.image = np.transpose(self.image, (1, 0, 2))
        self.h, self.w = self.w, self.h
        if self.protect_mask is not None:
            self.protect_mask = self.protect_mask.T
        if self.remove_mask is not None:
            self.remove_mask = self.remove_mask.T
        seam = self._find_vertical_seam()
        # Transpose back
        self.image = np.transpose(self.image, (1, 0, 2))
        self.h, self.w = self.w, self.h
        if self.protect_mask is not None:
            self.protect_mask = self.protect_mask.T
        if self.remove_mask is not None:
            self.remove_mask = self.remove_mask.T
        return seam

    # -- seam removal -------------------------------------------------------

    def _remove_vertical_seam(self, seam: np.ndarray) -> None:
        """Remove a vertical seam from the image (width decreases by 1)."""
        h, w, c = self.image.shape
        new_img = np.zeros((h, w - 1, c), dtype=np.uint8)
        for i in range(h):
            j = seam[i]
            new_img[i, :j] = self.image[i, :j]
            new_img[i, j:] = self.image[i, j + 1:]
        self.image = new_img
        self.w -= 1

        if self.protect_mask is not None:
            new_protect = np.zeros((h, w - 1), dtype=bool)
            for i in range(h):
                j = seam[i]
                new_protect[i, :j] = self.protect_mask[i, :j]
                new_protect[i, j:] = self.protect_mask[i, j + 1:]
            self.protect_mask = new_protect
        if self.remove_mask is not None:
            new_remove = np.zeros((h, w - 1), dtype=bool)
            for i in range(h):
                j = seam[i]
                new_remove[i, :j] = self.remove_mask[i, :j]
                new_remove[i, j:] = self.remove_mask[i, j + 1:]
            self.remove_mask = new_remove

    def _remove_horizontal_seam(self, seam: np.ndarray) -> None:
        """Remove a horizontal seam (height decreases by 1)."""
        h, w, c = self.image.shape
        new_img = np.zeros((h - 1, w, c), dtype=np.uint8)
        for j in range(w):
            i = seam[j]
            new_img[:i, j] = self.image[:i, j]
            new_img[i:, j] = self.image[i + 1:, j]
        self.image = new_img
        self.h -= 1

        if self.protect_mask is not None:
            new_protect = np.zeros((h - 1, w), dtype=bool)
            for j in range(w):
                i = seam[j]
                new_protect[:i, j] = self.protect_mask[:i, j]
                new_protect[i:, j] = self.protect_mask[i + 1:, j]
            self.protect_mask = new_protect
        if self.remove_mask is not None:
            new_remove = np.zeros((h - 1, w), dtype=bool)
            for j in range(w):
                i = seam[j]
                new_remove[:i, j] = self.remove_mask[:i, j]
                new_remove[i:, j] = self.remove_mask[i + 1:, j]
            self.remove_mask = new_remove

    # -- seam insertion -----------------------------------------------------

    def _insert_vertical_seam(self, seam: np.ndarray) -> None:
        """Insert a vertical seam by averaging adjacent pixels."""
        h, w, c = self.image.shape
        new_img = np.zeros((h, w + 1, c), dtype=np.uint8)
        for i in range(h):
            j = seam[i]
            # Average the seam pixel with its neighbor for the inserted pixel
            if j < w - 1:
                avg = ((self.image[i, j].astype(np.uint16) + self.image[i, j + 1].astype(np.uint16)) // 2).astype(np.uint8)
            else:
                avg = self.image[i, j].copy()
            new_img[i, :j] = self.image[i, :j]
            new_img[i, j] = avg
            new_img[i, j + 1:] = self.image[i, j:]
        self.image = new_img
        self.w += 1
        # Shift remaining seam positions for multi-insertion consistency
        # (handled by caller)

    def _insert_horizontal_seam(self, seam: np.ndarray) -> None:
        """Insert a horizontal seam by averaging adjacent pixels."""
        h, w, c = self.image.shape
        new_img = np.zeros((h + 1, w, c), dtype=np.uint8)
        for j in range(w):
            i = seam[j]
            if i < h - 1:
                avg = ((self.image[i, j].astype(np.uint16) + self.image[i + 1, j].astype(np.uint16)) // 2).astype(np.uint8)
            else:
                avg = self.image[i, j].copy()
            new_img[:i, j] = self.image[:i, j]
            new_img[i, j] = avg
            new_img[i + 1:, j] = self.image[i:, j]
        self.image = new_img
        self.h += 1

    # -- public API ---------------------------------------------------------

    def carve_vertical(self, num_seams: int) -> np.ndarray:
        """Remove `num_seams` vertical seams (reduces width)."""
        for _ in range(abs(num_seams)):
            seam = self._find_vertical_seam()
            self._remove_vertical_seam(seam)
            self.num_seams_carved += 1
        return self.image

    def carve_horizontal(self, num_seams: int) -> np.ndarray:
        """Remove `num_seams` horizontal seams (reduces height)."""
        for _ in range(abs(num_seams)):
            seam = self._find_horizontal_seam()
            self._remove_horizontal_seam(seam)
            self.num_seams_carved += 1
        return self.image

    def insert_vertical(self, num_seams: int) -> np.ndarray:
        """
        Insert `num_seams` vertical seams (increases width).
        Uses the optimal seam insertion approach: find seams on original,
        then insert in order with index adjustment.
        """
        seams_to_insert: list[np.ndarray] = []
        temp_carver = SeamCarver(self.image.copy(), self.energy_type)
        for _ in range(num_seams):
            seam = temp_carver._find_vertical_seam()
            seams_to_insert.append(seam)
            temp_carver._remove_vertical_seam(seam)

        # Insert seams in order with index adjustment.
        # Each previously-inserted seam shifts subsequent seam positions.
        for idx, seam in enumerate(seams_to_insert):
            adjusted = seam.copy()
            for prev in seams_to_insert[:idx]:
                adjusted += (seam >= prev).astype(int)
            self._insert_vertical_seam(adjusted)
            self.num_seams_carved += 1
        return self.image

    def insert_horizontal(self, num_seams: int) -> np.ndarray:
        """Insert `num_seams` horizontal seams (increases height)."""
        seams_to_insert: list[np.ndarray] = []
        temp_carver = SeamCarver(self.image.copy(), self.energy_type)
        for _ in range(num_seams):
            seam = temp_carver._find_horizontal_seam()
            seams_to_insert.append(seam)
            temp_carver._remove_horizontal_seam(seam)

        for idx, seam in enumerate(seams_to_insert):
            adjusted = seam.copy()
            for prev in seams_to_insert[:idx]:
                adjusted += (seam >= prev).astype(int)
            self._insert_horizontal_seam(adjusted)
            self.num_seams_carved += 1
        return self.image

    def remove_object(self, remove_mask: np.ndarray, max_iterations: int = 500) -> np.ndarray:
        """
        Remove an object specified by `remove_mask` (boolean H×W array).
        Removes seams until all marked pixels are gone, choosing vertical
        or horizontal seams based on the mask's aspect ratio.
        """
        if remove_mask.shape != (self.h, self.w):
            raise ValueError("Remove mask must match image dimensions")
        self.remove_mask = remove_mask.copy()

        iterations = 0
        while self.remove_mask.any() and iterations < max_iterations:
            # Choose orientation: if mask is wider than tall, remove vertical
            rows_with_mask = np.any(self.remove_mask, axis=1).sum()
            cols_with_mask = np.any(self.remove_mask, axis=0).sum()
            if cols_with_mask >= rows_with_mask:
                seam = self._find_vertical_seam()
                self._remove_vertical_seam(seam)
            else:
                seam = self._find_horizontal_seam()
                self._remove_horizontal_seam(seam)
            self.num_seams_carved += 1
            iterations += 1

        self.remove_mask = None
        return self.image

    def get_energy_map(self) -> np.ndarray:
        """Return the current energy map (normalized to 0-255 for visualization)."""
        e = self._compute_energy()
        e_min, e_max = e.min(), e.max()
        if e_max - e_min < 1e-10:
            return np.zeros_like(e, dtype=np.uint8)
        normalized = ((e - e_min) / (e_max - e_min) * 255).astype(np.uint8)
        return normalized

    def visualize_seam(self, seam: np.ndarray, orientation: str = "vertical") -> np.ndarray:
        """
        Draw a seam on a copy of the current image.
        Seam pixels are highlighted in red (255, 0, 0).
        """
        vis = self.image.copy()
        if vis.shape[2] == 1:
            vis = np.repeat(vis, 3, axis=2)
        if orientation == "vertical":
            for i, j in enumerate(seam):
                vis[i, j] = [255, 0, 0]
        else:
            for j, i in enumerate(seam):
                vis[i, j] = [255, 0, 0]
        return vis


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def resize_width(image: np.ndarray, target_width: int, energy_type: EnergyType = EnergyType.SOBEL) -> np.ndarray:
    """Resize image to target width using seam carving."""
    h, w = image.shape[:2]
    diff = target_width - w
    carver = SeamCarver(image, energy_type=energy_type)
    if diff < 0:
        return carver.carve_vertical(-diff)
    elif diff > 0:
        return carver.insert_vertical(diff)
    return image


def resize_height(image: np.ndarray, target_height: int, energy_type: EnergyType = EnergyType.SOBEL) -> np.ndarray:
    """Resize image to target height using seam carving."""
    h, w = image.shape[:2]
    diff = target_height - h
    carver = SeamCarver(image, energy_type=energy_type)
    if diff < 0:
        return carver.carve_horizontal(-diff)
    elif diff > 0:
        return carver.insert_horizontal(diff)
    return image


def resize(
    image: np.ndarray,
    target_width: int,
    target_height: int,
    energy_type: EnergyType = EnergyType.SOBEL,
) -> np.ndarray:
    """Resize image to target dimensions using seam carving."""
    carver = SeamCarver(image, energy_type=energy_type)
    w_diff = target_width - carver.w
    h_diff = target_height - carver.h
    # Remove first, then insert (order matters for quality)
    if w_diff < 0:
        carver.carve_vertical(-w_diff)
    if h_diff < 0:
        carver.carve_horizontal(-h_diff)
    if w_diff > 0:
        carver.insert_vertical(w_diff)
    if h_diff > 0:
        carver.insert_horizontal(h_diff)
    return carver.image


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    """Command-line interface for seam carving."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Content-aware image resizing via seam carving"
    )
    parser.add_argument("input", help="Input PPM (P6) image file")
    parser.add_argument("output", help="Output PPM (P6) image file")
    parser.add_argument("-W", "--width", type=int, help="Target width")
    parser.add_argument("-H", "--height", type=int, help="Target height")
    parser.add_argument(
        "-e", "--energy",
        choices=["sobel", "gradient", "forward"],
        default="sobel",
        help="Energy function to use",
    )
    parser.add_argument(
        "--energy-map", metavar="PATH",
        help="Save the energy map visualization to this PPM file",
    )
    args = parser.parse_args()

    img = read_ppm(args.input)
    energy_type = EnergyType(args.energy)

    if args.width is not None or args.height is not None:
        tw = args.width if args.width is not None else img.shape[1]
        th = args.height if args.height is not None else img.shape[0]
        result = resize(img, tw, th, energy_type=energy_type)
    else:
        print("No target dimensions specified, outputting original image.")
        result = img

    write_ppm(args.output, result)
    print(f"Input:  {img.shape[1]}x{img.shape[0]}")
    print(f"Output: {result.shape[1]}x{result.shape[0]}")
    print(f"Energy: {args.energy}")

    if args.energy_map:
        carver = SeamCarver(img, energy_type=energy_type)
        emap = carver.get_energy_map()
        # Convert grayscale energy to RGB for PPM
        emap_rgb = np.repeat(emap[:, :, np.newaxis], 3, axis=2)
        write_ppm(args.energy_map, emap_rgb)
        print(f"Energy map saved to: {args.energy_map}")

    return 0


if __name__ == "__main__":
    sys.exit(main())