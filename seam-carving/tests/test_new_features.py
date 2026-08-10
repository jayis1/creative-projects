#!/usr/bin/env python3
"""
tests/test_new_features.py — Tests for v3.0 features.

Tests cover:
  - PNG I/O (write/read round-trip, grayscale, RGB)
  - Unified image I/O dispatch (read_image/write_image)
  - New energy functions (Hofer, entropy)
  - Config system (CarverConfig, load/save, validation)
  - Logging (get_logger, JSON formatter)
  - Animation frame export
  - Batch processing
  - CLI subcommands
  - Exception hierarchy
  - New stats fields (min/max seam cost)
"""

import os
import sys
import tempfile
import json

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seamcarving import (
    SeamCarver, EnergyType, SeamCarvingError, InvalidImageError,
    InvalidConfigError, EnergyComputationError,
    read_ppm, write_ppm, read_png, write_png,
    read_image, write_image,
    resize, resize_width, resize_height,
    CarverConfig,
)
from seamcarving.energy import (
    sobel_energy, prewitt_energy, laplacian_energy,
    gradient_energy, forward_energy, hofer_energy, entropy_energy,
    to_gray, compute_energy,
)


# ---------------------------------------------------------------------------
# PNG I/O Tests
# ---------------------------------------------------------------------------

class TestPNGIO:
    """Test PNG read/write using stdlib zlib."""

    def test_png_rgb_round_trip(self, tmp_path):
        """PNG write then read should preserve RGB pixel data."""
        img = np.random.randint(0, 256, (8, 10, 3), dtype=np.uint8)
        path = str(tmp_path / "test.png")
        write_png(path, img)
        result = read_png(path)
        assert result.shape == (8, 10, 3)
        np.testing.assert_array_equal(result, img)

    def test_png_grayscale_round_trip(self, tmp_path):
        """PNG write then read should preserve grayscale pixel data."""
        img = np.random.randint(0, 256, (8, 10, 1), dtype=np.uint8)
        path = str(tmp_path / "gray.png")
        write_png(path, img)
        result = read_png(path)
        assert result.shape == (8, 10, 1)
        np.testing.assert_array_equal(result, img)

    def test_png_2d_array(self, tmp_path):
        """Writing a 2D array as PNG should produce a grayscale image."""
        img = np.random.randint(0, 256, (5, 7), dtype=np.uint8)
        path = str(tmp_path / "flat.png")
        write_png(path, img)
        result = read_png(path)
        assert result.shape == (5, 7, 1)

    def test_png_invalid_file(self, tmp_path):
        """Reading a non-PNG file should raise InvalidImageError."""
        path = str(tmp_path / "bad.png")
        with open(path, "wb") as f:
            f.write(b"NOTAPNG")
        with pytest.raises(InvalidImageError):
            read_png(path)

    def test_png_float_converted(self, tmp_path):
        """Float arrays should be clipped and converted to uint8."""
        img = np.full((4, 4, 3), 128.5, dtype=np.float64)
        path = str(tmp_path / "float.png")
        write_png(path, img)
        result = read_png(path)
        assert result.dtype == np.uint8


# ---------------------------------------------------------------------------
# Unified I/O Tests
# ---------------------------------------------------------------------------

class TestUnifiedIO:
    """Test the unified read_image/write_image dispatch."""

    def test_read_ppm_via_dispatch(self, tmp_path):
        """read_image should dispatch to PPM reader for .ppm files."""
        img = np.random.randint(0, 256, (4, 5, 3), dtype=np.uint8)
        path = str(tmp_path / "test.ppm")
        write_ppm(path, img)
        result = read_image(path)
        np.testing.assert_array_equal(result, img)

    def test_read_png_via_dispatch(self, tmp_path):
        """read_image should dispatch to PNG reader for .png files."""
        img = np.random.randint(0, 256, (4, 5, 3), dtype=np.uint8)
        path = str(tmp_path / "test.png")
        write_png(path, img)
        result = read_image(path)
        np.testing.assert_array_equal(result, img)

    def test_write_ppm_via_dispatch(self, tmp_path):
        """write_image should dispatch to PPM writer for .ppm files."""
        img = np.random.randint(0, 256, (4, 5, 3), dtype=np.uint8)
        path = str(tmp_path / "test.ppm")
        write_image(path, img)
        result = read_ppm(path)
        np.testing.assert_array_equal(result, img)

    def test_write_png_via_dispatch(self, tmp_path):
        """write_image should dispatch to PNG writer for .png files."""
        img = np.random.randint(0, 256, (4, 5, 3), dtype=np.uint8)
        path = str(tmp_path / "test.png")
        write_image(path, img)
        result = read_png(path)
        np.testing.assert_array_equal(result, img)

    def test_read_unsupported_format(self, tmp_path):
        """Unsupported format should raise InvalidImageError."""
        path = str(tmp_path / "test.xyz")
        with open(path, "wb") as f:
            f.write(b"DATA")
        with pytest.raises(InvalidImageError):
            read_image(path)

    def test_read_auto_detect_ppm(self, tmp_path):
        """read_image should auto-detect PPM by magic bytes even without extension."""
        img = np.random.randint(0, 256, (4, 5, 3), dtype=np.uint8)
        path = str(tmp_path / "noext")
        write_ppm(path, img)
        result = read_image(path)
        np.testing.assert_array_equal(result, img)


# ---------------------------------------------------------------------------
# New Energy Function Tests
# ---------------------------------------------------------------------------

class TestNewEnergyFunctions:
    """Test Hofer and Entropy energy functions."""

    def test_hofer_energy_shape(self):
        """Hofer energy should match image spatial dimensions."""
        img = np.random.randint(0, 256, (10, 12, 3), dtype=np.uint8)
        gray = to_gray(img)
        e = hofer_energy(gray)
        assert e.shape == (10, 12)

    def test_entropy_energy_shape(self):
        """Entropy energy should match image spatial dimensions."""
        img = np.random.randint(0, 256, (10, 12, 3), dtype=np.uint8)
        gray = to_gray(img)
        e = entropy_energy(gray)
        assert e.shape == (10, 12)

    def test_hofer_energy_non_negative(self):
        """Hofer energy should be non-negative."""
        img = np.random.randint(0, 256, (10, 10, 3), dtype=np.uint8)
        gray = to_gray(img)
        e = hofer_energy(gray)
        assert (e >= 0).all()

    def test_entropy_energy_non_negative(self):
        """Entropy energy should be non-negative."""
        img = np.random.randint(0, 256, (10, 10, 3), dtype=np.uint8)
        gray = to_gray(img)
        e = entropy_energy(gray)
        assert (e >= 0).all()

    def test_hofer_uniform_image(self):
        """Hofer energy on a uniform image should be low/zero."""
        img = np.full((10, 10, 3), 128, dtype=np.uint8)
        gray = to_gray(img)
        e = hofer_energy(gray)
        # Uniform image has minimal texture
        assert e.max() < 1.0

    def test_entropy_uniform_image(self):
        """Entropy energy on a uniform image should be zero."""
        img = np.full((10, 10, 3), 128, dtype=np.uint8)
        gray = to_gray(img)
        e = entropy_energy(gray)
        assert e.max() < 1e-6

    @pytest.mark.parametrize("etype", [EnergyType.HOFER, EnergyType.ENTROPY])
    def test_new_energy_with_seamcarver(self, etype):
        """New energy functions should work with SeamCarver."""
        img = np.random.randint(0, 256, (8, 10, 3), dtype=np.uint8)
        carver = SeamCarver(img, energy_type=etype)
        energy = carver._compute_energy()
        assert energy.shape == (8, 10)

    @pytest.mark.parametrize("etype", [EnergyType.HOFER, EnergyType.ENTROPY])
    def test_new_energy_carve(self, etype):
        """Carving with new energy functions should reduce width."""
        img = np.random.randint(0, 256, (8, 10, 3), dtype=np.uint8)
        carver = SeamCarver(img, energy_type=etype)
        carver.carve_vertical(3)
        assert carver.w == 7

    def test_compute_energy_dispatch(self):
        """compute_energy should dispatch correctly."""
        gray = to_gray(np.random.randint(0, 256, (5, 5, 3), dtype=np.uint8))
        for etype in EnergyType:
            e = compute_energy(gray, etype)
            assert e.shape == (5, 5)

    def test_compute_energy_unknown_type(self):
        """Unknown energy type should raise EnergyComputationError."""
        gray = np.zeros((5, 5), dtype=np.float64)
        with pytest.raises(EnergyComputationError):
            compute_energy(gray, "unknown")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Config Tests
# ---------------------------------------------------------------------------

class TestConfig:
    """Test the CarverConfig system."""

    def test_default_config(self):
        """Default config should have sensible values."""
        config = CarverConfig()
        assert config.energy_type == "sobel"
        assert config.target_width is None
        assert config.max_iterations == 500

    def test_config_validate_valid(self):
        """A valid config should pass validation."""
        config = CarverConfig(energy_type="forward", target_width=100)
        config.validate()

    def test_config_validate_invalid_energy(self):
        """Invalid energy type should raise InvalidConfigError."""
        config = CarverConfig(energy_type="nonexistent")
        with pytest.raises(InvalidConfigError):
            config.validate()

    def test_config_validate_invalid_width(self):
        """Non-positive target width should raise InvalidConfigError."""
        config = CarverConfig(target_width=0)
        with pytest.raises(InvalidConfigError):
            config.validate()

    def test_config_validate_invalid_log_level(self):
        """Invalid log level should raise InvalidConfigError."""
        config = CarverConfig(log_level="VERBOSE")
        with pytest.raises(InvalidConfigError):
            config.validate()

    def test_config_json_round_trip(self, tmp_path):
        """Config should survive JSON save/load round-trip."""
        config = CarverConfig(
            energy_type="forward",
            target_width=200,
            target_height=150,
            log_level="DEBUG",
            record_seams=True,
        )
        path = str(tmp_path / "config.json")
        config.save(path)
        loaded = CarverConfig.load(path)
        assert loaded.energy_type == "forward"
        assert loaded.target_width == 200
        assert loaded.target_height == 150
        assert loaded.log_level == "DEBUG"
        assert loaded.record_seams is True

    def test_config_yaml_round_trip(self, tmp_path):
        """Config should survive YAML save/load round-trip."""
        config = CarverConfig(energy_type="laplacian", target_width=50)
        path = str(tmp_path / "config.yaml")
        config.save(path)
        loaded = CarverConfig.load(path)
        assert loaded.energy_type == "laplacian"
        assert loaded.target_width == 50

    def test_config_toml_round_trip(self, tmp_path):
        """Config should survive TOML save/load round-trip."""
        config = CarverConfig(energy_type="gradient", target_width=80)
        path = str(tmp_path / "config.toml")
        config.save(path)
        loaded = CarverConfig.load(path)
        assert loaded.energy_type == "gradient"
        assert loaded.target_width == 80

    def test_config_from_dict(self):
        """from_dict should ignore unknown keys."""
        data = {"energy_type": "sobel", "unknown_key": "value"}
        config = CarverConfig.from_dict(data)
        assert config.energy_type == "sobel"

    def test_config_to_json_string(self):
        """to_json should produce valid JSON."""
        config = CarverConfig()
        s = config.to_json()
        data = json.loads(s)
        assert "energy_type" in data

    def test_config_load_not_found(self):
        """Loading a non-existent config should raise InvalidConfigError."""
        with pytest.raises(InvalidConfigError):
            CarverConfig.load("/nonexistent/path.json")

    def test_config_load_unsupported_format(self, tmp_path):
        """Unsupported format should raise InvalidConfigError."""
        path = str(tmp_path / "config.txt")
        with open(path, "w") as f:
            f.write("data")
        with pytest.raises(InvalidConfigError):
            CarverConfig.load(path)


# ---------------------------------------------------------------------------
# Logging Tests
# ---------------------------------------------------------------------------

class TestLogging:
    """Test the logging module."""

    def test_get_logger(self):
        """get_logger should return a configured logger."""
        from seamcarving.logging import get_logger
        import logging

        logger = get_logger("test", level=logging.DEBUG)
        assert logger.level == logging.DEBUG
        assert len(logger.handlers) > 0

    def test_get_logger_with_file(self, tmp_path):
        """get_logger with file should add a file handler."""
        from seamcarving.logging import get_logger
        import logging

        log_file = str(tmp_path / "test.log")
        logger = get_logger("test_file", log_file=log_file)
        logger.info("Test message")
        for h in logger.handlers:
            h.flush()
        assert os.path.exists(log_file)

    def test_json_formatter(self):
        """JSON formatter should produce valid JSON."""
        from seamcarving.logging import JSONFormatter
        import logging

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py",
            lineno=1, msg="Test message", args=(), exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["message"] == "Test message"
        assert data["level"] == "INFO"


# ---------------------------------------------------------------------------
# Animation Export Tests
# ---------------------------------------------------------------------------

class TestAnimationExport:
    """Test animation frame export."""

    def test_animation_dir_created(self, tmp_path):
        """Animation frames should be exported to the specified directory."""
        img = np.random.randint(0, 256, (8, 10, 3), dtype=np.uint8)
        anim_dir = str(tmp_path / "anim")
        carver = SeamCarver(img, energy_type=EnergyType.SOBEL)
        carver.carve_vertical(3, animation_dir=anim_dir, animation_format="png")
        assert os.path.isdir(anim_dir)
        frames = [f for f in os.listdir(anim_dir) if f.endswith(".png")]
        assert len(frames) == 3

    def test_animation_ppm_format(self, tmp_path):
        """Animation frames should support PPM format."""
        img = np.random.randint(0, 256, (8, 10, 3), dtype=np.uint8)
        anim_dir = str(tmp_path / "anim_ppm")
        carver = SeamCarver(img, energy_type=EnergyType.SOBEL)
        carver.carve_vertical(2, animation_dir=anim_dir, animation_format="ppm")
        frames = [f for f in os.listdir(anim_dir) if f.endswith(".ppm")]
        assert len(frames) == 2

    def test_animation_horizontal(self, tmp_path):
        """Horizontal carving should also support animation export."""
        img = np.random.randint(0, 256, (10, 8, 3), dtype=np.uint8)
        anim_dir = str(tmp_path / "anim_h")
        carver = SeamCarver(img, energy_type=EnergyType.SOBEL)
        carver.carve_horizontal(2, animation_dir=anim_dir, animation_format="png")
        frames = [f for f in os.listdir(anim_dir) if f.endswith(".png")]
        assert len(frames) == 2


# ---------------------------------------------------------------------------
# Enhanced Stats Tests
# ---------------------------------------------------------------------------

class TestEnhancedStats:
    """Test the enhanced statistics fields."""

    def test_stats_min_max_cost(self):
        """get_stats should include min and max seam cost."""
        img = np.random.randint(0, 256, (10, 10, 3), dtype=np.uint8)
        carver = SeamCarver(img)
        carver.carve_vertical(3)
        stats = carver.get_stats()
        assert "min_seam_cost" in stats
        assert "max_seam_cost" in stats
        assert stats["min_seam_cost"] <= stats["max_seam_cost"]

    def test_stats_empty_costs(self):
        """Stats with no carving should have zero costs."""
        img = np.zeros((10, 10, 3), dtype=np.uint8)
        carver = SeamCarver(img)
        stats = carver.get_stats()
        assert stats["min_seam_cost"] == 0.0
        assert stats["max_seam_cost"] == 0.0


# ---------------------------------------------------------------------------
# Exception Hierarchy Tests
# ---------------------------------------------------------------------------

class TestExceptionHierarchy:
    """Test the exception hierarchy."""

    def test_all_inherit_from_base(self):
        """All custom exceptions should inherit from SeamCarvingError."""
        from seamcarving.exceptions import (
            InvalidImageError, InvalidConfigError, InvalidMaskError,
            EnergyComputationError, SeamOperationError,
        )
        for exc_class in [
            InvalidImageError, InvalidConfigError, InvalidMaskError,
            EnergyComputationError, SeamOperationError,
        ]:
            assert issubclass(exc_class, SeamCarvingError)

    def test_invalid_image_with_path(self):
        """InvalidImageError should include path info when provided."""
        exc = InvalidImageError("Bad file", "/path/to/file.ppm")
        assert exc.path == "/path/to/file.ppm"
        assert "/path/to/file.ppm" in str(exc)


# ---------------------------------------------------------------------------
# Core Module Backward Compatibility Tests
# ---------------------------------------------------------------------------

class TestBackwardCompatibility:
    """Test that importing from seamcarving.core still works."""

    def test_import_from_core(self):
        """Core module should re-export all public names."""
        from seamcarving.core import (
            SeamCarver, EnergyType, SeamCarvingError, InvalidImageError,
            resize_width, resize_height, resize, read_ppm, write_ppm,
        )
        assert SeamCarver is not None
        assert EnergyType is not None

    def test_core_main_exists(self):
        """Core module should have a main function for CLI."""
        from seamcarving.core import main
        assert callable(main)

    def test_core_cli_still_works(self):
        """Running core.py as main should still work."""
        from seamcarving.core import main
        # main() with --help should return 0
        import sys
        old_argv = sys.argv
        sys.argv = ["seamcarving", "--help"]
        try:
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
        finally:
            sys.argv = old_argv


# ---------------------------------------------------------------------------
# Batch Processing Tests
# ---------------------------------------------------------------------------

class TestBatchProcessing:
    """Test batch processing of directories."""

    def test_batch_process(self, tmp_path):
        """Batch processing should handle multiple images."""
        from seamcarving.cli import process_batch

        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()

        # Create test images
        for i in range(3):
            img = np.random.randint(0, 256, (8, 10, 3), dtype=np.uint8)
            write_png(str(input_dir / f"img{i}.png"), img)

        results = process_batch(
            str(input_dir), str(output_dir),
            target_width=8, energy_type=EnergyType.SOBEL,
            output_format="png",
        )
        assert len(results) == 3
        for r in results:
            assert os.path.exists(r)

    def test_batch_empty_dir(self, tmp_path):
        """Batch processing an empty directory should return empty list."""
        from seamcarving.cli import process_batch

        input_dir = tmp_path / "empty"
        output_dir = tmp_path / "output"
        input_dir.mkdir()

        results = process_batch(str(input_dir), str(output_dir))
        assert len(results) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])