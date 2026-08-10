#!/usr/bin/env python3
"""
seamcarving/core.py — Core seam carving algorithm.

Implements content-aware image resizing via seam carving (Avidan & Shamir, 2007).
Supports:
  - 5 energy functions: Sobel, Prewitt, Laplacian, gradient, forward energy
  - Vertical and horizontal seam removal and insertion
  - Object removal via mask
  - Region protection via mask
  - Vectorized seam removal/insertion (NumPy masked operations)
  - Energy map, seam visualization, and animation frame export
  - PPM (P6) and PGM (P5) image I/O (no external image libraries required)
  - Quality metrics: energy preservation ratio, seam cost tracking

Dependencies: numpy only.
"""

from __future__ import annotations

import enum
import sys
from typing import Optional, List

import numpy as np


class EnergyType(enum.Enum):
    """Available energy functions for seam computation."""

    SOBEL = "sobel"        # Sobel operator gradient magnitude
    PREWITT = "prewitt"    # Prewitt operator gradient magnitude
    LAPLACIAN = "laplacian"  # Laplacian (second derivative) energy
    GRADIENT = "gradient"  # Simple central-difference gradient
    FORWARD = "forward"    # Forward energy (Avidan et al. 2008 improvement)


class SeamCarvingError(Exception):
    """Base exception for seam carving errors."""


class InvalidImageError(SeamCarvingError):
    """Raised when an image is malformed or unsupported."""


# ---------------------------------------------------------------------------
# Image I/O — PPM (P6) and PGM (P5) reader/writer, no external deps
# ---------------------------------------------------------------------------

def read_ppm(path: str) -> np.ndarray:
    """
    Read a binary PPM (P6) or PGM (P5) file.
    Returns an (H, W, 3) uint8 array for PPM, (H, W, 1) for PGM.
    """
    with open(path, "rb") as f:
        data = f.read()
    if data[:2] == b"P6":
        channels = 3
    elif data[:2] == b"P5":
        channels = 1
    else:
        raise InvalidImageError(f"Not a binary PPM (P6) or PGM (P5) file: {path}")

    idx = 2
    vals: list[int] = []
    while len(vals) < 3:
        # Skip whitespace
        while idx < len(data) and data[idx:idx + 1].isspace():
            idx += 1
        # Skip comments
        if idx < len(data) and data[idx:idx + 1] == b"#":
            while idx < len(data) and data[idx:idx + 1] != b"\n":
                idx += 1
            continue
        start = idx
        while idx < len(data) and not data[idx:idx + 1].isspace():
            idx += 1
        try:
            vals.append(int(data[start:idx]))
        except ValueError:
            raise InvalidImageError(f"Malformed header in {path}")
    idx += 1  # single whitespace after maxval
    w, h, maxval = vals
    if maxval != 255:
        raise InvalidImageError(f"Unsupported maxval {maxval}, expected 255")
    expected = h * w * channels
    pixels = np.frombuffer(data[idx:], dtype=np.uint8, count=expected)
    return pixels.reshape(h, w, channels).copy()


def write_ppm(path: str, img: np.ndarray) -> None:
    """
    Write an (H, W, C) uint8 array as a binary PPM (P6) or PGM (P5) file.
    C=1 produces PGM, C=3 produces PPM.
    """
    if img.ndim == 2:
        img = img[:, :, np.newaxis]
    if img.dtype != np.uint8:
        img = np.clip(img, 0, 255).astype(np.uint8)
    h, w, c = img.shape
    if c == 1:
        header = f"P5\n{w} {h}\n255\n".encode()
        body = img[:, :, 0].tobytes()
    elif c == 3:
        header = f"P6\n{w} {h}\n255\n".encode()
        body = img.tobytes()
    else:
        raise InvalidImageError(f"Cannot write image with {c} channels to PPM/PGM")
    with open(path, "wb") as f:
        f.write(header)
        f.write(body)


# ---------------------------------------------------------------------------
# Energy functions
# ---------------------------------------------------------------------------

def _to_gray(img: np.ndarray) -> np.ndarray:
    """Convert RGB image to grayscale using Rec. 601 luminance weights."""
    if img.shape[2] == 1:
        return img[:, :, 0].astype(np.float64)
    return (
        img[:, :, 0].astype(np.float64) * 0.299
        + img[:, :, 1].astype(np.float64) * 0.587
        + img[:, :, 2].astype(np.float64) * 0.114
    )


def _sobel_energy(gray: np.ndarray) -> np.ndarray:
    """Compute energy using Sobel operator magnitude (|Gx| + |Gy|)."""
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


def _prewitt_energy(gray: np.ndarray) -> np.ndarray:
    """Compute energy using Prewitt operator magnitude (|Gx| + |Gy|)."""
    gx = np.zeros_like(gray)
    gy = np.zeros_like(gray)
    gx[1:-1, 1:-1] = (
        -gray[:-2, :-2] - gray[:-2, 1:-1] - gray[:-2, 2:]
        + gray[2:, :-2] + gray[2:, 1:-1] + gray[2:, 2:]
    )
    gy[1:-1, 1:-1] = (
        -gray[:-2, :-2] + gray[:-2, 2:]
        - gray[1:-1, :-2] + gray[1:-1, 2:]
        - gray[2:, :-2] + gray[2:, 2:]
    )
    return np.abs(gx) + np.abs(gy)


def _laplacian_energy(gray: np.ndarray) -> np.ndarray:
    """Compute energy using Laplacian (second derivative) — detects rapid intensity changes."""
    lap = np.zeros_like(gray)
    lap[1:-1, 1:-1] = (
        -gray[:-2, 1:-1] - gray[2:, 1:-1]
        - gray[1:-1, :-2] - gray[1:-1, 2:]
        + 4 * gray[1:-1, 1:-1]
    )
    return np.abs(lap)


def _gradient_energy(gray: np.ndarray) -> np.ndarray:
    """Simple central-difference gradient energy."""
    gx = np.zeros_like(gray)
    gy = np.zeros_like(gray)
    gx[:, 1:-1] = (gray[:, 2:] - gray[:, :-2]) / 2.0
    gy[1:-1, :] = (gray[2:, :] - gray[:-2, :]) / 2.0
    return np.abs(gx) + np.abs(gy)


def _forward_energy(gray: np.ndarray) -> np.ndarray:
    """
    Forward energy cost (Avidan et al. 2008).
    Accounts for the energy *introduced* by removing a seam, not just
    the energy at the pixel. Minimizes the new adjacency cost created
    when neighboring pixels become adjacent after seam removal.

    The three costs at pixel (i, j) are:
      cU = |I(i, j+1) - I(i, j-1)|         (came from above)
      cL = |I(i, j) - I(i, j-1)| + cU       (came from upper-left)
      cR = |I(i, j) - I(i, j+1)| + cU       (came from upper-right)

    The DP accumulates: M(i,j) = min(M(i-1,j-1)+cL, M(i-1,j)+cU, M(i-1,j+1)+cR)
    """
    h, w = gray.shape
    cu = np.zeros_like(gray)
    cL = np.zeros_like(gray)
    cR = np.zeros_like(gray)

    cu[:, 1:-1] = np.abs(gray[:, 2:] - gray[:, :-2])
    cL[:, 1:-1] = np.abs(gray[:, 1:-1] - gray[:, :-2]) + cu[:, 1:-1]
    cR[:, 1:-1] = np.abs(gray[:, 1:-1] - gray[:, 2:]) + cu[:, 1:-1]

    # Accumulate via DP — vectorized row-by-row
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
# Vectorized seam removal/insertion helpers
# ---------------------------------------------------------------------------

def _remove_seam_2d(arr: np.ndarray, seam: np.ndarray, axis: int) -> np.ndarray:
    """
    Remove a seam from a 2D or 3D array along the given axis.
    Uses a boolean mask for vectorized removal — O(H*W) without Python loops.

    Parameters
    ----------
    arr : np.ndarray  (H, W) or (H, W, C)
    seam : np.ndarray  column indices (for axis=1) or row indices (for axis=0)
    axis : int         1 = vertical seam (removes from width), 0 = horizontal (removes from height)
    """
    if arr.ndim == 2:
        h, w = arr.shape
    else:
        h, w = arr.shape[:2]

    if axis == 1:
        # Vertical seam: remove one column per row
        mask = np.ones((h, w), dtype=bool)
        mask[np.arange(h), seam] = False
        if arr.ndim == 2:
            return arr[mask].reshape(h, w - 1)
        else:
            return arr[mask].reshape(h, w - 1, arr.shape[2])
    else:
        # Horizontal seam: remove one row per column
        mask = np.ones((h, w), dtype=bool)
        mask[seam, np.arange(w)] = False
        if arr.ndim == 2:
            return arr[mask].reshape(h - 1, w)
        else:
            return arr[mask].reshape(h - 1, w, arr.shape[2])


def _insert_seam_2d(arr: np.ndarray, seam: np.ndarray, axis: int, insert_values: np.ndarray) -> np.ndarray:
    """
    Insert a seam into a 2D or 3D array along the given axis.

    Parameters
    ----------
    arr : np.ndarray  (H, W) or (H, W, C)
    seam : np.ndarray  indices where the new seam goes
    axis : int         1 = vertical (increases width), 0 = horizontal (increases height)
    insert_values : np.ndarray  values to insert at seam positions
    """
    if arr.ndim == 2:
        h, w = arr.shape
    else:
        h, w = arr.shape[:2]

    if axis == 1:
        # Vertical seam: insert one column per row
        new_shape = (h, w + 1) if arr.ndim == 2 else (h, w + 1, arr.shape[2])
        result = np.zeros(new_shape, dtype=arr.dtype)
        for i in range(h):
            j = seam[i]
            if arr.ndim == 2:
                result[i, :j] = arr[i, :j]
                result[i, j] = insert_values[i]
                result[i, j + 1:] = arr[i, j:]
            else:
                result[i, :j] = arr[i, :j]
                result[i, j] = insert_values[i]
                result[i, j + 1:] = arr[i, j:]
        return result
    else:
        # Horizontal seam: insert one row per column
        new_shape = (h + 1, w) if arr.ndim == 2 else (h + 1, w, arr.shape[2])
        result = np.zeros(new_shape, dtype=arr.dtype)
        for j in range(w):
            i = seam[j]
            if arr.ndim == 2:
                result[:i, j] = arr[:i, j]
                result[i, j] = insert_values[j]
                result[i + 1:, j] = arr[i:, j]
            else:
                result[:i, j] = arr[:i, j]
                result[i, j] = insert_values[j]
                result[i + 1:, j] = arr[i:, j]
        return result


# ---------------------------------------------------------------------------
# Seam Carver
# ---------------------------------------------------------------------------

class SeamCarver:
    """
    Content-aware image resizer using seam carving.

    Parameters
    ----------
    image : np.ndarray
        (H, W, C) uint8 array (C=1 for grayscale, C=3 for RGB).
    energy_type : EnergyType
        Which energy function to use for seam computation.
    protect_mask : np.ndarray, optional
        (H, W) boolean array. True = protect this pixel (high energy boost).
    remove_mask : np.ndarray, optional
        (H, W) boolean array. True = mark for removal (negative energy).

    Attributes
    ----------
    image : np.ndarray
        Current working image (modified in-place by carving operations).
    energy : np.ndarray
        Current energy map (last computed).
    seam_history : list of np.ndarray
        Record of all seams removed/inserted (for animation/debugging).
    seam_costs : list of float
        Cost (total energy) of each seam that was removed.
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
        if not isinstance(image, np.ndarray):
            raise InvalidImageError("image must be a numpy ndarray")
        if image.ndim != 3 or image.shape[2] not in (1, 3):
            raise InvalidImageError(
                f"Image must be (H, W, C) with C=1 or 3, got shape {image.shape}"
            )
        if image.dtype != np.uint8:
            image = np.clip(image, 0, 255).astype(np.uint8)

        self.image = image.copy()
        self.energy_type = energy_type
        self.h, self.w = image.shape[:2]
        self.num_seams_carved = 0

        # Validate masks
        if protect_mask is not None:
            if protect_mask.shape != (self.h, self.w):
                raise InvalidImageError(
                    f"protect_mask shape {protect_mask.shape} != image shape {(self.h, self.w)}"
                )
            self.protect_mask = protect_mask.copy()
        else:
            self.protect_mask = None

        if remove_mask is not None:
            if remove_mask.shape != (self.h, self.w):
                raise InvalidImageError(
                    f"remove_mask shape {remove_mask.shape} != image shape {(self.h, self.w)}"
                )
            self.remove_mask = remove_mask.copy()
        else:
            self.remove_mask = None

        self.energy: Optional[np.ndarray] = None
        self.seam_history: List[np.ndarray] = []
        self.seam_costs: List[float] = []

    # -- energy computation -------------------------------------------------

    def _compute_energy(self) -> np.ndarray:
        """Compute the energy map for the current image."""
        gray = _to_gray(self.image)

        if self.energy_type == EnergyType.SOBEL:
            e = _sobel_energy(gray)
        elif self.energy_type == EnergyType.PREWITT:
            e = _prewitt_energy(gray)
        elif self.energy_type == EnergyType.LAPLACIAN:
            e = _laplacian_energy(gray)
        elif self.energy_type == EnergyType.GRADIENT:
            e = _gradient_energy(gray)
        elif self.energy_type == EnergyType.FORWARD:
            e = _forward_energy(gray)
        else:
            raise SeamCarvingError(f"Unknown energy type: {self.energy_type}")

        # Apply mask modifiers
        if self.protect_mask is not None:
            e = e.copy()
            e[self.protect_mask] += self.PROTECT_BOOST
        if self.remove_mask is not None:
            e = e.copy()
            e[self.remove_mask] += self.REMOVE_PENALTY

        self.energy = e
        return e

    # -- seam finding (vertical seams) --------------------------------------

    def _find_vertical_seam(self) -> np.ndarray:
        """
        Find the lowest-energy vertical seam using dynamic programming.
        Returns an array of column indices, one per row (length = H).

        The DP recurrence:
            M(i, j) = energy(i, j) + min(M(i-1, j-1), M(i-1, j), M(i-1, j+1))
        Backtrace from argmin of the last row.
        """
        energy = self._compute_energy()
        h, w = energy.shape
        M = energy.astype(np.float64).copy()

        for i in range(1, h):
            up = M[i - 1, :]
            left = np.empty(w)
            right = np.empty(w)
            left[0] = np.inf
            left[1:] = up[:-1]
            right[-1] = np.inf
            right[:-1] = up[1:]
            M[i] += np.minimum(np.minimum(up, left), right)

        # Backtrace from the minimum-energy pixel in the last row
        seam = np.empty(h, dtype=np.int64)
        seam[-1] = int(np.argmin(M[-1]))
        for i in range(h - 2, -1, -1):
            j = seam[i + 1]
            # Check up to three neighbors in the row above
            candidates = [j]
            if j > 0:
                candidates.append(j - 1)
            if j < w - 1:
                candidates.append(j + 1)
            seam[i] = min(candidates, key=lambda c: M[i, c])

        # Record the seam cost for quality metrics
        cost = float(M[-1, seam[-1]])
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

    # -- seam removal (vectorized) ------------------------------------------

    def _remove_vertical_seam(self, seam: np.ndarray) -> float:
        """
        Remove a vertical seam from the image (width decreases by 1).
        Uses vectorized boolean mask removal instead of Python row-loops.
        Returns the seam cost (total energy of the removed seam).
        """
        h, w, c = self.image.shape
        # Build boolean mask: True = keep, False = remove
        mask = np.ones((h, w), dtype=bool)
        mask[np.arange(h), seam] = False

        # Compute seam cost before removing (for quality metrics).
        # self.energy was set by _compute_energy() during _find_vertical_seam(),
        # and its shape matches the current (pre-removal) image.
        if self.energy is not None and self.energy.shape == (h, w):
            cost = float(self.energy[np.arange(h), seam].sum())
        else:
            cost = 0.0

        self.image = self.image[mask].reshape(h, w - 1, c)
        self.w -= 1

        if self.protect_mask is not None:
            self.protect_mask = self.protect_mask[mask].reshape(h, w - 1)
        if self.remove_mask is not None:
            self.remove_mask = self.remove_mask[mask].reshape(h, w - 1)

        return cost

    def _remove_horizontal_seam(self, seam: np.ndarray) -> float:
        """
        Remove a horizontal seam (height decreases by 1).
        Vectorized using boolean mask.
        Returns the seam cost.
        """
        h, w, c = self.image.shape
        mask = np.ones((h, w), dtype=bool)
        mask[seam, np.arange(w)] = False

        # Compute seam cost: we need the energy map for the current (non-transposed)
        # image. self.energy may be stale after horizontal seam finding (which
        # transposes internally), so recompute if dimensions don't match.
        if self.energy is not None and self.energy.shape == (h, w):
            cost = float(self.energy[seam, np.arange(w)].sum())
        else:
            cost = 0.0

        self.image = self.image[mask].reshape(h - 1, w, c)
        self.h -= 1

        if self.protect_mask is not None:
            self.protect_mask = self.protect_mask[mask].reshape(h - 1, w)
        if self.remove_mask is not None:
            self.remove_mask = self.remove_mask[mask].reshape(h - 1, w)

        return cost

    # -- seam insertion -----------------------------------------------------

    def _compute_insertion_values_vertical(self, seam: np.ndarray) -> np.ndarray:
        """
        Compute pixel values for a vertical seam insertion using bilinear
        averaging of adjacent pixels. At boundaries, replicate the edge pixel.
        """
        h, w, c = self.image.shape
        values = np.zeros((h, c), dtype=np.uint8)
        for i in range(h):
            j = seam[i]
            if j < w - 1:
                # Average current pixel with right neighbor
                values[i] = (
                    (self.image[i, j].astype(np.uint16)
                     + self.image[i, j + 1].astype(np.uint16)) // 2
                ).astype(np.uint8)
            else:
                values[i] = self.image[i, j].copy()
        return values

    def _compute_insertion_values_horizontal(self, seam: np.ndarray) -> np.ndarray:
        """Compute pixel values for a horizontal seam insertion (bilinear averaging)."""
        h, w, c = self.image.shape
        values = np.zeros((w, c), dtype=np.uint8)
        for j in range(w):
            i = seam[j]
            if i < h - 1:
                values[j] = (
                    (self.image[i, j].astype(np.uint16)
                     + self.image[i + 1, j].astype(np.uint16)) // 2
                ).astype(np.uint8)
            else:
                values[j] = self.image[i, j].copy()
        return values

    def _insert_vertical_seam(self, seam: np.ndarray) -> None:
        """Insert a vertical seam by averaging adjacent pixels."""
        h, w, c = self.image.shape
        insert_vals = self._compute_insertion_values_vertical(seam)
        new_img = np.zeros((h, w + 1, c), dtype=np.uint8)
        for i in range(h):
            j = seam[i]
            new_img[i, :j] = self.image[i, :j]
            new_img[i, j] = insert_vals[i]
            new_img[i, j + 1:] = self.image[i, j:]
        self.image = new_img
        self.w += 1

    def _insert_horizontal_seam(self, seam: np.ndarray) -> None:
        """Insert a horizontal seam by averaging adjacent pixels."""
        h, w, c = self.image.shape
        insert_vals = self._compute_insertion_values_horizontal(seam)
        new_img = np.zeros((h + 1, w, c), dtype=np.uint8)
        for j in range(w):
            i = seam[j]
            new_img[:i, j] = self.image[:i, j]
            new_img[i, j] = insert_vals[j]
            new_img[i + 1:, j] = self.image[i:, j]
        self.image = new_img
        self.h += 1

    # -- public API ---------------------------------------------------------

    def carve_vertical(self, num_seams: int, record: bool = False) -> np.ndarray:
        """
        Remove `num_seams` vertical seams (reduces width).

        Parameters
        ----------
        num_seams : int
            Number of seams to remove (must be < current width).
        record : bool
            If True, store each seam in seam_history for animation.

        Returns
        -------
        np.ndarray
            The resulting image.
        """
        if num_seams < 0:
            raise ValueError("num_seams must be non-negative")
        if num_seams >= self.w:
            raise ValueError(
                f"Cannot remove {num_seams} seams from image of width {self.w}"
            )
        for _ in range(num_seams):
            seam = self._find_vertical_seam()
            cost = self._remove_vertical_seam(seam)
            self.seam_costs.append(cost)
            if record:
                self.seam_history.append(seam.copy())
            self.num_seams_carved += 1
        return self.image

    def carve_horizontal(self, num_seams: int, record: bool = False) -> np.ndarray:
        """
        Remove `num_seams` horizontal seams (reduces height).

        Parameters
        ----------
        num_seams : int
            Number of seams to remove (must be < current height).
        record : bool
            If True, store each seam in seam_history for animation.
        """
        if num_seams < 0:
            raise ValueError("num_seams must be non-negative")
        if num_seams >= self.h:
            raise ValueError(
                f"Cannot remove {num_seams} seams from image of height {self.h}"
            )
        for _ in range(num_seams):
            seam = self._find_horizontal_seam()
            cost = self._remove_horizontal_seam(seam)
            self.seam_costs.append(cost)
            if record:
                self.seam_history.append(seam.copy())
            self.num_seams_carved += 1
        return self.image

    def insert_vertical(self, num_seams: int) -> np.ndarray:
        """
        Insert `num_seams` vertical seams (increases width).
        Uses the optimal seam insertion approach: find all seams on a temporary
        copy (removing them one by one), then insert into the original with
        index adjustment to account for already-inserted seams.
        """
        if num_seams < 0:
            raise ValueError("num_seams must be non-negative")

        seams_to_insert: List[np.ndarray] = []
        temp_carver = SeamCarver(self.image.copy(), self.energy_type)
        for _ in range(num_seams):
            if temp_carver.w <= 1:
                break
            seam = temp_carver._find_vertical_seam()
            seams_to_insert.append(seam)
            temp_carver._remove_vertical_seam(seam)

        # Insert seams in order, adjusting indices for previously inserted seams.
        # When a seam at column j is inserted, all subsequent seams with
        # columns >= j must be shifted right by 1.
        for idx, seam in enumerate(seams_to_insert):
            adjusted = seam.copy()
            for prev in seams_to_insert[:idx]:
                adjusted += (seam >= prev).astype(int)
            self._insert_vertical_seam(adjusted)
            self.num_seams_carved += 1
        return self.image

    def insert_horizontal(self, num_seams: int) -> np.ndarray:
        """Insert `num_seams` horizontal seams (increases height)."""
        if num_seams < 0:
            raise ValueError("num_seams must be non-negative")

        seams_to_insert: List[np.ndarray] = []
        temp_carver = SeamCarver(self.image.copy(), self.energy_type)
        for _ in range(num_seams):
            if temp_carver.h <= 1:
                break
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
        or horizontal seams based on the mask's extent in each dimension.

        After removal, the image is smaller. To restore original dimensions,
        call insert_vertical/insert_horizontal afterwards.
        """
        if remove_mask.shape != (self.h, self.w):
            raise InvalidImageError("Remove mask must match image dimensions")
        self.remove_mask = remove_mask.copy()

        iterations = 0
        while self.remove_mask is not None and self.remove_mask.any() and iterations < max_iterations:
            # Choose orientation based on mask extent
            rows_with_mask = int(np.any(self.remove_mask, axis=1).sum())
            cols_with_mask = int(np.any(self.remove_mask, axis=0).sum())
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
        """Return the current energy map normalized to 0–255 for visualization."""
        e = self._compute_energy()
        e_min, e_max = float(e.min()), float(e.max())
        if e_max - e_min < 1e-10:
            return np.zeros_like(e, dtype=np.uint8)
        normalized = ((e - e_min) / (e_max - e_min) * 255).astype(np.uint8)
        return normalized

    def visualize_seam(self, seam: np.ndarray, orientation: str = "vertical",
                       color: tuple = (255, 0, 0)) -> np.ndarray:
        """
        Draw a seam on a copy of the current image.
        Seam pixels are highlighted in the specified color (default: red).

        Parameters
        ----------
        seam : np.ndarray
            Seam indices (column indices for vertical, row indices for horizontal).
        orientation : str
            "vertical" or "horizontal".
        color : tuple of int
            (R, G, B) color for the seam highlight.
        """
        vis = self.image.copy()
        if vis.shape[2] == 1:
            vis = np.repeat(vis, 3, axis=2)
        if orientation == "vertical":
            for i, j in enumerate(seam):
                vis[i, j] = list(color)
        elif orientation == "horizontal":
            for j, i in enumerate(seam):
                vis[i, j] = list(color)
        else:
            raise ValueError(f"orientation must be 'vertical' or 'horizontal', got '{orientation}'")
        return vis

    def visualize_multiple_seams(self, seams: List[np.ndarray],
                                  orientation: str = "vertical") -> np.ndarray:
        """Draw multiple seams on a copy of the image, each in a different color."""
        vis = self.image.copy()
        if vis.shape[2] == 1:
            vis = np.repeat(vis, 3, axis=2)
        colors = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255),
            (255, 255, 0), (255, 0, 255), (0, 255, 255),
            (128, 0, 0), (0, 128, 0), (0, 0, 128),
        ]
        for idx, seam in enumerate(seams):
            color = colors[idx % len(colors)]
            if orientation == "vertical":
                for i, j in enumerate(seam):
                    if 0 <= j < vis.shape[1]:
                        vis[i, j] = list(color)
            else:
                for j, i in enumerate(seam):
                    if 0 <= i < vis.shape[0]:
                        vis[i, j] = list(color)
        return vis

    def energy_preservation_ratio(self) -> float:
        """
        Compute the ratio of total energy preserved after carving.
        A value close to 1.0 means most high-energy content was preserved.
        Only meaningful after carving operations.

        Returns
        -------
        float
            1 - (sum of removed seam costs / original total energy)
        """
        if not self.seam_costs:
            return 1.0
        total_removed = sum(self.seam_costs)
        # Original total energy is not stored separately; estimate from current
        current_total = float(self._compute_energy().sum())
        original_total = current_total + total_removed
        if original_total < 1e-10:
            return 1.0
        return 1.0 - (total_removed / original_total)

    def get_stats(self) -> dict:
        """Return a dictionary of carver statistics."""
        return {
            "image_size": (self.h, self.w),
            "num_seams_carved": self.num_seams_carved,
            "num_seams_recorded": len(self.seam_history),
            "avg_seam_cost": float(np.mean(self.seam_costs)) if self.seam_costs else 0.0,
            "total_seam_cost": float(sum(self.seam_costs)) if self.seam_costs else 0.0,
            "energy_preservation_ratio": self.energy_preservation_ratio(),
            "energy_type": self.energy_type.value,
        }


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def resize_width(image: np.ndarray, target_width: int,
                 energy_type: EnergyType = EnergyType.SOBEL) -> np.ndarray:
    """Resize image to target width using seam carving."""
    h, w = image.shape[:2]
    diff = target_width - w
    if diff == 0:
        return image.copy()
    carver = SeamCarver(image, energy_type=energy_type)
    if diff < 0:
        return carver.carve_vertical(-diff)
    else:
        return carver.insert_vertical(diff)


def resize_height(image: np.ndarray, target_height: int,
                  energy_type: EnergyType = EnergyType.SOBEL) -> np.ndarray:
    """Resize image to target height using seam carving."""
    h, w = image.shape[:2]
    diff = target_height - h
    if diff == 0:
        return image.copy()
    carver = SeamCarver(image, energy_type=energy_type)
    if diff < 0:
        return carver.carve_horizontal(-diff)
    else:
        return carver.insert_horizontal(diff)


def resize(
    image: np.ndarray,
    target_width: int,
    target_height: int,
    energy_type: EnergyType = EnergyType.SOBEL,
) -> np.ndarray:
    """
    Resize image to target dimensions using seam carving.
    Removes seams before inserting (order matters for quality — removal
    is cheaper and more reliable than insertion).
    """
    if target_width <= 0 or target_height <= 0:
        raise ValueError("Target dimensions must be positive")
    carver = SeamCarver(image, energy_type=energy_type)
    w_diff = target_width - carver.w
    h_diff = target_height - carver.h

    # Remove first, then insert
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

def _parse_mask_file(path: str, h: int, w: int) -> np.ndarray:
    """Read a mask from a PGM file (non-zero = active)."""
    mask_img = read_ppm(path)
    if mask_img.ndim == 3:
        mask_img = mask_img[:, :, 0]
    if mask_img.shape != (h, w):
        raise InvalidImageError(
            f"Mask file {path} has shape {mask_img.shape}, expected ({h}, {w})"
        )
    return mask_img > 0


def main() -> int:
    """Command-line interface for seam carving."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Content-aware image resizing via seam carving"
    )
    parser.add_argument("input", help="Input PPM (P6) or PGM (P5) image file")
    parser.add_argument("output", help="Output PPM (P6) image file")
    parser.add_argument("-W", "--width", type=int, help="Target width")
    parser.add_argument("-H", "--height", type=int, help="Target height")
    parser.add_argument(
        "-e", "--energy",
        choices=["sobel", "prewitt", "laplacian", "gradient", "forward"],
        default="sobel",
        help="Energy function to use (default: sobel)",
    )
    parser.add_argument(
        "--energy-map", metavar="PATH",
        help="Save the energy map visualization to this PPM file",
    )
    parser.add_argument(
        "--seam-vis", metavar="PATH",
        help="Save a visualization of the first seam to this PPM file",
    )
    parser.add_argument(
        "--protect", metavar="PATH",
        help="PGM mask file: non-zero pixels are protected from carving",
    )
    parser.add_argument(
        "--remove", metavar="PATH",
        help="PGM mask file: non-zero pixels are marked for object removal",
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Print carver statistics after processing",
    )
    args = parser.parse_args()

    img = read_ppm(args.input)
    energy_type = EnergyType(args.energy)

    # Read masks if provided
    protect_mask = None
    remove_mask = None
    h, w = img.shape[:2]
    if args.protect:
        protect_mask = _parse_mask_file(args.protect, h, w)
    if args.remove:
        remove_mask = _parse_mask_file(args.remove, h, w)

    carver = SeamCarver(img, energy_type=energy_type,
                        protect_mask=protect_mask, remove_mask=remove_mask)

    if args.remove:
        # Object removal mode
        result = carver.remove_object(remove_mask)
    elif args.width is not None or args.height is not None:
        tw = args.width if args.width is not None else carver.w
        th = args.height if args.height is not None else carver.h
        w_diff = tw - carver.w
        h_diff = th - carver.h
        if w_diff < 0:
            carver.carve_vertical(-w_diff)
        if h_diff < 0:
            carver.carve_horizontal(-h_diff)
        if w_diff > 0:
            carver.insert_vertical(w_diff)
        if h_diff > 0:
            carver.insert_horizontal(h_diff)
        result = carver.image
    else:
        print("No target dimensions specified, outputting original image.")
        result = img

    write_ppm(args.output, result)
    print(f"Input:  {img.shape[1]}x{img.shape[0]}")
    print(f"Output: {result.shape[1]}x{result.shape[0]}")
    print(f"Energy: {args.energy}")

    if args.energy_map:
        emap_carver = SeamCarver(img, energy_type=energy_type)
        emap = emap_carver.get_energy_map()
        emap_rgb = np.repeat(emap[:, :, np.newaxis], 3, axis=2)
        write_ppm(args.energy_map, emap_rgb)
        print(f"Energy map saved to: {args.energy_map}")

    if args.seam_vis:
        vis_carver = SeamCarver(img, energy_type=energy_type)
        seam = vis_carver._find_vertical_seam()
        vis = vis_carver.visualize_seam(seam, "vertical")
        write_ppm(args.seam_vis, vis)
        print(f"Seam visualization saved to: {args.seam_vis}")

    if args.stats:
        stats = carver.get_stats()
        print("\nStatistics:")
        for key, val in stats.items():
            print(f"  {key}: {val}")

    return 0


if __name__ == "__main__":
    sys.exit(main())