"""
seamcarving/cli.py — Command-line interface for seam carving.

Supports:
  - Resize to target width/height
  - Object removal via mask
  - Region protection via mask
  - Energy function selection (7 types)
  - Energy map and seam visualization export
  - Animation frame export
  - Batch processing of multiple images
  - Statistics output
  - Config file support (JSON/YAML/TOML)
  - Logging with file output and JSON mode
  - PNG output (via stdlib zlib)

Usage
-----
::

    python3 -m seamcarving input.ppm output.ppm -W 100
    python3 -m seamcarving input.png output.png -W 200 -H 150 -e forward
    python3 -m seamcarving input.ppm output.ppm --config config.yaml
    python3 -m seamcarving batch input_dir/ output_dir/ -W 100 --format png
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

import numpy as np

from .carver import SeamCarver, resize, resize_width, resize_height
from .config import CarverConfig
from .energy import EnergyType
from .exceptions import SeamCarvingError, InvalidImageError
from .io import read_image, write_image, read_ppm, write_ppm
from .logging import get_logger

logger = get_logger("seamcarving.cli", configure=False)


# ---------------------------------------------------------------------------
# Mask parsing
# ---------------------------------------------------------------------------

def _parse_mask_file(path: str, h: int, w: int) -> np.ndarray:
    """Read a mask from a PGM/PNG file (non-zero = active)."""
    mask_img = read_image(path)
    if mask_img.ndim == 3:
        mask_img = mask_img[:, :, 0]
    if mask_img.shape != (h, w):
        raise InvalidImageError(
            f"Mask file {path} has shape {mask_img.shape}, expected ({h}, {w})"
        )
    return mask_img > 0


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

def process_batch(
    input_dir: str,
    output_dir: str,
    target_width: Optional[int] = None,
    target_height: Optional[int] = None,
    energy_type: EnergyType = EnergyType.SOBEL,
    output_format: str = "ppm",
    log_level: str = "INFO",
) -> List[str]:
    """Process all images in a directory.

    Returns a list of output file paths.
    """
    input_dir_path = Path(input_dir)
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    # Find all images
    extensions = {".ppm", ".pgm", ".png"}
    images = sorted(
        f for f in input_dir_path.iterdir()
        if f.suffix.lower() in extensions
    )

    if not images:
        logger.warning("No images found in %s", input_dir)
        return []

    results = []
    for img_path in images:
        try:
            logger.info("Processing %s...", img_path.name)
            img = read_image(img_path)
            if target_width or target_height:
                tw = target_width or img.shape[1]
                th = target_height or img.shape[0]
                result = resize(img, tw, th, energy_type)
            else:
                result = img

            out_name = img_path.stem + "." + output_format
            out_path = output_dir_path / out_name
            write_image(str(out_path), result)
            results.append(str(out_path))
            logger.info("  -> %s (%dx%d)", out_name, result.shape[1], result.shape[0])
        except Exception as e:
            logger.error("Failed to process %s: %s", img_path.name, e)

    return results


# ---------------------------------------------------------------------------
# Single image processing
# ---------------------------------------------------------------------------

def process_single(
    input_path: str,
    output_path: str,
    config: CarverConfig,
) -> None:
    """Process a single image with the given configuration."""
    energy_type = EnergyType(config.energy_type)

    img = read_image(input_path)
    h, w = img.shape[:2]
    logger.info("Input: %s (%dx%d)", input_path, w, h)

    # Read masks
    protect_mask = None
    remove_mask = None
    if config.protect_mask_path:
        protect_mask = _parse_mask_file(config.protect_mask_path, h, w)
    if config.remove_mask_path:
        remove_mask = _parse_mask_file(config.remove_mask_path, h, w)

    carver = SeamCarver(
        img, energy_type=energy_type,
        protect_mask=protect_mask, remove_mask=remove_mask,
    )

    start_time = time.time()

    if config.remove_mask_path and remove_mask is not None:
        # Object removal mode
        result = carver.remove_object(remove_mask, max_iterations=config.max_iterations)
    elif config.target_width is not None or config.target_height is not None:
        tw = config.target_width if config.target_width is not None else carver.w
        th = config.target_height if config.target_height is not None else carver.h
        w_diff = tw - carver.w
        h_diff = th - carver.h

        # Animation dir
        anim_dir = None
        if config.animation_dir:
            anim_dir = config.animation_dir
            os.makedirs(anim_dir, exist_ok=True)

        if w_diff < 0:
            carver.carve_vertical(
                -w_diff, record=config.record_seams,
                animation_dir=anim_dir, animation_format=config.animation_format,
            )
        if h_diff < 0:
            carver.carve_horizontal(
                -h_diff, record=config.record_seams,
                animation_dir=anim_dir, animation_format=config.animation_format,
            )
        if w_diff > 0:
            carver.insert_vertical(w_diff)
        if h_diff > 0:
            carver.insert_horizontal(h_diff)
        result = carver.image
    else:
        logger.warning("No target dimensions or removal mask specified; "
                        "outputting original image.")
        result = img

    elapsed = time.time() - start_time
    logger.info("Output: %s (%dx%d) in %.2fs", output_path,
                result.shape[1], result.shape[0], elapsed)

    write_image(output_path, result)

    # Energy map export
    if config.energy_map_path:
        emap_carver = SeamCarver(img, energy_type=energy_type)
        emap = emap_carver.get_energy_map()
        emap_rgb = np.repeat(emap[:, :, np.newaxis], 3, axis=2)
        write_image(config.energy_map_path, emap_rgb)
        logger.info("Energy map saved to: %s", config.energy_map_path)

    # Seam visualization export
    if config.seam_vis_path:
        vis_carver = SeamCarver(img, energy_type=energy_type)
        seam = vis_carver._find_vertical_seam()
        vis = vis_carver.visualize_seam(seam, "vertical")
        write_image(config.seam_vis_path, vis)
        logger.info("Seam visualization saved to: %s", config.seam_vis_path)

    # Stats
    stats = carver.get_stats()
    logger.info("Statistics:")
    for key, val in stats.items():
        logger.info("  %s: %s", key, val)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser for the default (resize) mode."""
    parser = argparse.ArgumentParser(
        prog="seamcarving",
        description="Content-aware image resizing via seam carving "
                    "(Avidan & Shamir 2007)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Resize to 100px wide
  python3 -m seamcarving input.ppm output.ppm -W 100

  # Resize to 200x150 with forward energy
  python3 -m seamcarving input.ppm output.ppm -W 200 -H 150 -e forward

  # Export animation frames as PNG
  python3 -m seamcarving input.ppm output.ppm -W 100 --animate frames/

  # Object removal with mask
  python3 -m seamcarving input.ppm output.ppm --remove mask.pgm

  # Batch process a directory
  python3 -m seamcarving batch input_dir/ output_dir/ -W 100 --format png

  # Use config file
  python3 -m seamcarving input.ppm output.ppm --config config.yaml

  # Save config template
  python3 -m seamcarving save-config config.json
""",
    )
    parser.add_argument("input", help="Input image file")
    parser.add_argument("output", help="Output image file")
    _add_single_args(parser)
    return parser


def build_subparser(prog: str, description: str) -> argparse.ArgumentParser:
    """Build a subcommand parser."""
    parser = argparse.ArgumentParser(
        prog=f"seamcarving {prog}",
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    return parser


def _add_single_args(parser: argparse.ArgumentParser) -> None:
    """Add single-image arguments to a parser or subparser."""
    parser.add_argument("-W", "--width", type=int, help="Target width")
    parser.add_argument("-H", "--height", type=int, help="Target height")
    parser.add_argument(
        "-e", "--energy",
        choices=[e.value for e in EnergyType],
        default="sobel",
        help="Energy function (default: sobel)",
    )
    parser.add_argument(
        "--energy-map", metavar="PATH",
        help="Save the energy map visualization to this file",
    )
    parser.add_argument(
        "--seam-vis", metavar="PATH",
        help="Save a visualization of the first seam to this file",
    )
    parser.add_argument(
        "--protect", metavar="PATH",
        help="Mask file: non-zero pixels are protected from carving",
    )
    parser.add_argument(
        "--remove", metavar="PATH",
        help="Mask file: non-zero pixels are marked for object removal",
    )
    parser.add_argument(
        "--animate", metavar="DIR",
        help="Export animation frames to this directory",
    )
    parser.add_argument(
        "--animation-format", default="png",
        choices=["ppm", "png"],
        help="Animation frame format (default: png)",
    )
    parser.add_argument(
        "--config", metavar="PATH",
        help="Load configuration from a JSON/YAML/TOML file",
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Print carver statistics after processing",
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO)",
    )
    parser.add_argument(
        "--log-file", metavar="PATH",
        help="Write logs to this file",
    )
    parser.add_argument(
        "--json-logs", action="store_true",
        help="Format log messages as JSON",
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> int:
    """CLI entry point."""
    # Check for subcommands by inspecting sys.argv before argparse
    argv = sys.argv[1:]

    SUBCOMMANDS = {
        "batch": _run_batch,
        "save-config": _run_save_config,
        "config-info": _run_config_info,
    }

    if argv and argv[0] in SUBCOMMANDS:
        return SUBCOMMANDS[argv[0]](argv[1:])

    # Default: single image processing
    parser = build_parser()
    args = parser.parse_args(argv)

    input_path = args.input
    output_path = args.output

    # Load config
    if args.config:
        config = CarverConfig.load(args.config)
    else:
        config = CarverConfig()

    # Override config with CLI args
    config.energy_type = args.energy
    if args.width is not None:
        config.target_width = args.width
    if args.height is not None:
        config.target_height = args.height
    if args.energy_map:
        config.energy_map_path = args.energy_map
    if args.seam_vis:
        config.seam_vis_path = args.seam_vis
    if args.protect:
        config.protect_mask_path = args.protect
    if args.remove:
        config.remove_mask_path = args.remove
    if args.animate:
        config.animation_dir = args.animate
    if args.animation_format:
        config.animation_format = args.animation_format
    if args.log_level:
        config.log_level = args.log_level
    if args.log_file:
        config.log_file = args.log_file
    if args.json_logs:
        config.json_logs = args.json_logs

    config.validate()

    # Configure logging
    import logging as _logging
    log_level = getattr(_logging, config.log_level.upper(), _logging.INFO)
    get_logger(
        "seamcarving", level=log_level,
        log_file=config.log_file, json_format=config.json_logs,
    )

    try:
        process_single(input_path, output_path, config)
    except SeamCarvingError as e:
        logger.error("Error: %s", e)
        return 1
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return 1

    return 0


def _run_save_config(argv: list) -> int:
    """Handle the 'save-config' subcommand."""
    parser = argparse.ArgumentParser(
        prog="seamcarving save-config",
        description="Save a default configuration file",
    )
    parser.add_argument("path", help="Output config path (.json/.yaml/.toml)")
    args = parser.parse_args(argv)
    config = CarverConfig()
    config.save(args.path)
    print(f"Default config saved to: {args.path}")
    return 0


def _run_config_info(argv: list) -> int:
    """Handle the 'config-info' subcommand."""
    parser = argparse.ArgumentParser(
        prog="seamcarving config-info",
        description="Print current configuration",
    )
    parser.add_argument("--config", help="Config file to load")
    args = parser.parse_args(argv)
    if args.config:
        config = CarverConfig.load(args.config)
    else:
        config = CarverConfig()
    print(config.to_json())
    return 0


def _run_batch(argv: list) -> int:
    """Handle the 'batch' subcommand."""
    parser = argparse.ArgumentParser(
        prog="seamcarving batch",
        description="Batch process a directory of images",
    )
    parser.add_argument("input_dir", help="Directory of input images")
    parser.add_argument("output_dir", help="Directory for output images")
    parser.add_argument("-W", "--width", type=int, help="Target width")
    parser.add_argument("-H", "--height", type=int, help="Target height")
    parser.add_argument(
        "-e", "--energy",
        choices=[e.value for e in EnergyType],
        default="sobel",
        help="Energy function (default: sobel)",
    )
    parser.add_argument(
        "--format", default="ppm",
        choices=["ppm", "pgm", "png"],
        help="Output format (default: ppm)",
    )
    parser.add_argument("--log-level", default="INFO", help="Log level")
    args = parser.parse_args(argv)

    import logging as _logging
    log_level = getattr(_logging, args.log_level.upper(), _logging.INFO)
    get_logger("seamcarving", level=log_level)
    results = process_batch(
        args.input_dir, args.output_dir,
        target_width=args.width, target_height=args.height,
        energy_type=EnergyType(args.energy),
        output_format=args.format,
        log_level=args.log_level,
    )
    print(f"Processed {len(results)} images")
    return 0


if __name__ == "__main__":
    sys.exit(main())