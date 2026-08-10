"""
seamcarving/carver.py — Core seam carving algorithm.

Implements content-aware image resizing via seam carving
(Avidan & Shamir, 2007) with multiple energy functions, seam
removal/insertion, object removal, region protection, animation
frame export, and quality metrics.

The main class is :class:`SeamCarver`.
"""

from __future__ import annotations

import os
from typing import List, Optional, Dict, Any

import numpy as np

from .energy import EnergyType, compute_energy, to_gray
from .exceptions import (
    SeamCarvingError, InvalidImageError, SeamOperationError,
)
from .io import write_image
from .logging import get_logger

logger = get_logger("seamcarving", configure=False)


# ---------------------------------------------------------------------------
# Vectorised seam removal / insertion helpers
# ---------------------------------------------------------------------------

def _remove_seam_2d(arr: np.ndarray, seam: np.ndarray, axis: int) -> np.ndarray:
    """Remove a seam from a 2D or 3D array along the given axis.

    Uses a boolean mask for vectorised removal — O(H*W) without Python loops.

    Parameters
    ----------
    arr : np.ndarray
        ``(H, W)`` or ``(H, W, C)``.
    seam : np.ndarray
        Column indices (axis=1) or row indices (axis=0).
    axis : int
        ``1`` = vertical seam, ``0`` = horizontal seam.
    """
    if arr.ndim == 2:
        h, w = arr.shape
    else:
        h, w = arr.shape[:2]

    if axis == 1:
        mask = np.ones((h, w), dtype=bool)
        mask[np.arange(h), seam] = False
        if arr.ndim == 2:
            return arr[mask].reshape(h, w - 1)
        return arr[mask].reshape(h, w - 1, arr.shape[2])
    else:
        mask = np.ones((h, w), dtype=bool)
        mask[seam, np.arange(w)] = False
        if arr.ndim == 2:
            return arr[mask].reshape(h - 1, w)
        return arr[mask].reshape(h - 1, w, arr.shape[2])


def _insert_seam_2d(
    arr: np.ndarray,
    seam: np.ndarray,
    axis: int,
    insert_values: np.ndarray,
) -> np.ndarray:
    """Insert a seam into a 2D or 3D array along the given axis."""
    if arr.ndim == 2:
        h, w = arr.shape
    else:
        h, w = arr.shape[:2]

    if axis == 1:
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
    """Content-aware image resizer using seam carving.

    Parameters
    ----------
    image : np.ndarray
        ``(H, W, C)`` ``uint8`` array (C=1 for grayscale, C=3 for RGB).
    energy_type : EnergyType
        Which energy function to use for seam computation.
    protect_mask : np.ndarray, optional
        ``(H, W)`` boolean array. ``True`` = protect this pixel (high energy boost).
    remove_mask : np.ndarray, optional
        ``(H, W)`` boolean array. ``True`` = mark for removal (negative energy).

    Attributes
    ----------
    image : np.ndarray
        Current working image (modified in-place by carving operations).
    energy : Optional[np.ndarray]
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

        logger.debug(
            "SeamCarver initialised: %dx%d, energy=%s, protect=%s, remove=%s",
            self.h, self.w, energy_type.value,
            protect_mask is not None, remove_mask is not None,
        )

    # -- energy computation -------------------------------------------------

    def _compute_energy(self) -> np.ndarray:
        """Compute the energy map for the current image."""
        gray = to_gray(self.image)
        e = compute_energy(gray, self.energy_type)

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
        """Find the lowest-energy vertical seam using dynamic programming.

        Returns an array of column indices, one per row (length = H).

        The DP recurrence::

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
            candidates = [j]
            if j > 0:
                candidates.append(j - 1)
            if j < w - 1:
                candidates.append(j + 1)
            seam[i] = min(candidates, key=lambda c: M[i, c])

        return seam

    def _find_horizontal_seam(self) -> np.ndarray:
        """Find the lowest-energy horizontal seam (transpose, find vertical).

        Note: We transpose the image and masks, call ``_find_vertical_seam``
        (which sets ``self.energy`` on the transposed image), then transpose
        everything back.  After transposing back, ``self.energy`` is stale
        (it has the transposed shape), so we clear it to prevent dimension
        mismatches in subsequent operations.
        """
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
        # Clear stale energy map
        self.energy = None
        return seam

    # -- seam removal (vectorised) ------------------------------------------

    def _remove_vertical_seam(self, seam: np.ndarray) -> float:
        """Remove a vertical seam from the image (width decreases by 1).

        Uses vectorised boolean mask removal instead of Python row-loops.
        Returns the seam cost (total energy of the removed seam).
        """
        h, w, c = self.image.shape
        mask = np.ones((h, w), dtype=bool)
        mask[np.arange(h), seam] = False

        # Compute seam cost before removing
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
        """Remove a horizontal seam (height decreases by 1).

        Vectorised using boolean mask.  Returns the seam cost.
        """
        h, w, c = self.image.shape
        mask = np.ones((h, w), dtype=bool)
        mask[seam, np.arange(w)] = False

        # Recompute energy if needed for accurate cost tracking
        if self.energy is None or self.energy.shape != (h, w):
            energy = self._compute_energy()
        else:
            energy = self.energy
        cost = float(energy[seam, np.arange(w)].sum())

        self.image = self.image[mask].reshape(h - 1, w, c)
        self.h -= 1

        if self.protect_mask is not None:
            self.protect_mask = self.protect_mask[mask].reshape(h - 1, w)
        if self.remove_mask is not None:
            self.remove_mask = self.remove_mask[mask].reshape(h - 1, w)

        return cost

    # -- seam insertion -----------------------------------------------------

    def _compute_insertion_values_vertical(self, seam: np.ndarray) -> np.ndarray:
        """Compute pixel values for a vertical seam insertion (bilinear avg)."""
        h, w, c = self.image.shape
        values = np.zeros((h, c), dtype=np.uint8)
        for i in range(h):
            j = seam[i]
            if j < w - 1:
                values[i] = (
                    (self.image[i, j].astype(np.uint16)
                     + self.image[i, j + 1].astype(np.uint16)) // 2
                ).astype(np.uint8)
            else:
                values[i] = self.image[i, j].copy()
        return values

    def _compute_insertion_values_horizontal(self, seam: np.ndarray) -> np.ndarray:
        """Compute pixel values for a horizontal seam insertion (bilinear avg)."""
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

    # -- animation frame export ---------------------------------------------

    def _export_frame(
        self,
        seam: np.ndarray,
        orientation: str,
        frame_num: int,
        output_dir: str,
        fmt: str = "png",
    ) -> str:
        """Export a single animation frame with the seam highlighted."""
        os.makedirs(output_dir, exist_ok=True)
        vis = self.visualize_seam(seam, orientation, color=(255, 0, 0))
        ext = fmt if fmt != "ppm" else "ppm"
        fname = f"frame_{frame_num:05d}.{ext}"
        fpath = os.path.join(output_dir, fname)
        write_image(fpath, vis)
        return fpath

    # -- public API ---------------------------------------------------------

    def carve_vertical(
        self,
        num_seams: int,
        record: bool = False,
        animation_dir: Optional[str] = None,
        animation_format: str = "png",
    ) -> np.ndarray:
        """Remove ``num_seams`` vertical seams (reduces width).

        Parameters
        ----------
        num_seams : int
            Number of seams to remove (must be < current width).
        record : bool
            If True, store each seam in ``seam_history`` for animation.
        animation_dir : str, optional
            If provided, export animation frames to this directory.
        animation_format : str
            Format for animation frames (``png`` or ``ppm``).

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
        for i in range(num_seams):
            seam = self._find_vertical_seam()
            if animation_dir:
                self._export_frame(
                    seam, "vertical", i, animation_dir, animation_format
                )
            cost = self._remove_vertical_seam(seam)
            self.seam_costs.append(cost)
            if record:
                self.seam_history.append(seam.copy())
            self.num_seams_carved += 1
            logger.debug("Carved vertical seam %d/%d, cost=%.2f", i + 1, num_seams, cost)
        return self.image

    def carve_horizontal(
        self,
        num_seams: int,
        record: bool = False,
        animation_dir: Optional[str] = None,
        animation_format: str = "png",
    ) -> np.ndarray:
        """Remove ``num_seams`` horizontal seams (reduces height).

        Parameters
        ----------
        num_seams : int
            Number of seams to remove (must be < current height).
        record : bool
            If True, store each seam in ``seam_history`` for animation.
        animation_dir : str, optional
            If provided, export animation frames to this directory.
        animation_format : str
            Format for animation frames (``png`` or ``ppm``).

        Returns
        -------
        np.ndarray
            The resulting image.
        """
        if num_seams < 0:
            raise ValueError("num_seams must be non-negative")
        if num_seams >= self.h:
            raise ValueError(
                f"Cannot remove {num_seams} seams from image of height {self.h}"
            )
        for i in range(num_seams):
            seam = self._find_horizontal_seam()
            if animation_dir:
                self._export_frame(
                    seam, "horizontal", i, animation_dir, animation_format
                )
            cost = self._remove_horizontal_seam(seam)
            self.seam_costs.append(cost)
            if record:
                self.seam_history.append(seam.copy())
            self.num_seams_carved += 1
            logger.debug("Carved horizontal seam %d/%d, cost=%.2f", i + 1, num_seams, cost)
        return self.image

    def insert_vertical(self, num_seams: int) -> np.ndarray:
        """Insert ``num_seams`` vertical seams (increases width).

        Uses the optimal seam insertion approach: find all seams on a
        temporary copy (removing them one by one), then insert into the
        original with index adjustment for already-inserted seams.
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

        # Insert seams in order, adjusting indices for previously inserted seams
        for idx, seam in enumerate(seams_to_insert):
            adjusted = seam.copy()
            for prev in seams_to_insert[:idx]:
                adjusted += (seam >= prev).astype(int)
            self._insert_vertical_seam(adjusted)
            self.num_seams_carved += 1
        return self.image

    def insert_horizontal(self, num_seams: int) -> np.ndarray:
        """Insert ``num_seams`` horizontal seams (increases height)."""
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

    def remove_object(
        self, remove_mask: np.ndarray, max_iterations: int = 500
    ) -> np.ndarray:
        """Remove an object specified by ``remove_mask`` (boolean H×W array).

        Removes seams until all marked pixels are gone, choosing vertical
        or horizontal seams based on the mask's extent in each dimension.
        After removal, the image is smaller.  To restore original dimensions,
        call ``insert_vertical`` / ``insert_horizontal`` afterwards.
        """
        if remove_mask.shape != (self.h, self.w):
            raise InvalidImageError("Remove mask must match image dimensions")
        self.remove_mask = remove_mask.copy()

        iterations = 0
        while self.remove_mask is not None and self.remove_mask.any() and iterations < max_iterations:
            rows_with_mask = int(np.any(self.remove_mask, axis=1).sum())
            cols_with_mask = int(np.any(self.remove_mask, axis=0).sum())
            if cols_with_mask >= rows_with_mask:
                seam = self._find_vertical_seam()
                cost = self._remove_vertical_seam(seam)
            else:
                seam = self._find_horizontal_seam()
                cost = self._remove_horizontal_seam(seam)
            self.seam_costs.append(cost)
            self.num_seams_carved += 1
            iterations += 1
            logger.debug("Object removal iteration %d, cost=%.2f", iterations, cost)

        self.remove_mask = None
        return self.image

    def get_energy_map(self) -> np.ndarray:
        """Return the current energy map normalised to 0–255 for visualization."""
        e = self._compute_energy()
        e_min, e_max = float(e.min()), float(e.max())
        if e_max - e_min < 1e-10:
            return np.zeros_like(e, dtype=np.uint8)
        normalized = ((e - e_min) / (e_max - e_min) * 255).astype(np.uint8)
        return normalized

    def visualize_seam(
        self,
        seam: np.ndarray,
        orientation: str = "vertical",
        color: tuple = (255, 0, 0),
    ) -> np.ndarray:
        """Draw a seam on a copy of the current image.

        Seam pixels are highlighted in the specified color (default: red).

        Parameters
        ----------
        seam : np.ndarray
            Seam indices (column indices for vertical, row indices for horizontal).
        orientation : str
            ``"vertical"`` or ``"horizontal"``.
        color : tuple of int
            ``(R, G, B)`` color for the seam highlight.
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
            raise ValueError(
                f"orientation must be 'vertical' or 'horizontal', got '{orientation}'"
            )
        return vis

    def visualize_multiple_seams(
        self,
        seams: List[np.ndarray],
        orientation: str = "vertical",
    ) -> np.ndarray:
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
        """Compute the ratio of total energy preserved after carving.

        A value close to 1.0 means most high-energy content was preserved.
        Only meaningful after carving operations.
        """
        if not self.seam_costs:
            return 1.0
        total_removed = sum(self.seam_costs)
        current_total = float(self._compute_energy().sum())
        original_total = current_total + total_removed
        if original_total < 1e-10:
            return 1.0
        return 1.0 - (total_removed / original_total)

    def get_stats(self) -> Dict[str, Any]:
        """Return a dictionary of carver statistics."""
        return {
            "image_size": (self.h, self.w),
            "num_seams_carved": self.num_seams_carved,
            "num_seams_recorded": len(self.seam_history),
            "avg_seam_cost": float(np.mean(self.seam_costs)) if self.seam_costs else 0.0,
            "total_seam_cost": float(sum(self.seam_costs)) if self.seam_costs else 0.0,
            "min_seam_cost": float(np.min(self.seam_costs)) if self.seam_costs else 0.0,
            "max_seam_cost": float(np.max(self.seam_costs)) if self.seam_costs else 0.0,
            "energy_preservation_ratio": self.energy_preservation_ratio(),
            "energy_type": self.energy_type.value,
        }


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def resize_width(
    image: np.ndarray,
    target_width: int,
    energy_type: EnergyType = EnergyType.SOBEL,
) -> np.ndarray:
    """Resize image to target width using seam carving.

    Raises ``ValueError`` if ``target_width <= 0``.
    """
    if target_width <= 0:
        raise ValueError(f"target_width must be positive, got {target_width}")
    h, w = image.shape[:2]
    diff = target_width - w
    if diff == 0:
        return image.copy()
    carver = SeamCarver(image, energy_type=energy_type)
    if diff < 0:
        return carver.carve_vertical(-diff)
    return carver.insert_vertical(diff)


def resize_height(
    image: np.ndarray,
    target_height: int,
    energy_type: EnergyType = EnergyType.SOBEL,
) -> np.ndarray:
    """Resize image to target height using seam carving.

    Raises ``ValueError`` if ``target_height <= 0``.
    """
    if target_height <= 0:
        raise ValueError(f"target_height must be positive, got {target_height}")
    h, w = image.shape[:2]
    diff = target_height - h
    if diff == 0:
        return image.copy()
    carver = SeamCarver(image, energy_type=energy_type)
    if diff < 0:
        return carver.carve_horizontal(-diff)
    return carver.insert_horizontal(diff)


def resize(
    image: np.ndarray,
    target_width: int,
    target_height: int,
    energy_type: EnergyType = EnergyType.SOBEL,
) -> np.ndarray:
    """Resize image to target dimensions using seam carving.

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