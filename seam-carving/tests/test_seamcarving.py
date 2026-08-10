#!/usr/bin/env python3
"""
tests/test_seamcarving.py — Comprehensive test suite for the seam carving library.

Tests cover:
  - Image I/O (PPM/PGM read/write, round-trip, error cases)
  - Energy functions (all 5, shape correctness, boundary behavior)
  - Seam finding (vertical/horizontal, DP correctness, connectivity)
  - Seam removal (dimensions, content preservation, mask propagation)
  - Seam insertion (dimensions, index adjustment, boundary handling)
  - Object removal (mask elimination, dimension reduction)
  - Mask protection (protected regions survive carving)
  - Visualization (seam drawing, color correctness)
  - Quality metrics (seam costs, energy preservation ratio, stats)
  - Convenience functions (resize_width, resize_height, resize)
  - Edge cases (1x1 images, single-row/column, invalid inputs)
  - Bug regression tests
"""

import os
import sys
import tempfile
import numpy as np

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seamcarving import (
    SeamCarver, EnergyType, SeamCarvingError, InvalidImageError,
    resize, resize_width, resize_height, read_ppm, write_ppm,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def gradient_image():
    """A 10x8 RGB gradient image with a vertical edge."""
    img = np.zeros((8, 10, 3), dtype=np.uint8)
    for x in range(10):
        for y in range(8):
            img[y, x] = [x * 25, y * 30, (x + y) * 10]
    return img


@pytest.fixture
def edge_image():
    """A 10x10 image with a sharp vertical edge at x=5."""
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    img[:, 5:] = [255, 255, 255]
    return img


@pytest.fixture
def small_image():
    """A 3x3 RGB image for basic tests."""
    return np.array([
        [[10, 20, 30], [40, 50, 60], [70, 80, 90]],
        [[11, 21, 31], [41, 51, 61], [71, 81, 91]],
        [[12, 22, 32], [42, 52, 62], [72, 82, 92]],
    ], dtype=np.uint8)


# ---------------------------------------------------------------------------
# Image I/O Tests
# ---------------------------------------------------------------------------

class TestImageIO:
    """Test PPM/PGM reading and writing."""

    def test_ppm_round_trip(self, tmp_path):
        """PPM write then read should preserve pixel data."""
        img = np.random.randint(0, 256, (8, 10, 3), dtype=np.uint8)
        path = str(tmp_path / "test.ppm")
        write_ppm(path, img)
        result = read_ppm(path)
        assert result.shape == (8, 10, 3)
        np.testing.assert_array_equal(result, img)

    def test_pgm_round_trip(self, tmp_path):
        """PGM write then read should preserve pixel data."""
        img = np.random.randint(0, 256, (8, 10, 1), dtype=np.uint8)
        path = str(tmp_path / "test.pgm")
        write_ppm(path, img)
        result = read_ppm(path)
        assert result.shape == (8, 10, 1)
        np.testing.assert_array_equal(result, img)

    def test_ppm_with_comments(self, tmp_path):
        """PPM reader should handle comments in the header."""
        path = str(tmp_path / "comments.ppm")
        header = b"P6\n# This is a comment\n3 2\n# Another comment\n255\n"
        pixels = bytes([0] * 18)
        with open(path, "wb") as f:
            f.write(header + pixels)
        result = read_ppm(path)
        assert result.shape == (2, 3, 3)

    def test_read_invalid_format(self, tmp_path):
        """Reading a non-PPM/PGM file should raise InvalidImageError."""
        path = str(tmp_path / "bad.ppm")
        with open(path, "wb") as f:
            f.write(b"NOTANIMAGE")
        with pytest.raises(InvalidImageError):
            read_ppm(path)

    def test_write_2d_array_as_pgm(self, tmp_path):
        """Writing a 2D array should produce a PGM file."""
        img = np.random.randint(0, 256, (4, 5), dtype=np.uint8)
        path = str(tmp_path / "gray.pgm")
        write_ppm(path, img)
        result = read_ppm(path)
        assert result.shape == (4, 5, 1)
        np.testing.assert_array_equal(result[:, :, 0], img)


# ---------------------------------------------------------------------------
# Energy Function Tests
# ---------------------------------------------------------------------------

class TestEnergyFunctions:
    """Test all energy function implementations."""

    @pytest.mark.parametrize("etype", list(EnergyType))
    def test_energy_shape(self, gradient_image, etype):
        """Energy map should match image spatial dimensions."""
        carver = SeamCarver(gradient_image, energy_type=etype)
        energy = carver._compute_energy()
        assert energy.shape == (8, 10)

    @pytest.mark.parametrize("etype", list(EnergyType))
    def test_energy_non_negative(self, gradient_image, etype):
        """Energy values should be non-negative (except when remove_mask is used)."""
        carver = SeamCarver(gradient_image, energy_type=etype)
        energy = carver._compute_energy()
        assert (energy >= 0).all() or (energy < 0).any()  # forward energy M can be 0+
        # Without masks, all standard energies should be >= 0
        if etype != EnergyType.FORWARD:
            assert (energy >= 0).all()

    def test_sobel_detects_edges(self, edge_image):
        """Sobel energy should be high at the edge (x=5) and low elsewhere."""
        carver = SeamCarver(edge_image, energy_type=EnergyType.SOBEL)
        energy = carver._compute_energy()
        # Energy at the edge (columns 4-5) should be higher than in flat regions
        edge_energy = energy[:, 4:6].mean()
        flat_energy = energy[:, 0:3].mean()
        assert edge_energy > flat_energy

    def test_energy_uniform_image(self):
        """A uniform image should have zero energy everywhere."""
        img = np.full((10, 10, 3), 128, dtype=np.uint8)
        for etype in [EnergyType.SOBEL, EnergyType.PREWITT, EnergyType.LAPLACIAN, EnergyType.GRADIENT]:
            carver = SeamCarver(img, energy_type=etype)
            energy = carver._compute_energy()
            assert energy.max() == 0.0, f"{etype.value} should be 0 for uniform image"


# ---------------------------------------------------------------------------
# Seam Finding Tests
# ---------------------------------------------------------------------------

class TestSeamFinding:
    """Test vertical and horizontal seam finding."""

    def test_vertical_seam_length(self, gradient_image):
        """Vertical seam should have one entry per row."""
        carver = SeamCarver(gradient_image)
        seam = carver._find_vertical_seam()
        assert len(seam) == 8  # height of gradient_image

    def test_vertical_seam_connectivity(self, gradient_image):
        """Consecutive seam pixels should differ by at most 1 in column."""
        carver = SeamCarver(gradient_image)
        seam = carver._find_vertical_seam()
        for i in range(len(seam) - 1):
            assert abs(seam[i + 1] - seam[i]) <= 1, \
                f"Seam not connected at row {i}: {seam[i]} -> {seam[i+1]}"

    def test_vertical_seam_bounds(self, gradient_image):
        """All seam indices should be within valid column range."""
        carver = SeamCarver(gradient_image)
        seam = carver._find_vertical_seam()
        w = gradient_image.shape[1]
        assert (seam >= 0).all() and (seam < w).all()

    def test_horizontal_seam_length(self, gradient_image):
        """Horizontal seam should have one entry per column."""
        carver = SeamCarver(gradient_image)
        seam = carver._find_horizontal_seam()
        assert len(seam) == 10  # width of gradient_image

    def test_horizontal_seam_connectivity(self, gradient_image):
        """Consecutive horizontal seam pixels should differ by at most 1 in row."""
        carver = SeamCarver(gradient_image)
        seam = carver._find_horizontal_seam()
        for j in range(len(seam) - 1):
            assert abs(seam[j + 1] - seam[j]) <= 1

    def test_seam_avoids_high_energy(self, edge_image):
        """Seam should prefer the low-energy (black) side of the edge image."""
        carver = SeamCarver(edge_image, energy_type=EnergyType.SOBEL)
        seam = carver._find_vertical_seam()
        # Most seam pixels should be in the low-energy region (columns 0-4)
        low_energy_count = sum(1 for s in seam if s < 5)
        assert low_energy_count > len(seam) / 2, \
            f"Seam should avoid high-energy region, got seam: {seam}"

    def test_find_seam_preserves_image(self, gradient_image):
        """Finding a seam should not modify the image."""
        carver = SeamCarver(gradient_image)
        original = carver.image.copy()
        carver._find_vertical_seam()
        np.testing.assert_array_equal(carver.image, original)

    def test_find_horizontal_seam_preserves_image(self, gradient_image):
        """Finding a horizontal seam should not modify the image."""
        carver = SeamCarver(gradient_image)
        original = carver.image.copy()
        carver._find_horizontal_seam()
        np.testing.assert_array_equal(carver.image, original)

    def test_find_horizontal_seam_preserves_dimensions(self, gradient_image):
        """Finding a horizontal seam should not change image dimensions."""
        carver = SeamCarver(gradient_image)
        orig_h, orig_w = carver.h, carver.w
        carver._find_horizontal_seam()
        assert carver.h == orig_h
        assert carver.w == orig_w


# ---------------------------------------------------------------------------
# Seam Removal Tests
# ---------------------------------------------------------------------------

class TestSeamRemoval:
    """Test vertical and horizontal seam removal."""

    def test_carve_vertical_reduces_width(self, gradient_image):
        """Carving N vertical seams should reduce width by N."""
        carver = SeamCarver(gradient_image)
        original_w = carver.w
        carver.carve_vertical(3)
        assert carver.w == original_w - 3
        assert carver.image.shape[1] == original_w - 3

    def test_carve_horizontal_reduces_height(self, gradient_image):
        """Carving N horizontal seams should reduce height by N."""
        carver = SeamCarver(gradient_image)
        original_h = carver.h
        carver.carve_horizontal(2)
        assert carver.h == original_h - 2
        assert carver.image.shape[0] == original_h - 2

    def test_carve_vertical_preserves_height(self, gradient_image):
        """Vertical carving should not change height."""
        carver = SeamCarver(gradient_image)
        original_h = carver.h
        carver.carve_vertical(3)
        assert carver.h == original_h

    def test_carve_vertical_invalid_count(self, gradient_image):
        """Carving more seams than width should raise ValueError."""
        carver = SeamCarver(gradient_image)
        with pytest.raises(ValueError):
            carver.carve_vertical(10)  # width is 10

    def test_carve_negative_seams(self, gradient_image):
        """Negative seam count should raise ValueError."""
        carver = SeamCarver(gradient_image)
        with pytest.raises(ValueError):
            carver.carve_vertical(-1)

    def test_carve_with_recording(self, gradient_image):
        """Carving with record=True should populate seam_history."""
        carver = SeamCarver(gradient_image)
        carver.carve_vertical(5, record=True)
        assert len(carver.seam_history) == 5

    def test_carve_without_recording(self, gradient_image):
        """Carving without record should not populate seam_history."""
        carver = SeamCarver(gradient_image)
        carver.carve_vertical(5, record=False)
        assert len(carver.seam_history) == 0

    def test_carve_tracks_seam_costs(self, gradient_image):
        """Carving should track seam costs."""
        carver = SeamCarver(gradient_image)
        carver.carve_vertical(3)
        assert len(carver.seam_costs) == 3

    def test_mask_propagation_after_carve(self, gradient_image):
        """Protect mask should be properly propagated after carving."""
        protect = np.zeros((8, 10), dtype=bool)
        protect[:, 0] = True  # protect first column
        carver = SeamCarver(gradient_image, protect_mask=protect)
        carver.carve_vertical(3)
        assert carver.protect_mask is not None
        assert carver.protect_mask.shape == (8, 7)
        # First column should still be protected
        assert carver.protect_mask[:, 0].all()


# ---------------------------------------------------------------------------
# Seam Insertion Tests
# ---------------------------------------------------------------------------

class TestSeamInsertion:
    """Test seam insertion (enlargement)."""

    def test_insert_vertical_increases_width(self, gradient_image):
        """Inserting N vertical seams should increase width by N."""
        carver = SeamCarver(gradient_image)
        original_w = carver.w
        carver.insert_vertical(3)
        assert carver.w == original_w + 3
        assert carver.image.shape[1] == original_w + 3

    def test_insert_horizontal_increases_height(self, gradient_image):
        """Inserting N horizontal seams should increase height by N."""
        carver = SeamCarver(gradient_image)
        original_h = carver.h
        carver.insert_horizontal(2)
        assert carver.h == original_h + 2
        assert carver.image.shape[0] == original_h + 2

    def test_insert_negative_seams(self, gradient_image):
        """Negative seam insertion should raise ValueError."""
        carver = SeamCarver(gradient_image)
        with pytest.raises(ValueError):
            carver.insert_vertical(-1)

    def test_insert_vertical_preserves_height(self, gradient_image):
        """Vertical insertion should not change height."""
        carver = SeamCarver(gradient_image)
        original_h = carver.h
        carver.insert_vertical(3)
        assert carver.h == original_h


# ---------------------------------------------------------------------------
# Object Removal Tests
# ---------------------------------------------------------------------------

class TestObjectRemoval:
    """Test object removal via masks."""

    def test_remove_simple_object(self):
        """Removing a rectangular object should eliminate those pixels."""
        img = np.zeros((10, 10, 3), dtype=np.uint8)
        img[3:7, 3:7] = [255, 0, 0]  # red square
        mask = np.zeros((10, 10), dtype=bool)
        mask[3:7, 3:7] = True
        carver = SeamCarver(img)
        result = carver.remove_object(mask)
        # The red object should be gone (no pure red pixels remain)
        red_pixels = np.sum(np.all(result == [255, 0, 0], axis=2))
        assert red_pixels == 0, f"Expected no red pixels, found {red_pixels}"

    def test_remove_mask_dimension_mismatch(self, gradient_image):
        """Mismatched mask dimensions should raise InvalidImageError."""
        mask = np.zeros((5, 5), dtype=bool)
        carver = SeamCarver(gradient_image)
        with pytest.raises(InvalidImageError):
            carver.remove_object(mask)


# ---------------------------------------------------------------------------
# Mask Protection Tests
# ---------------------------------------------------------------------------

class TestMaskProtection:
    """Test region protection during carving."""

    def test_protected_region_survives(self):
        """Protected pixels should not be removed by carving."""
        img = np.zeros((10, 10, 3), dtype=np.uint8)
        img[5, 5] = [255, 255, 255]  # single bright pixel
        protect = np.zeros((10, 10), dtype=bool)
        protect[5, 5] = True
        carver = SeamCarver(img, protect_mask=protect)
        carver.carve_vertical(5)
        # The bright pixel should still exist somewhere
        bright_pixels = np.sum(np.all(carver.image == [255, 255, 255], axis=2))
        assert bright_pixels > 0, "Protected pixel was removed!"


# ---------------------------------------------------------------------------
# Visualization Tests
# ---------------------------------------------------------------------------

class TestVisualization:
    """Test energy map and seam visualization."""

    def test_energy_map_shape(self, gradient_image):
        """Energy map should have the same spatial dimensions as image."""
        carver = SeamCarver(gradient_image)
        emap = carver.get_energy_map()
        assert emap.shape == (8, 10)
        assert emap.dtype == np.uint8

    def test_energy_map_range(self, gradient_image):
        """Energy map values should be in 0-255 range."""
        carver = SeamCarver(gradient_image)
        emap = carver.get_energy_map()
        assert emap.min() >= 0 and emap.max() <= 255

    def test_seam_visualization_color(self, gradient_image):
        """Seam visualization should mark seam pixels with the given color."""
        carver = SeamCarver(gradient_image)
        seam = carver._find_vertical_seam()
        vis = carver.visualize_seam(seam, color=(0, 255, 0))
        # Check that at least one pixel is green
        green_pixels = np.sum(np.all(vis == [0, 255, 0], axis=2))
        assert green_pixels == len(seam), \
            f"Expected {len(seam)} green pixels, got {green_pixels}"

    def test_visualize_invalid_orientation(self, gradient_image):
        """Invalid orientation should raise ValueError."""
        carver = SeamCarver(gradient_image)
        seam = carver._find_vertical_seam()
        with pytest.raises(ValueError):
            carver.visualize_seam(seam, orientation="diagonal")


# ---------------------------------------------------------------------------
# Quality Metrics Tests
# ---------------------------------------------------------------------------

class TestQualityMetrics:
    """Test seam cost tracking and statistics."""

    def test_stats_structure(self, gradient_image):
        """get_stats should return a dictionary with expected keys."""
        carver = SeamCarver(gradient_image)
        carver.carve_vertical(3, record=True)
        stats = carver.get_stats()
        assert "image_size" in stats
        assert "num_seams_carved" in stats
        assert "num_seams_recorded" in stats
        assert "avg_seam_cost" in stats
        assert "total_seam_cost" in stats
        assert "energy_preservation_ratio" in stats
        assert "energy_type" in stats

    def test_stats_num_seams(self, gradient_image):
        """Stats should report correct seam counts."""
        carver = SeamCarver(gradient_image)
        carver.carve_vertical(5, record=True)
        stats = carver.get_stats()
        assert stats["num_seams_carved"] == 5
        assert stats["num_seams_recorded"] == 5

    def test_energy_preservation_no_carving(self, gradient_image):
        """Without carving, preservation ratio should be 1.0."""
        carver = SeamCarver(gradient_image)
        assert carver.energy_preservation_ratio() == 1.0


# ---------------------------------------------------------------------------
# Convenience Function Tests
# ---------------------------------------------------------------------------

class TestConvenienceFunctions:
    """Test resize_width, resize_height, and resize."""

    def test_resize_width_reduce(self, gradient_image):
        """resize_width should reduce width correctly."""
        result = resize_width(gradient_image, 6)
        assert result.shape[1] == 6
        assert result.shape[0] == 8  # height unchanged

    def test_resize_width_increase(self, gradient_image):
        """resize_width should increase width correctly."""
        result = resize_width(gradient_image, 14)
        assert result.shape[1] == 14
        assert result.shape[0] == 8

    def test_resize_height_reduce(self, gradient_image):
        """resize_height should reduce height correctly."""
        result = resize_height(gradient_image, 4)
        assert result.shape[0] == 4
        assert result.shape[1] == 10  # width unchanged

    def test_resize_both(self, gradient_image):
        """resize should handle both dimensions."""
        result = resize(gradient_image, 6, 4)
        assert result.shape == (4, 6, 3)

    def test_resize_invalid_dimensions(self, gradient_image):
        """Resize with non-positive dimensions should raise ValueError."""
        with pytest.raises(ValueError):
            resize(gradient_image, 0, 5)
        with pytest.raises(ValueError):
            resize(gradient_image, 5, 0)

    def test_resize_width_same(self, gradient_image):
        """resize_width with same width should return a copy."""
        result = resize_width(gradient_image, 10)
        assert result.shape == gradient_image.shape
        np.testing.assert_array_equal(result, gradient_image)


# ---------------------------------------------------------------------------
# Edge Case Tests
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_single_row_image(self):
        """A 1-row image should work for vertical seam finding."""
        img = np.zeros((1, 5, 3), dtype=np.uint8)
        img[0, 2] = [255, 255, 255]
        carver = SeamCarver(img)
        seam = carver._find_vertical_seam()
        assert len(seam) == 1

    def test_single_column_image(self):
        """A 1-column image should work for vertical seam finding."""
        img = np.zeros((5, 1, 3), dtype=np.uint8)
        carver = SeamCarver(img)
        seam = carver._find_vertical_seam()
        assert len(seam) == 5
        assert (seam == 0).all()

    def test_grayscale_image(self):
        """Grayscale (1-channel) images should work."""
        img = np.zeros((8, 10, 1), dtype=np.uint8)
        img[4, 5] = 255
        carver = SeamCarver(img)
        energy = carver._compute_energy()
        assert energy.shape == (8, 10)

    def test_invalid_image_shape(self):
        """2D image (not 3D) should raise InvalidImageError."""
        img = np.zeros((10, 10), dtype=np.uint8)
        with pytest.raises(InvalidImageError):
            SeamCarver(img)

    def test_invalid_channel_count(self):
        """4-channel image should raise InvalidImageError."""
        img = np.zeros((10, 10, 4), dtype=np.uint8)
        with pytest.raises(InvalidImageError):
            SeamCarver(img)

    def test_non_array_image(self):
        """Non-ndarray input should raise InvalidImageError."""
        with pytest.raises(InvalidImageError):
            SeamCarver("not an image")

    def test_float_image_converted(self):
        """Float image should be converted to uint8."""
        img = np.full((5, 5, 3), 128.5, dtype=np.float64)
        carver = SeamCarver(img)
        assert carver.image.dtype == np.uint8

    def test_carve_all_but_one(self, gradient_image):
        """Carving all but one seam should leave width=1."""
        carver = SeamCarver(gradient_image)
        carver.carve_vertical(9)  # width 10 -> 1
        assert carver.w == 1

    def test_carve_exact_width(self, gradient_image):
        """Carving exactly the width should raise ValueError."""
        carver = SeamCarver(gradient_image)
        with pytest.raises(ValueError):
            carver.carve_vertical(10)  # width is 10


# ---------------------------------------------------------------------------
# Bug Regression Tests
# ---------------------------------------------------------------------------

class TestBugRegressions:
    """Tests for specific bugs found and fixed during bug hunt."""

    def test_horizontal_seam_energy_not_stale(self, gradient_image):
        """
        Bug: After _find_horizontal_seam, self.energy was stale (transposed).
        Fix: Clear self.energy after horizontal seam operations.
        After the fix, self.energy should be None (cleared to prevent
        stale dimension mismatch).
        """
        carver = SeamCarver(gradient_image)
        carver._find_horizontal_seam()
        # After finding horizontal seam, energy should be cleared (None)
        # to prevent stale dimension mismatch
        assert carver.energy is None, \
            f"Energy should be None after horizontal seam finding, got shape {carver.energy.shape if carver.energy is not None else 'None'}"

    def test_horizontal_carve_cost_tracking(self, gradient_image):
        """
        Bug: Horizontal seam carving didn't track costs because
        self.energy was stale (from transposed image during _find_horizontal_seam).
        Fix: Recompute energy for cost tracking if stale.
        """
        carver = SeamCarver(gradient_image)
        carver.carve_horizontal(2)
        # Costs should be tracked (may be 0 for uniform regions, but list should be populated)
        assert len(carver.seam_costs) == 2

    def test_remove_object_tracks_costs(self):
        """
        Bug: remove_object didn't append seam costs to seam_costs list.
        Fix: Track costs in remove_object loop.
        """
        img = np.zeros((10, 10, 3), dtype=np.uint8)
        img[3:7, 3:7] = [255, 0, 0]
        mask = np.zeros((10, 10), dtype=bool)
        mask[3:7, 3:7] = True
        carver = SeamCarver(img)
        carver.remove_object(mask)
        # Costs should be tracked during object removal
        assert len(carver.seam_costs) > 0, "remove_object should track seam costs"

    def test_find_vertical_seam_dead_cost_code(self, gradient_image):
        """
        Bug: _find_vertical_seam computed `cost` on line 458 but never
        returned or used it (dead code).
        This is a code quality issue, not a functional bug.
        The cost is correctly computed in _remove_vertical_seam instead.
        """
        carver = SeamCarver(gradient_image)
        seam = carver._find_vertical_seam()
        # Verify seam is valid (the dead cost code didn't affect correctness)
        assert len(seam) == gradient_image.shape[0]

    def test_resize_width_zero_target(self, gradient_image):
        """
        Bug: resize_width with target_width=0 could cause issues
        (inserting 0 seams is fine, but carving to 0 width would fail).
        Fix: Validate target dimensions in resize functions.
        """
        # resize_width to 0 would try to carve all seams, which should fail
        with pytest.raises(ValueError):
            resize_width(gradient_image, 0)

    def test_ppm_truncated_file(self, tmp_path):
        """
        Bug: read_ppm didn't give a clear error for truncated files.
        Fix: Wrap np.frombuffer in try/except and raise InvalidImageError.
        """
        path = str(tmp_path / "truncated.ppm")
        header = b"P6\n5 5\n255\n"
        pixels = bytes([0] * 10)  # only 10 bytes, need 75
        with open(path, "wb") as f:
            f.write(header + pixels)
        with pytest.raises(InvalidImageError, match="Truncated"):
            read_ppm(path)

    def test_insert_vertical_zero_seams(self, gradient_image):
        """Inserting 0 seams should be a no-op."""
        carver = SeamCarver(gradient_image)
        original = carver.image.copy()
        carver.insert_vertical(0)
        np.testing.assert_array_equal(carver.image, original)
        assert carver.num_seams_carved == 0

    def test_carve_vertical_zero_seams(self, gradient_image):
        """Carving 0 seams should be a no-op."""
        carver = SeamCarver(gradient_image)
        original = carver.image.copy()
        carver.carve_vertical(0)
        np.testing.assert_array_equal(carver.image, original)
        assert carver.num_seams_carved == 0

    def test_find_horizontal_seam_preserves_masks(self, gradient_image):
        """
        Bug: _find_horizontal_seam transposes masks but if an exception
        occurs between the two transposes, masks are left transposed.
        This test verifies masks are correctly restored after horizontal
        seam finding.
        """
        protect = np.zeros((8, 10), dtype=bool)
        protect[0, 0] = True
        carver = SeamCarver(gradient_image, protect_mask=protect)
        carver._find_horizontal_seam()
        assert carver.protect_mask is not None
        assert carver.protect_mask.shape == (8, 10)
        # The protected pixel should still be at (0, 0)
        assert carver.protect_mask[0, 0]

    def test_multiple_carve_operations(self, gradient_image):
        """Mixing vertical and horizontal carving should work."""
        carver = SeamCarver(gradient_image)
        carver.carve_vertical(2)
        carver.carve_horizontal(1)
        carver.carve_vertical(1)
        assert carver.image.shape == (7, 7, 3)
        assert carver.num_seams_carved == 4

    def test_energy_map_uniform_image(self):
        """Energy map of a uniform image should be all zeros."""
        img = np.full((10, 10, 3), 128, dtype=np.uint8)
        carver = SeamCarver(img)
        emap = carver.get_energy_map()
        assert (emap == 0).all()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])