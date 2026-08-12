"""Renderers for boids simulation: ASCII, SVG, PPM, and TrailSVG (no external deps).

Enhanced v2.0: TrailSVGRenderer draws boid paths with fading,
PPM and SVG renderers use config colors.
"""

from __future__ import annotations
import math
from typing import Optional
from boids.simulation import BoidSimulation


class ASCIIRenderer:
    """Render a single frame as ASCII art to a string.

    Maps boid positions to a character grid and draws boids as arrows
    pointing in their velocity direction.
    """

    def __init__(self, cols: int = 80, rows: int = 24):
        self.cols = cols
        self.rows = rows

    def render(self, sim: BoidSimulation) -> str:
        w, h = sim.config.width, sim.config.height
        grid = [[" "] * self.cols for _ in range(self.rows)]

        # draw obstacles as '#' circles
        for obs in sim.obstacles:
            cx = int(obs.pos.x / w * self.cols)
            cy = int(obs.pos.y / h * self.rows)
            r = max(1, int(obs.radius / w * self.cols))
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if dx * dx + dy * dy <= r * r:
                        px, py = cx + dx, cy + dy
                        if 0 <= px < self.cols and 0 <= py < self.rows:
                            grid[py][px] = "#"

        # draw goal as '*'
        if sim.goal:
            gx = int(sim.goal.x / w * self.cols)
            gy = int(sim.goal.y / h * self.rows)
            if 0 <= gx < self.cols and 0 <= gy < self.rows:
                grid[gy][gx] = "*"

        # draw predators as 'X'
        for pred in sim.predators:
            px = int(pred.pos.x / w * self.cols)
            py = int(pred.pos.y / h * self.rows)
            if 0 <= px < self.cols and 0 <= py < self.rows:
                grid[py][px] = "X"

        # draw boids as directional arrows (8 directions)
        dir_arrows = ["→", "↗", "↑", "↖", "←", "↙", "↓", "↘"]
        for b in sim.boids:
            bx = int(b.pos.x / w * self.cols)
            by = int(b.pos.y / h * self.rows)
            if 0 <= bx < self.cols and 0 <= by < self.rows:
                angle = b.vel.angle
                idx = int((angle / (math.pi / 4)) + 0.5) % 8
                grid[by][bx] = dir_arrows[idx]

        lines = ["".join(row) for row in grid]
        return "\n".join(lines)


class SVGRenderer:
    """Render a frame as an SVG string with configurable colors."""

    def render(
        self,
        sim: BoidSimulation,
        filename: Optional[str] = None,
    ) -> str:
        w, h = sim.config.width, sim.config.height
        cfg = sim.config
        parts: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}">'
        ]
        parts.append(f'<rect width="{w}" height="{h}" fill="{cfg.background_color}"/>')

        # obstacles
        for obs in sim.obstacles:
            parts.append(
                f'<circle cx="{obs.pos.x:.1f}" cy="{obs.pos.y:.1f}" '
                f'r="{obs.radius:.1f}" fill="{cfg.obstacle_color}" '
                f'sroke="{cfg.obstacle_color}" opacity="0.7"/>'
            )

        # goal
        if sim.goal:
            parts.append(
                f'<circle cx="{sim.goal.x:.1f}" cy="{sim.goal.y:.1f}" '
                f'r="8" fill="{cfg.goal_color}" opacity="0.6"/>'
            )

        # boids as small triangles
        for b in sim.boids:
            angle = b.vel.angle
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            # triangle pointing in direction of velocity
            tip = (b.pos.x + cos_a * b.radius * 2, b.pos.y + sin_a * b.radius * 2)
            left = (
                b.pos.x + math.cos(angle + 2.5) * b.radius,
                b.pos.y + math.sin(angle + 2.5) * b.radius,
            )
            right = (
                b.pos.x + math.cos(angle - 2.5) * b.radius,
                b.pos.y + math.sin(angle - 2.5) * b.radius,
            )
            pts = f"{tip[0]:.1f},{tip[1]:.1f} {left[0]:.1f},{left[1]:.1f} {right[0]:.1f},{right[1]:.1f}"
            parts.append(
                f'<polygon points="{pts}" fill="{cfg.boid_color}" opacity="0.8"/>'
            )

        # predators in red
        for p in sim.predators:
            angle = p.vel.angle
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            tip = (p.pos.x + cos_a * p.radius * 3, p.pos.y + sin_a * p.radius * 3)
            left = (
                p.pos.x + math.cos(angle + 2.5) * p.radius * 1.5,
                p.pos.y + math.sin(angle + 2.5) * p.radius * 1.5,
            )
            right = (
                p.pos.x + math.cos(angle - 2.5) * p.radius * 1.5,
                p.pos.y + math.sin(angle - 2.5) * p.radius * 1.5,
            )
            pts = f"{tip[0]:.1f},{tip[1]:.1f} {left[0]:.1f},{left[1]:.1f} {right[0]:.1f},{right[1]:.1f}"
            parts.append(
                f'<polygon points="{pts}" fill="{cfg.predator_color}" opacity="0.9"/>'
            )

        parts.append("</svg>")
        svg = "\n".join(parts)
        if filename:
            with open(filename, "w") as f:
                f.write(svg)
        return svg


class TrailSVGRenderer:
    """SVG renderer that also draws boid trails with fading opacity.

    Useful for visualizing movement paths over time.
    """

    def render(
        self,
        sim: BoidSimulation,
        filename: Optional[str] = None,
    ) -> str:
        w, h = sim.config.width, sim.config.height
        cfg = sim.config
        parts: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}">'
        ]
        parts.append(f'<rect width="{w}" height="{h}" fill="{cfg.background_color}"/>')

        # draw trails with fading opacity
        for b in sim.boids:
            if b.trail and len(b.trail) > 1:
                trail_list = list(b.trail)
                n = len(trail_list)
                for i in range(1, n):
                    opacity = (i / n) * 0.5
                    x1, y1 = trail_list[i - 1]
                    x2, y2 = trail_list[i]
                    parts.append(
                        f'<line x1="{x1:.1f}" y1="{y1:.1f}" '
                        f'x2="{x2:.1f}" y2="{y2:.1f}" '
                        f'stroke="{cfg.boid_color}" stroke-width="1" '
                        f'opacity="{opacity:.2f}"/>'
                    )

        # draw boid triangles (reuse SVGRenderer logic)
        for b in sim.boids:
            angle = b.vel.angle
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            tip = (b.pos.x + cos_a * b.radius * 2, b.pos.y + sin_a * b.radius * 2)
            left = (
                b.pos.x + math.cos(angle + 2.5) * b.radius,
                b.pos.y + math.sin(angle + 2.5) * b.radius,
            )
            right = (
                b.pos.x + math.cos(angle - 2.5) * b.radius,
                b.pos.y + math.sin(angle - 2.5) * b.radius,
            )
            pts = f"{tip[0]:.1f},{tip[1]:.1f} {left[0]:.1f},{left[1]:.1f} {right[0]:.1f},{right[1]:.1f}"
            parts.append(
                f'<polygon points="{pts}" fill="{cfg.boid_color}" opacity="0.8"/>'
            )

        # predators
        for p in sim.predators:
            # predator trail
            if p.trail and len(p.trail) > 1:
                trail_list = list(p.trail)
                n = len(trail_list)
                for i in range(1, n):
                    opacity = (i / n) * 0.5
                    x1, y1 = trail_list[i - 1]
                    x2, y2 = trail_list[i]
                    parts.append(
                        f'<line x1="{x1:.1f}" y1="{y1:.1f}" '
                        f'x2="{x2:.1f}" y2="{y2:.1f}" '
                        f'stroke="{cfg.predator_color}" stroke-width="2" '
                        f'opacity="{opacity:.2f}"/>'
                    )
            angle = p.vel.angle
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            tip = (p.pos.x + cos_a * p.radius * 3, p.pos.y + sin_a * p.radius * 3)
            left = (
                p.pos.x + math.cos(angle + 2.5) * p.radius * 1.5,
                p.pos.y + math.sin(angle + 2.5) * p.radius * 1.5,
            )
            right = (
                p.pos.x + math.cos(angle - 2.5) * p.radius * 1.5,
                p.pos.y + math.sin(angle - 2.5) * p.radius * 1.5,
            )
            pts = f"{tip[0]:.1f},{tip[1]:.1f} {left[0]:.1f},{left[1]:.1f} {right[0]:.1f},{right[1]:.1f}"
            parts.append(
                f'<polygon points="{pts}" fill="{cfg.predator_color}" opacity="0.9"/>'
            )

        # obstacles
        for obs in sim.obstacles:
            parts.append(
                f'<circle cx="{obs.pos.x:.1f}" cy="{obs.pos.y:.1f}" '
                f'r="{obs.radius:.1f}" fill="{cfg.obstacle_color}" opacity="0.7"/>'
            )

        parts.append("</svg>")
        svg = "\n".join(parts)
        if filename:
            with open(filename, "w") as f:
                f.write(svg)
        return svg


class PPMRenderer:
    """Render a frame as a PPM (P6 binary) image — no external dependencies.

    Enhanced v2.0: uses config colors.
    """

    def _parse_color(self, hex_color: str) -> tuple[int, int, int]:
        """Parse '#RRGGBB' to (r, g, b) tuple."""
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    def render(
        self,
        sim: BoidSimulation,
        filename: str,
        scale: float = 1.0,
    ) -> None:
        w = int(sim.config.width * scale)
        h = int(sim.config.height * scale)
        cfg = sim.config

        bg = self._parse_color(cfg.background_color)
        boid_col = self._parse_color(cfg.boid_color)
        pred_col = self._parse_color(cfg.predator_color)
        obs_col = self._parse_color(cfg.obstacle_color)
        goal_col = self._parse_color(cfg.goal_color)

        pixels = bytearray([bg[0], bg[1], bg[2]] * (w * h))

        def put_pixel(px: int, py: int, color: tuple[int, int, int]) -> None:
            if 0 <= px < w and 0 <= py < h:
                idx = (py * w + px) * 3
                pixels[idx] = color[0]
                pixels[idx + 1] = color[1]
                pixels[idx + 2] = color[2]

        # obstacles
        for obs in sim.obstacles:
            cx = int(obs.pos.x * scale)
            cy = int(obs.pos.y * scale)
            r = max(1, int(obs.radius * scale))
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if dx * dx + dy * dy <= r * r:
                        put_pixel(cx + dx, cy + dy, obs_col)

        # goal
        if sim.goal:
            gx = int(sim.goal.x * scale)
            gy = int(sim.goal.y * scale)
            for dy in range(-5, 6):
                for dx in range(-5, 6):
                    if dx * dx + dy * dy <= 25:
                        put_pixel(gx + dx, gy + dy, goal_col)

        # boids
        for b in sim.boids:
            bx = int(b.pos.x * scale)
            by = int(b.pos.y * scale)
            r = max(1, int(b.radius * scale))
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if dx * dx + dy * dy <= r * r:
                        put_pixel(bx + dx, by + dy, boid_col)

        # predators
        for p in sim.predators:
            px = int(p.pos.x * scale)
            py = int(p.pos.y * scale)
            r = max(2, int(p.radius * scale))
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if dx * dx + dy * dy <= r * r:
                        put_pixel(px + dx, py + dy, pred_col)

        with open(filename, "wb") as f:
            f.write(f"P6\n{w} {h}\n255\n".encode())
            f.write(bytes(pixels))