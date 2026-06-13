#!/usr/bin/env python3
"""
LOOM — Terminal Generative Art Weaver
Creates animated geometric tapestry patterns using Unicode block characters.
Patterns are generated from layered trigonometric functions and rendered
as a continuously evolving woven textile in your terminal.

Version: 1.1.1
"""

import os
import sys
import time
import math
import random
import argparse
import signal
from collections import namedtuple

# ─── Version ────────────────────────────────────────────────────────────
__version__ = "1.1.1"

# ─── Unicode block characters for weaving ───────────────────────────────
BLOCKS = {
    "full": "█",
    "dark": "▓",
    "medium": "▒",
    "light": "░",
    "top_half": "▀",
    "bottom_half": "▄",
    "left_half": "▌",
    "right_half": "▐",
    "quad_tl": "▘",
    "quad_tr": "▝",
    "quad_bl": "▖",
    "quad_br": "▗",
    "quad_full": "█",
    "dot": "·",
    "shade1": "░",
    "shade2": "▒",
    "shade3": "▓",
}

# Color palette threads for the loom
PALETTES = {
    "sunset": [(255, 80, 50), (255, 160, 40), (255, 220, 80), (180, 40, 80), (120, 20, 60)],
    "ocean": [(20, 80, 160), (40, 160, 200), (80, 220, 240), (10, 40, 100), (60, 200, 180)],
    "forest": [(30, 120, 40), (80, 200, 60), (160, 220, 80), (20, 80, 30), (100, 180, 100)],
    "neon": [(255, 0, 128), (0, 255, 128), (128, 0, 255), (255, 255, 0), (0, 200, 255)],
    "ember": [(255, 60, 0), (255, 120, 20), (200, 40, 0), (255, 200, 50), (120, 10, 0)],
    "aurora": [(80, 255, 180), (40, 120, 255), (200, 80, 255), (120, 255, 200), (60, 200, 160)],
    "monochrome": [(255, 255, 255), (200, 200, 200), (140, 140, 140), (80, 80, 80), (40, 40, 40)],
    "thermal": [(0, 0, 40), (0, 60, 180), (220, 40, 40), (255, 180, 0), (255, 255, 200)],
    "nightshade": [(40, 0, 60), (100, 0, 120), (180, 40, 160), (255, 100, 200), (200, 180, 255)],
}

WEAVE_PATTERNS = ["plain", "twill", "satin", "herringbone", "basket", "diamond", "hexagonal"]


def rgb_to_ansi(r, g, b):
    """Convert RGB values to a 24-bit ANSI escape code.

    Args:
        r: Red component (0-255)
        g: Green component (0-255)
        b: Blue component (0-255)

    Returns:
        ANSI escape string for the given color.
    """
    return f"\033[38;2;{int(max(0, min(255, r)))};{int(max(0, min(255, g)))};{int(max(0, min(255, b)))}m"


def blend_color(c1, c2, t):
    """Linearly interpolate between two RGB color tuples.

    Args:
        c1: Starting color as (R, G, B) tuple.
        c2: Ending color as (R, G, B) tuple.
        t: Interpolation factor (0.0 = c1, 1.0 = c2).

    Returns:
        Interpolated (R, G, B) tuple.
    """
    return (
        c1[0] + (c2[0] - c1[0]) * t,
        c1[1] + (c2[1] - c1[1]) * t,
        c1[2] + (c2[2] - c1[2]) * t,
    )


def palette_color(palette, t):
    """Get a color from a palette at position t (0.0-1.0), with smooth interpolation.

    The palette wraps around, so t values outside [0, 1] produce smooth cycling.

    Args:
        palette: List of (R, G, B) tuples forming the color gradient.
        t: Position along the palette (0.0-1.0), wraps cyclically.

    Returns:
        Interpolated (R, G, B) color tuple.
    """
    t = t % 1.0
    n = len(palette)
    idx = t * n
    i = int(idx) % n
    j = (i + 1) % n
    frac = idx - int(idx)
    return blend_color(palette[i], palette[j], frac)


def clamp(value, lo=0.0, hi=1.0):
    """Clamp a value between lo and hi."""
    return max(lo, min(hi, value))


WeaveLayer = namedtuple("WeaveLayer", ["freq_x", "freq_y", "phase_x", "phase_y", "speed", "amplitude"])


def random_layer():
    """Generate a random weave layer with randomized parameters.

    Returns:
        A WeaveLayer namedtuple with random frequency, phase, speed, and amplitude.
    """
    return WeaveLayer(
        freq_x=random.uniform(0.02, 0.15),
        freq_y=random.uniform(0.02, 0.15),
        phase_x=random.uniform(0, math.pi * 2),
        phase_y=random.uniform(0, math.pi * 2),
        speed=random.uniform(0.3, 1.5),
        amplitude=random.uniform(0.3, 1.0),
    )


class Loom:
    """A generative art loom that weaves animated patterns in the terminal.

    The Loom simulates a textile loom by layering trigonometric wave functions
    (representing warp and weft threads) to produce evolving, woven-looking
    patterns. Each frame computes an interference pattern from the layers,
    then maps values to Unicode block characters and interpolated colors.

    Attributes:
        width: Terminal width in characters.
        height: Terminal height in rows.
        palette_name: Name of the active color palette.
        pattern_name: Name of the active weave pattern.
        fps: Target frames per second for animation.
        layers: List of WeaveLayer namedtuples defining the wave composition.
    """

    def __init__(self, width=None, height=None, palette="sunset", pattern="twill",
                 layers=3, seed=None, fps=15, speed=2.0, info=False):
        """Initialize the Loom with the given parameters.

        Args:
            width: Terminal width (default: auto-detect, capped at 120).
            height: Terminal height (default: auto-detect, capped at 50).
            palette: Color palette name (must be a key in PALETTES).
            pattern: Weave pattern name (must be in WEAVE_PATTERNS).
            layers: Number of wave layers to compose (more = more complex).
            seed: Random seed for reproducibility (None = random).
            fps: Target frames per second.
            speed: Animation speed multiplier (default 2.0).
            info: Whether to display info overlay bar.
        """
        # Try to detect terminal size, fall back gracefully
        try:
            term_size = os.get_terminal_size()
            default_w = min(term_size.columns, 120)
            default_h = min(term_size.lines - 2, 50)
        except OSError:
            default_w = 80
            default_h = 24

        self.width = width or default_w
        self.height = height or default_h
        self.palette_name = palette
        if palette not in PALETTES:
            print(f"Warning: Unknown palette '{palette}', using 'sunset'.", file=sys.stderr)
            self.palette_name = "sunset"
        self.palette = PALETTES[self.palette_name]
        if pattern not in WEAVE_PATTERNS:
            print(f"Warning: Unknown pattern '{pattern}', using 'twill'.", file=sys.stderr)
            self.pattern_name = "twill"
        else:
            self.pattern_name = pattern
        if fps <= 0:
            print(f"Warning: FPS must be positive, got {fps}, using 15.", file=sys.stderr)
            fps = 15
        self.fps = fps
        self.frame_time = 1.0 / fps
        if speed <= 0:
            print(f"Warning: Speed must be positive, got {speed}, using 1.0.", file=sys.stderr)
            speed = 1.0
        self.speed = speed
        self.info = info

        # Validate dimensions
        if self.width < 10:
            print(f"Warning: width {self.width} is very small, using 10.", file=sys.stderr)
            self.width = 10
        if self.height < 5:
            print(f"Warning: height {self.height} is very small, using 5.", file=sys.stderr)
            self.height = 5

        if seed is not None:
            random.seed(seed)
        self._seed = seed

        self.layers = [random_layer() for _ in range(max(1, layers))]
        self.warp_threads = [random.uniform(0.01, 0.08) for _ in range(self.width)]
        self.weft_threads = [random.uniform(0.01, 0.08) for _ in range(self.height)]

        # Global phase offsets that slowly evolve
        self.global_phase = random.uniform(0, math.pi * 2)
        self.global_drift = random.uniform(0.1, 0.4)

    def compute_weave_value(self, x, y, t):
        """Compute the weave value at position (x, y) at time t.

        This is the core generative function — it layers multiple
        trigonometric functions to create complex interference patterns,
        then modulates with warp/weft thread parameters (like real fabric).

        Args:
            x: Column position.
            y: Row position.
            t: Time parameter for animation.

        Returns:
            Float value roughly in the range -1.5 to 1.5.
        """
        value = 0.0
        total_amplitude = 0.0

        for layer in self.layers:
            # Each layer contributes a sine wave with its own frequency, phase, and speed
            wave = math.sin(
                layer.freq_x * x + layer.phase_x + t * layer.speed
            ) * math.cos(
                layer.freq_y * y + layer.phase_y + t * layer.speed * 0.7
            )
            # Add cross terms for more complex patterns
            wave += 0.5 * math.sin(
                (layer.freq_x + layer.freq_y) * (x + y) * 0.5
                + self.global_phase + t * layer.speed * 0.3
            )
            value += wave * layer.amplitude
            total_amplitude += layer.amplitude

        if total_amplitude > 0:
            value /= total_amplitude

        # Apply warp/weft thread modulation (like real fabric)
        # Use modulo to safely handle x/y values beyond array bounds
        wx = x % len(self.warp_threads) if self.warp_threads else 0
        wy = y % len(self.weft_threads) if self.weft_threads else 0
        warp_mod = math.sin(self.warp_threads[wx] * x + t * 0.2)
        weft_mod = math.sin(self.weft_threads[wy] * y + t * 0.15)
        value = value * 0.8 + (warp_mod + weft_mod) * 0.1

        # Global drift creates slow evolution
        value += 0.1 * math.sin(self.global_drift * t + self.global_phase)

        return value  # Range roughly -1.5 to 1.5

    def value_to_char(self, value):
        """Map a weave value to a Unicode block character.

        Args:
            value: Raw weave value (roughly -1.5 to 1.5).

        Returns:
            A single Unicode block character string.
        """
        # Normalize to 0-1
        v = (value + 1.5) / 3.0
        v = clamp(v)

        if v < 0.15:
            return BLOCKS["light"]
        elif v < 0.3:
            return BLOCKS["quad_tl"]
        elif v < 0.45:
            return BLOCKS["shade2"]
        elif v < 0.55:
            return BLOCKS["medium"]
        elif v < 0.7:
            return BLOCKS["shade3"]
        elif v < 0.85:
            return BLOCKS["dark"]
        else:
            return BLOCKS["full"]

    def value_to_color_and_char(self, value, x, y, t):
        """Map a weave value to both a color and character based on pattern style.

        Args:
            value: Raw weave value.
            x: Column position.
            y: Row position.
            t: Time parameter.

        Returns:
            Tuple of (color_tuple, char_string).
        """
        # Color based on the value mapped to palette
        v = (value + 1.5) / 3.0
        v = clamp(v)
        color_t = (v + math.sin(x * 0.05 + t * 0.3) * 0.15 + math.cos(y * 0.04 + t * 0.2) * 0.15) % 1.0
        color = palette_color(self.palette, color_t)

        # Character based on pattern
        char = self._pattern_char(v, x, y, t)

        return color, char

    def _pattern_char(self, v, x, y, t):
        """Select character based on the weave pattern.

        Args:
            v: Normalized weave value (0.0-1.0).
            x: Column position.
            y: Row position.
            t: Time parameter.

        Returns:
            A single Unicode block character string.
        """
        if self.pattern_name == "plain":
            return self._plain_char(v)
        elif self.pattern_name == "twill":
            return self._twill_char(v, x, y)
        elif self.pattern_name == "satin":
            return self._satin_char(v, x, y)
        elif self.pattern_name == "herringbone":
            return self._herringbone_char(v, x, y)
        elif self.pattern_name == "basket":
            return self._basket_char(v, x, y)
        elif self.pattern_name == "diamond":
            return self._diamond_char(v, x, y, t)
        elif self.pattern_name == "hexagonal":
            return self._hexagonal_char(v, x, y, t)
        else:
            return self._twill_char(v, x, y)

    def _plain_char(self, v):
        """Plain weave — simple over-under alternation."""
        if v < 0.25:
            return BLOCKS["light"]
        elif v < 0.75:
            return BLOCKS["medium"]
        else:
            return BLOCKS["full"]

    def _twill_char(self, v, x, y):
        """Diagonal twill weave pattern."""
        diag = (x + y) % 8
        if diag < 2:
            if v < 0.3:
                return BLOCKS["light"]
            return BLOCKS["shade2"] if v < 0.6 else BLOCKS["dark"]
        elif diag < 5:
            if v > 0.7:
                return BLOCKS["full"]
            return BLOCKS["shade3"] if v > 0.4 else BLOCKS["medium"]
        else:
            if v < 0.35:
                return BLOCKS["dot"]
            return BLOCKS["shade1"] if v < 0.65 else BLOCKS["shade2"]

    def _satin_char(self, v, x, y):
        """Satin weave — scattered highlights on smooth ground."""
        highlight = ((x * 7 + y * 3) % 11) < 2
        if highlight:
            return BLOCKS["full"] if v > 0.3 else BLOCKS["shade3"]
        else:
            return BLOCKS["light"] if v < 0.6 else BLOCKS["shade2"]

    def _herringbone_char(self, v, x, y):
        """Herringbone — V-shaped pattern like classic suiting."""
        period = 16
        diag = (x + y) % period
        anti_diag = (x - y) % period
        v_pattern = (diag + anti_diag) % period
        if v_pattern < 4 or v_pattern > period - 4:
            return BLOCKS["full"] if v > 0.4 else BLOCKS["shade3"]
        return BLOCKS["light"] if v < 0.5 else BLOCKS["shade1"]

    def _basket_char(self, v, x, y):
        """Basket weave — alternating blocks of over/under."""
        bx = (x // 4) % 2
        by = (y // 2) % 2
        if bx == by:
            return BLOCKS["full"] if v > 0.3 else BLOCKS["shade3"]
        else:
            return BLOCKS["shade1"] if v < 0.5 else BLOCKS["medium"]

    def _diamond_char(self, v, x, y, t):
        """Diamond pattern with time-based subtle rotation."""
        period = 12
        cx = (x % period) - period // 2
        cy = (y % period) - period // 2
        dist = abs(cx) + abs(cy)
        if dist < 3:
            return BLOCKS["full"] if v > 0.3 else BLOCKS["shade3"]
        elif dist < 5:
            return BLOCKS["medium"] if v > 0.4 else BLOCKS["shade2"]
        else:
            return BLOCKS["light"] if v < 0.5 else BLOCKS["dot"]

    def _hexagonal_char(self, v, x, y, t):
        """Hexagonal weave — honeycomb-like structure based on axial coordinates.

        Converts (x, y) to approximate hexagonal axial coordinates,
        then uses modulo to create a repeating honeycomb tile with
        distinct border, wall, and interior characters.
        """
        # Convert to approximate hex axial coordinates
        q = (x * 2 + y) / 3.0
        r = y / 1.5
        # Hex round to nearest cell center
        rq = round(q) % 7
        rr = round(r) % 5
        # Distance from hex center determines cell type
        dq = abs(q - round(q))
        dr = abs(r - round(r))
        dist = math.sqrt(dq * dq + dr * dr)

        if dist < 0.25:
            # Interior: dense fill
            if v > 0.5:
                return BLOCKS["full"]
            return BLOCKS["shade3"] if v > 0.25 else BLOCKS["shade2"]
        elif dist < 0.5:
            # Wall region
            if v > 0.6:
                return BLOCKS["dark"]
            return BLOCKS["medium"] if v > 0.3 else BLOCKS["shade1"]
        else:
            # Border / gap between hexagons
            return BLOCKS["light"] if v < 0.4 else BLOCKS["dot"]

    def render_frame(self, t):
        """Render a single frame of the loom animation with full color.

        Args:
            t: Time parameter controlling animation state.

        Returns:
            List of strings, one per row, with ANSI color codes.
        """
        lines = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                value = self.compute_weave_value(x, y, t)
                color, char = self.value_to_color_and_char(value, x, y, t)
                row.append(f"{rgb_to_ansi(*color)}{char}")
            lines.append("".join(row))
        return lines

    def render_ascii_frame(self, t):
        """Render a frame using only ASCII characters (no colors).

        Args:
            t: Time parameter controlling animation state.

        Returns:
            List of strings, one per row, with plain ASCII characters.
        """
        ascii_chars = " .:-=+*#%@█"
        lines = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                value = self.compute_weave_value(x, y, t)
                v = (value + 1.5) / 3.0
                v = clamp(v)
                idx = int(v * (len(ascii_chars) - 1))
                row.append(ascii_chars[idx])
            lines.append("".join(row))
        return lines

    def _info_bar(self, t, fps_actual):
        """Build an info overlay bar string.

        Args:
            t: Current animation time.
            fps_actual: Measured frames per second.

        Returns:
            ANSI-formatted string for the info bar.
        """
        seed_str = str(self._seed) if self._seed is not None else "random"
        info = f" LOOM v{__version__} │ {self.palette_name} │ {self.pattern_name} │ layers={len(self.layers)} │ seed={seed_str} │ {self.width}×{self.height} │ t={t:.1f} │ {fps_actual:.0f}fps "
        # Truncate if wider than terminal
        if len(info) > self.width:
            info = info[:self.width - 1] + " "
        # Pad to width
        info = info.ljust(self.width)
        return f"\033[48;2;30;30;50m\033[38;2;200;220;255m{info}\033[0m"

    def animate(self, duration=None, ascii_mode=False):
        """Run the loom animation in the terminal.

        Renders frames in a loop, maintaining the target FPS. Handles
        terminal setup (hide cursor, clear screen) and teardown (show
        cursor, reset colors) via try/finally for clean exit on Ctrl+C.

        Args:
            duration: Maximum animation time in seconds (None = infinite).
            ascii_mode: If True, use plain ASCII characters without colors.
        """
        _running = [True]  # Use list for mutability in nested function

        def _signal_handler(signum, frame):
            _running[0] = False

        # Install signal handlers for graceful shutdown
        original_sigint = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, _signal_handler)
        original_sigterm = signal.getsignal(signal.SIGTERM) if hasattr(signal, 'SIGTERM') else None
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, _signal_handler)

        try:
            if not ascii_mode:
                # Check if terminal supports 24-bit color
                term = os.environ.get("TERM", "")
                colorterm = os.environ.get("COLORTERM", "")
                if "truecolor" not in colorterm.lower() and "256color" not in term.lower():
                    print("Note: Terminal may not support truecolor. Using ASCII mode.", file=sys.stderr)
                    ascii_mode = True

            start_time = time.time()
            t = 0.0
            frame_count = 0
            fps_actual = self.fps
            last_fps_time = start_time

            # Hide cursor
            sys.stdout.write("\033[?25l")
            sys.stdout.flush()

            # Info height offset
            info_rows = 1 if self.info else 0

            while _running[0]:
                frame_start = time.time()

                if duration is not None and t > duration:
                    break

                if ascii_mode:
                    lines = self.render_ascii_frame(t)
                else:
                    lines = self.render_frame(t)

                # Build output: move cursor to top-left and draw
                output = "\033[H" + "\n".join(lines)
                if not ascii_mode:
                    output += "\033[0m"  # Reset colors

                # Add info bar overlay if requested
                if self.info:
                    # Place info bar at bottom of pattern area
                    output += "\n" + self._info_bar(t, fps_actual)

                try:
                    sys.stdout.write(output)
                    sys.stdout.flush()
                except BrokenPipeError:
                    break

                # Advance time
                t += self.frame_time * self.speed

                # Calculate actual FPS every 30 frames
                frame_count += 1
                if frame_count % 30 == 0:
                    now = time.time()
                    elapsed = now - last_fps_time
                    if elapsed > 0:
                        fps_actual = 30.0 / elapsed
                    last_fps_time = now

                # Maintain frame rate
                frame_elapsed = time.time() - frame_start
                if frame_elapsed < self.frame_time:
                    time.sleep(self.frame_time - frame_elapsed)

        except Exception:
            raise
        finally:
            # Restore signal handlers
            signal.signal(signal.SIGINT, original_sigint)
            if hasattr(signal, 'SIGTERM') and original_sigterm is not None:
                signal.signal(signal.SIGTERM, original_sigterm)
            # Show cursor and reset colors
            sys.stdout.write("\033[?25h\033[0m")
            sys.stdout.write("\n")
            sys.stdout.flush()

    def snapshot(self, t=0.0, ascii_mode=False):
        """Render a single snapshot frame as a string.

        Args:
            t: Time parameter for the snapshot.
            ascii_mode: If True, use plain ASCII characters.

        Returns:
            String containing the rendered frame (with ANSI codes if not ASCII mode).
        """
        if ascii_mode:
            return "\n".join(self.render_ascii_frame(t))
        else:
            lines = self.render_frame(t)
            return "\n".join(lines) + "\033[0m\n"

    def save_frames(self, filename="loom_output.txt", frames=10, interval=0.5, ascii_mode=False, colored=False):
        """Save multiple frames to a text file.

        Args:
            filename: Output file path.
            frames: Number of frames to save.
            interval: Time interval between frames.
            ascii_mode: If True, use plain ASCII characters (ignores colored).
            colored: If True and not ascii_mode, include ANSI color codes in output.

        Returns:
            The filename that was written.
        """
        with open(filename, "w", encoding="utf-8") as f:
            for i in range(frames):
                t = i * interval
                f.write(f"--- Frame {i} (t={t:.1f}) ---\n")
                if ascii_mode or not colored:
                    f.write("\n".join(self.render_ascii_frame(t)))
                else:
                    f.write("\n".join(self.render_frame(t)))
                    f.write("\033[0m")
                f.write("\n\n")
        return filename

    def list_palettes(self):
        """Return a formatted string listing all available palettes."""
        lines = ["Available palettes:"]
        for name, colors in PALETTES.items():
            # Show a small color preview using ANSI codes
            preview = " ".join(f"{rgb_to_ansi(*c)}██" for c in colors) + "\033[0m"
            lines.append(f"  {name:12s} {preview}")
        return "\n".join(lines)

    def list_patterns(self):
        """Return a formatted string listing all available patterns."""
        lines = ["Available patterns:"]
        for name in WEAVE_PATTERNS:
            lines.append(f"  {name}")
        return "\n".join(lines)


def main():
    """Main entry point for the LOOM command-line tool."""
    parser = argparse.ArgumentParser(
        description="LOOM — Terminal Generative Art Weaver",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  loom.py                          # Start animation with defaults
  loom.py --palette neon           # Neon color scheme
  loom.py --pattern diamond        # Diamond weave pattern
  loom.py --seed 42 --width 80     # Reproducible, custom size
  loom.py --ascii                   # ASCII-only mode (no colors)
  loom.py --snapshot > art.txt     # Save single frame to file
  loom.py --palette aurora --layers 5   # More complex weaving
  loom.py --info                    # Show live stats overlay
  loom.py --speed 4 --fps 30       # Fast animation at 30fps
  loom.py --save output.txt         # Save 10 colored frames to file
  loom.py --save output.txt --ascii    # Save 10 ASCII frames to file

Available palettes: sunset, ocean, forest, neon, ember, aurora, monochrome, thermal, nightshade
Available patterns: plain, twill, satin, herringbone, basket, diamond, hexagonal
        """
    )

    parser.add_argument("-V", "--version", action="version", version=f"LOOM {__version__}")
    parser.add_argument("-W", "--width", type=int, help="Terminal width (default: auto-detect)")
    parser.add_argument("-H", "--height", type=int, help="Terminal height (default: auto-detect)")
    parser.add_argument("-p", "--palette", default="sunset",
                        choices=list(PALETTES.keys()), help="Color palette (default: sunset)")
    parser.add_argument("--pattern", default="twill",
                        choices=WEAVE_PATTERNS, help="Weave pattern (default: twill)")
    parser.add_argument("-l", "--layers", type=int, default=3, help="Number of weave layers (default: 3)")
    parser.add_argument("-s", "--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--fps", type=int, default=15, help="Frames per second (default: 15)")
    parser.add_argument("--speed", type=float, default=2.0, help="Animation speed multiplier (default: 2.0)")
    parser.add_argument("--ascii", action="store_true", help="ASCII-only mode (no ANSI colors)")
    parser.add_argument("--snapshot", action="store_true", help="Output a single frame and exit")
    parser.add_argument("--duration", type=float, default=None, help="Animation duration in seconds")
    parser.add_argument("--save", type=str, default=None, help="Save frames to file instead of animating")
    parser.add_argument("--save-frames", type=int, default=10, help="Number of frames to save (default: 10)")
    parser.add_argument("--save-colored", action="store_true", help="Save with ANSI color codes (default for --save; this flag is kept for backward compatibility)")
    parser.add_argument("--info", action="store_true", help="Show info overlay bar during animation")
    parser.add_argument("--list-palettes", action="store_true", help="List available palettes and exit")
    parser.add_argument("--list-patterns", action="store_true", help="List available weave patterns and exit")

    args = parser.parse_args()

    # Handle list commands
    if args.list_palettes:
        loom = Loom(width=40, height=10)
        print(loom.list_palettes())
        return

    if args.list_patterns:
        loom = Loom(width=40, height=10)
        print(loom.list_patterns())
        return

    loom = Loom(
        width=args.width,
        height=args.height,
        palette=args.palette,
        pattern=args.pattern,
        layers=args.layers,
        seed=args.seed,
        fps=args.fps,
        speed=args.speed,
        info=args.info,
    )

    if args.snapshot:
        print(loom.snapshot(t=2.0, ascii_mode=args.ascii))
    elif args.save:
        # --ascii forces plain ASCII output; otherwise use colored by default
        # --save-colored is kept for backward compatibility but is now the default
        use_ascii = args.ascii
        use_colored = not args.ascii
        filename = loom.save_frames(
            args.save,
            frames=args.save_frames,
            ascii_mode=use_ascii,
            colored=use_colored,
        )
        print(f"Saved {args.save_frames} frames to {filename}", file=sys.stderr)
    else:
        # Clear screen before starting animation
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()
        loom.animate(duration=args.duration, ascii_mode=args.ascii)


if __name__ == "__main__":
    main()