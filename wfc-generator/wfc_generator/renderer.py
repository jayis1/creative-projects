"""Multi-format renderer for WFC output grids.

Renders a 2D grid of tile names (or symbols) to ANSI-colored terminal output,
plain text, an HTML table, an SVG image, or a PNG image (requires Pillow).
"""

from __future__ import annotations

import io
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class Renderer:
    """Render WFC output grids in various formats.

    The class maps tile names (or single-character aliases) to display
    symbols, ANSI color codes, and HTML colors.  Subclass and override the
    class-level maps to customize appearance.
    """

    # ANSI color codes for common tile types
    COLOR_MAP = {
        "deep_water": "\033[44m",   "shallow_water": "\033[46m",
        "water": "\033[44m",        "land": "\033[42m",
        "forest": "\033[32m",       "mountain": "\033[37m",
        "snow": "\033[47m",         "sand": "\033[43m",
        "grass": "\033[42m",        "hill": "\033[33m",
        "road": "\033[40m",         "road_h": "\033[40m",
        "road_v": "\033[40m",       "building": "\033[41m",
        "park": "\033[42m",         "sidewalk": "\033[47m",
        "parking": "\033[43m",      "intersection": "\033[40m",
        "floor": "\033[40m",        "wall": "\033[37m",
        "corridor": "\033[44m",     "door": "\033[43m",
        "pillar": "\033[33m",       "stairs": "\033[46m",
        "treasure": "\033[41m",     "empty": "\033[48m\033[38m",
        "wire_h": "\033[32m",       "wire_v": "\033[32m",
        "wire_ne": "\033[32m",      "wire_nw": "\033[32m",
        "wire_se": "\033[32m",      "wire_sw": "\033[32m",
        "junction": "\033[31m",     "component": "\033[33m",
        "via": "\033[36m",
        # New tiles
        "water_lily": "\033[45m",   "bridge": "\033[43m",
        "tree": "\033[32m",         "flower": "\033[45m",
        "fountain": "\033[46m",     "market": "\033[41m",
        "tower": "\033[41m",        "gate": "\033[43m",
        "path": "\033[33m",         "dead_end": "\033[31m",
        "lava": "\033[41m",         "ash": "\033[37m",
        "ice": "\033[46m",          "tundra": "\033[47m",
        # Single char aliases
        "~": "\033[44m",   ".": "\033[43m",   "#": "\033[42m",
        "T": "\033[32m",   "^": "\033[37m",   " ": "\033[47m",
        "R": "\033[40m",   "B": "\033[41m",   "g": "\033[42m",
        "h": "\033[33m",
    }

    RESET = "\033[0m"

    SYMBOL_MAP = {
        "deep_water": "~",     "shallow_water": "~",
        "water": "~",          "land": "#",
        "forest": "T",         "mountain": "^",
        "snow": " ",           "sand": ".",
        "grass": "g",          "hill": "h",
        "road": "R",           "road_h": "-",
        "road_v": "|",         "building": "B",
        "park": "P",           "sidewalk": "s",
        "parking": "p",        "intersection": "+",
        "floor": ".",          "wall": "#",
        "corridor": "=",        "door": "D",
        "pillar": "o",         "stairs": ">",
        "treasure": "$",       "empty": " ",
        "wire_h": "-",         "wire_v": "|",
        "wire_ne": "└",        "wire_nw": "┘",
        "wire_se": "┌",        "wire_sw": "┐",
        "junction": "+",       "component": "■",
        "via": "⊙",
        # New tiles
        "water_lily": "l",     "bridge": "=",
        "tree": "♣",           "flower": "✿",
        "fountain": "f",       "market": "M",
        "tower": "i",          "gate": "G",
        "path": ".",            "dead_end": "D",
        "lava": "L",            "ash": "a",
        "ice": "I",            "tundra": "t",
        # Single char aliases
        "~": "~",   ".": ".",   "#": "#",
        "T": "T",   "^": "^",   " ": " ",
        "R": "R",   "B": "B",   "g": "g",
        "h": "h",
    }

    # HTML colors for all tile types
    HTML_COLOR_MAP = {
        "deep_water": "#1a5276",   "shallow_water": "#5dade2",
        "water": "#4488cc",        "land": "#88cc44",
        "forest": "#336622",       "mountain": "#888888",
        "snow": "#ffffff",         "sand": "#ccaa44",
        "grass": "#7dce6e",        "hill": "#c4a63d",
        "road": "#444444",         "road_h": "#555555",
        "road_v": "#555555",       "building": "#cc4444",
        "park": "#66aa44",         "sidewalk": "#bbbbbb",
        "parking": "#999966",      "intersection": "#666666",
        "floor": "#443322",        "wall": "#888877",
        "corridor": "#665544",     "door": "#ccaa44",
        "pillar": "#888888",       "stairs": "#55aacc",
        "treasure": "#ffcc00",     "empty": "#1a1a1a",
        "wire_h": "#33cc33",       "wire_v": "#33cc33",
        "wire_ne": "#33cc33",      "wire_nw": "#33cc33",
        "wire_se": "#33cc33",      "wire_sw": "#33cc33",
        "junction": "#cc3333",     "component": "#ccaa33",
        "via": "#33cccc",
        # New tiles
        "water_lily": "#c39bd3",   "bridge": "#d4a017",
        "tree": "#2e7d32",        "flower": "#e91e63",
        "fountain": "#4fc3f7",    "market": "#d84315",
        "tower": "#8e0000",       "gate": "#bf8f00",
        "path": "#a1887f",        "dead_end": "#a0522d",
        "lava": "#d84315",        "ash": "#bdbdbd",
        "ice": "#81d4fa",         "tundra": "#eceff1",
        "~": "#4488cc",   ".": "#ccaa44",   "#": "#88cc44",
        "T": "#336622",   "^": "#888888",   " ": "#ffffff",
        "R": "#444444",   "B": "#cc4444",   "g": "#7dce6e",
        "h": "#c4a63d",
    }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @classmethod
    def _get_symbol(cls, cell: str) -> str:
        return cls.SYMBOL_MAP.get(cell, str(cell)[0] if cell else "?")

    @classmethod
    def _get_color(cls, cell: str) -> str:
        return cls.COLOR_MAP.get(cell, "")

    @classmethod
    def _get_html_color(cls, cell: str) -> str:
        return cls.HTML_COLOR_MAP.get(cell, "#cccccc")

    # ------------------------------------------------------------------ #
    # Renderers
    # ------------------------------------------------------------------ #
    @classmethod
    def render_colored(cls, grid: List[List[str]]) -> str:
        """Render a grid with ANSI colors."""
        lines: List[str] = []
        for row in grid:
            line = ""
            for cell in row:
                color = cls._get_color(cell)
                symbol = cls._get_symbol(cell)
                line += f"{color}{symbol}{cls.RESET}"
            lines.append(line)
        return "\n".join(lines)

    @classmethod
    def render_plain(cls, grid: List[List[str]]) -> str:
        """Render a grid as plain text."""
        lines: List[str] = []
        for row in grid:
            line = ""
            for cell in row:
                line += cls._get_symbol(cell)
            lines.append(line)
        return "\n".join(lines)

    @classmethod
    def render_html(
        cls, grid: List[List[str]], cell_size: int = 16, title: str = "WFC Output"
    ) -> str:
        """Render a grid as an HTML page with colored cells."""
        html = '<!DOCTYPE html>\n<html><head>\n'
        html += f'<title>{title}</title>\n'
        html += '<style>\n'
        html += '  body { background: #1a1a2e; color: #eee; font-family: monospace; padding: 20px; }\n'
        html += f'  td {{ width: {cell_size}px; height: {cell_size}px; text-align: center; font-size: {max(8, cell_size//2)}px; }}\n'
        html += '  table { border-collapse: collapse; }\n'
        html += '  h1 { color: #e0e0e0; }\n'
        html += '</style>\n</head>\n<body>\n'
        html += f'<h1>{title}</h1>\n'
        html += f'<p>Grid: {len(grid[0]) if grid else 0}x{len(grid)}</p>\n'
        html += '<table>\n'
        for row in grid:
            html += '<tr>'
            for cell in row:
                color = cls._get_html_color(cell)
                symbol = cls._get_symbol(cell)
                html += f'<td style="background-color: {color};" title="{cell}">{symbol}</td>'
            html += '</tr>\n'
        html += '</table>\n</body>\n</html>'
        return html

    @classmethod
    def render_svg(
        cls, grid: List[List[str]], cell_size: int = 20, title: str = "WFC Output"
    ) -> str:
        """Render a grid as an SVG image with colored cells."""
        if not grid:
            return '<svg xmlns="http://www.w3.org/2000/svg"></svg>'
        height = len(grid)
        width = len(grid[0]) if grid else 0
        svg_width = width * cell_size
        svg_height = height * cell_size
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{svg_width}" height="{svg_height}" '
            f'viewBox="0 0 {svg_width} {svg_height}">',
            f'<title>{title}</title>',
            '<rect width="100%" height="100%" fill="#1a1a2e"/>',
        ]
        for y, row in enumerate(grid):
            for x, cell in enumerate(row):
                color = cls._get_html_color(cell)
                symbol = cls._get_symbol(cell)
                cx = x * cell_size
                cy = y * cell_size
                lines.append(
                    f'  <rect x="{cx}" y="{cy}" width="{cell_size}" '
                    f'height="{cell_size}" fill="{color}"/>'
                )
                if cell_size >= 12:
                    font_size = max(8, cell_size * 0.55)
                    lines.append(
                        f'  <text x="{cx + cell_size//2}" '
                        f'y="{cy + cell_size//2 + int(font_size*0.35)}" '
                        f'text-anchor="middle" font-size="{font_size:.0f}" '
                        f'fill="#fff" font-family="monospace">{symbol}</text>'
                    )
        lines.append('</svg>')
        return '\n'.join(lines)

    @classmethod
    def render_png(
        cls, grid: List[List[str]], cell_size: int = 16, title: str = "WFC Output"
    ) -> Optional[bytes]:
        """Render a grid as PNG bytes (requires Pillow).  Returns ``None`` if unavailable."""
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            logger.warning("Pillow not installed. Install with: pip install Pillow")
            return None

        if not grid:
            return None
        height = len(grid)
        width = len(grid[0])
        img_width = width * cell_size
        img_height = height * cell_size
        img = Image.new("RGB", (img_width, img_height), (26, 26, 46))
        draw = ImageDraw.Draw(img)

        for y, row in enumerate(grid):
            for x, cell in enumerate(row):
                color_hex = cls._get_html_color(cell)
                r = int(color_hex[1:3], 16)
                g = int(color_hex[3:5], 16)
                b = int(color_hex[5:7], 16)
                x0, y0 = x * cell_size, y * cell_size
                draw.rectangle(
                    [x0, y0, x0 + cell_size - 1, y0 + cell_size - 1], fill=(r, g, b)
                )
                if cell_size >= 14:
                    symbol = cls._get_symbol(cell)
                    try:
                        font = ImageFont.truetype(
                            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                            max(8, cell_size // 2),
                        )
                    except (OSError, IOError):
                        font = ImageFont.load_default()
                    draw.text(
                        (x0 + cell_size // 2, y0 + cell_size // 2),
                        symbol,
                        fill=(255, 255, 255),
                        font=font,
                        anchor="mm",
                    )
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()