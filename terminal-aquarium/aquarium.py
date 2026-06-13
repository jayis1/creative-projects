#!/usr/bin/env python3
"""
Terminal Aquarium — A beautiful animated aquarium that lives in your terminal.
Features procedurally generated fish with unique patterns, swaying plants,
rising bubbles, ambient lighting effects, and interactive feeding.
"""

import curses
import random
import math
import time
import sys
import signal
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from collections import deque


# ─── Fish Species Database ──────────────────────────────────────────────

SPECIES = [
    {"name": "Neon Tetra",      "body": "▸", "tail": "◁", "colors": [(0, 255, 255), (255, 50, 50)], "max_size": 1.0, "speed": (0.8, 1.4), "school": True},
    {"name": "Guppy",           "body": "▸", "tail": "✿", "colors": [(255, 180, 50), (50, 200, 255)], "max_size": 0.9, "speed": (0.6, 1.2), "school": False},
    {"name": "Angelfish",       "body": "◆", "tail": "◇", "colors": [(220, 220, 255), (100, 100, 200)], "max_size": 1.8, "speed": (0.3, 0.7), "school": False},
    {"name": "Clownfish",       "body": "▸", "tail": "◁", "colors": [(255, 130, 0), (255, 255, 255)], "max_size": 1.2, "speed": (0.5, 1.0), "school": True},
    {"name": "Betta",           "body": "▸", "tail": "✾", "colors": [(180, 0, 220), (100, 0, 255)], "max_size": 1.5, "speed": (0.4, 0.8), "school": False},
    {"name": "Goldfish",        "body": "▸", "tail": "◡", "colors": [(255, 180, 0), (255, 120, 0)], "max_size": 1.3, "speed": (0.4, 0.9), "school": False},
    {"name": "Discus",          "body": "●", "tail": "○", "colors": [(255, 80, 80), (50, 200, 150)], "max_size": 1.6, "speed": (0.3, 0.6), "school": False},
    {"name": "Danio",           "body": "▸", "tail": "◁", "colors": [(200, 200, 200), (100, 100, 255)], "max_size": 0.8, "speed": (0.9, 1.5), "school": True},
    {"name": "Pufferfish",      "body": "◎", "tail": "◦", "colors": [(230, 220, 100), (80, 80, 80)], "max_size": 1.4, "speed": (0.2, 0.5), "school": False},
    {"name": "Swordtail",       "body": "▸", "tail": "➤", "colors": [(200, 50, 50), (50, 150, 50)], "max_size": 1.1, "speed": (0.5, 1.1), "school": False},
]

PLANT_TYPES = [
    {"name": "Anubias",     "chars": ["⌇", "⡇", "⣇"], "color": (40, 160, 60)},
    {"name": "Java Fern",   "chars": ["⌇", "⡇", "⣇"], "color": (30, 180, 40)},
    {"name": "Hornwort",    "chars": ["┊", "╎", "┆"], "color": (50, 200, 70)},
    {"name": "Vallisneria", "chars": ["│", "┃", "╽"], "color": (20, 140, 50)},
    {"name": "Cryptocoryne","chars": ["⌇", "⡇", "⣇"], "color": (60, 150, 40)},
]

FISH_NAMES = [
    "Bubbles", "Nemo", "Dory", "Finley", "Splash", "Coral", "Gil",
    "Ariel", "Marlin", "Pearl", "Sunny", "Goldie", "Flash", "Ripple",
    "Sparkle", "Zippy", "Glimmer", "Neptune", "Cleo", "Delta",
    "Oceana", "Finnick", "Kai", "Marina", "Reef", "Storm", "Wade",
    "Brook", "River", "Shelly", "Whiskers", "Blinky", "Echo",
    "Jewel", "Comet", "Pip", "Nerite", "Tide", "Cove", "Lagoon",
]


# ─── Helper Functions ───────────────────────────────────────────────────

def rgb_to_curses(r, g, b):
    """Convert RGB (0-255) to curses color (0-1000)."""
    return int(r * 1000 / 255), int(g * 1000 / 255), int(b * 1000 / 255)


def lerp_color(c1, c2, t):
    """Linearly interpolate between two RGB colors."""
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def darken(color, factor=0.5):
    return tuple(int(c * factor) for c in color)


# ─── Data Classes ───────────────────────────────────────────────────────

@dataclass
class Fish:
    x: float
    y: float
    species: dict
    size: float
    speed: float
    direction: int  # 1 = right, -1 = left
    color_pair: int
    name: str
    vy: float = 0.0
    wobble_phase: float = 0.0
    wobble_speed: float = 0.0
    alive: bool = True
    age: float = 0.0
    food_target: Optional[Tuple[float, float]] = None
    scared: float = 0.0  # scare timer
    body_color: tuple = (255, 255, 255)
    accent_color: tuple = (200, 200, 200)

    def __post_init__(self):
        self.wobble_phase = random.uniform(0, math.pi * 2)
        self.wobble_speed = random.uniform(2.0, 4.0)


@dataclass
class Bubble:
    x: float
    y: float
    radius: float = 1.0
    speed: float = 0.5
    wobble: float = 0.0
    wobble_phase: float = 0.0
    wobble_speed: float = 0.0
    char: str = "°"

    def __post_init__(self):
        self.wobble_phase = random.uniform(0, math.pi * 2)
        self.wobble_speed = random.uniform(1.5, 3.5)
        self.char = random.choice(["°", "˚", "∘", "○", "∙"])


@dataclass
class Plant:
    x: int
    y: int  # bottom y (root)
    plant_type: dict
    height: int
    sway_phase: float = 0.0
    sway_speed: float = 0.0

    def __post_init__(self):
        self.sway_phase = random.uniform(0, math.pi * 2)
        self.sway_speed = random.uniform(0.5, 1.5)


@dataclass
class FoodParticle:
    x: float
    y: float
    vy: float = 0.3
    vx: float = 0.0
    life: float = 15.0  # seconds before it disappears
    char: str = "●"

    def __post_init__(self):
        self.vx = random.uniform(-0.1, 0.1)


@dataclass
class Rock:
    x: int
    y: int
    width: int
    height: int
    chars: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.chars = []
        for row in range(self.height):
            line_chars = []
            for col in range(self.width):
                r = random.random()
                if r < 0.4:
                    line_chars.append("▓")
                elif r < 0.7:
                    line_chars.append("▒")
                elif r < 0.9:
                    line_chars.append("░")
                else:
                    line_chars.append("·")
            self.chars.append("".join(line_chars))


# ─── Aquarium Manager ───────────────────────────────────────────────────

class Aquarium:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        self.water_top = 3
        self.sand_height = 3
        self.fish: List[Fish] = []
        self.bubbles: List[Bubble] = []
        self.plants: List[Plant] = []
        self.food: List[FoodParticle] = []
        self.rocks: List[Rock] = []
        self.time = 0.0
        self.dt = 1.0 / 15.0
        self.frame_count = 0
        self.color_map = {}  # (r,g,b) -> color_pair number
        self.next_color_pair = 1
        self.max_colors = 256
        self.paused = False
        self.show_info = False
        self.message = ""
        self.message_timer = 0.0

        # Initialize colors
        curses.start_color()
        curses.use_default_colors()
        if not curses.can_change_color():
            # Fallback: use basic colors
            self.basic_colors = True
        else:
            self.basic_colors = False

        # Set up initial color pairs
        self._init_colors()

        # Populate aquarium
        self._create_sand()
        self._create_plants()
        self._create_rocks()
        num_fish = random.randint(8, 14)
        for i in range(num_fish):
            self._spawn_fish()

        self._show_message(f"Welcome! Press F to feed, I for info, Q to quit. {len(self.fish)} fish swimming.")

    def _init_colors(self):
        """Set up basic color pairs."""
        # Water colors
        self._register_color((20, 60, 140))   # deep water
        self._register_color((30, 80, 160))    # mid water
        self._register_color((40, 100, 180))   # light water
        # Sand
        self._register_color((194, 178, 128))  # sand
        self._register_color((170, 150, 100))   # dark sand
        # Plant
        self._register_color((40, 180, 60))
        # Fish colors - will be registered per fish
        # Bubble
        self._register_color((180, 220, 255))
        # Food
        self._register_color((255, 200, 50))
        # Info text
        self._register_color((200, 230, 255))
        # Rock
        self._register_color((100, 95, 90))

    def _register_color(self, rgb):
        """Register an RGB color and return its pair number."""
        if rgb in self.color_map:
            return self.color_map[rgb]

        if self.next_color_pair >= self.max_colors:
            # Reuse the closest existing color
            best = min(self.color_map.keys(),
                       key=lambda c: sum((a - b) ** 2 for a, b in zip(c, rgb)))
            return self.color_map[best]

        pair_num = self.next_color_pair
        r, g, b = rgb_to_curses(*rgb)

        try:
            if self.basic_colors:
                # Map to basic color
                idx = self.next_color_pair
                if idx <= 7:
                    curses.init_pair(idx, idx, -1)
                else:
                    curses.init_pair(idx, curses.COLOR_WHITE, -1)
            else:
                curses.init_color(pair_num, r, g, b)
                curses.init_pair(pair_num, pair_num, -1)
        except curses.error:
            pass

        self.color_map[rgb] = pair_num
        self.next_color_pair += 1
        return pair_num

    def _get_color(self, rgb):
        """Get color pair number for an RGB color."""
        if rgb in self.color_map:
            return self.color_map[rgb]
        return self._register_color(rgb)

    def _create_sand(self):
        """Pre-generate sand texture."""
        self.sand_rows = []
        for row in range(self.sand_height):
            line = ""
            for col in range(self.width):
                r = random.random()
                if r < 0.3:
                    line += "·"
                elif r < 0.6:
                    line += "≈"
                elif r < 0.8:
                    line += "░"
                else:
                    line += " "
            self.sand_rows.append(line)

    def _create_plants(self):
        """Place plants along the bottom."""
        num_plants = random.randint(4, min(8, self.width // 15))
        for _ in range(num_plants):
            x = random.randint(5, self.width - 5)
            pt = random.choice(PLANT_TYPES)
            h = random.randint(5, min(15, self.height // 2))
            plant = Plant(x=x, y=self.height - self.sand_height, plant_type=pt, height=h)
            self.plants.append(plant)

    def _create_rocks(self):
        """Place decorative rocks."""
        num_rocks = random.randint(2, 4)
        for _ in range(num_rocks):
            w = random.randint(3, 7)
            h = random.randint(2, 4)
            x = random.randint(2, self.width - w - 2)
            rock = Rock(x=x, y=self.height - self.sand_height - h + 1, width=w, height=h)
            self.rocks.append(rock)

    def _spawn_fish(self, x=None, y=None):
        """Spawn a new fish."""
        species = random.choice(SPECIES)
        if x is None:
            x = random.uniform(5, self.width - 5)
        if y is None:
            y = random.uniform(self.water_top + 2, self.height - self.sand_height - 3)
        direction = random.choice([-1, 1])
        speed = random.uniform(*species["speed"])
        size = random.uniform(0.7, 1.0) * species["max_size"]

        # Pick a unique-ish name
        name = random.choice(FISH_NAMES)

        # Fish color with slight variation
        c1 = species["colors"][0]
        c2 = species["colors"][1]
        variation = random.uniform(-20, 20)
        body_color = tuple(max(0, min(255, int(c + variation))) for c in c1)
        accent_color = tuple(max(0, min(255, int(c + variation))) for c in c2)

        pair = self._register_color(body_color)

        fish = Fish(
            x=x, y=y, species=species, size=size, speed=speed,
            direction=direction, color_pair=pair, name=name,
        )
        fish.body_color = body_color
        fish.accent_color = accent_color
        self.fish.append(fish)
        return fish

    def _show_message(self, msg, duration=4.0):
        self.message = msg
        self.message_timer = duration

    def _feed(self):
        """Drop food from the top."""
        num_particles = random.randint(3, 7)
        for _ in range(num_particles):
            x = random.uniform(5, self.width - 5)
            y = float(self.water_top + 1)
            food = FoodParticle(x=x, y=y)
            self.food.append(food)
        self._show_message(f"Feeding time! {len(self.food)} food particles in the water.")

    def update(self):
        """Update all aquarium entities."""
        if self.paused:
            return

        self.time += self.dt
        self.frame_count += 1

        # Update message timer
        if self.message_timer > 0:
            self.message_timer -= self.dt
            if self.message_timer <= 0:
                self.message = ""

        # Update fish
        for fish in self.fish:
            fish.age += self.dt
            fish.scared = max(0, fish.scared - self.dt)

            # Check for nearby food
            fish.food_target = None
            if self.food:
                closest = min(self.food, key=lambda f: (f.x - fish.x) ** 2 + (f.y - fish.y) ** 2)
                dist = math.sqrt((closest.x - fish.x) ** 2 + (closest.y - fish.y) ** 2)
                if dist < 20:
                    fish.food_target = (closest.x, closest.y)

            if fish.food_target:
                # Swim toward food
                tx, ty = fish.food_target
                dx = tx - fish.x
                dy = ty - fish.y
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < 1.0:
                    # Eat the food
                    self.food = [f for f in self.food if not (abs(f.x - tx) < 2 and abs(f.y - ty) < 2)]
                else:
                    fish.direction = 1 if dx > 0 else -1
                    fish.x += (dx / dist) * fish.speed * 1.5 * self.dt * 8
                    fish.y += (dy / dist) * fish.speed * 1.5 * self.dt * 8
            else:
                # Normal swimming with wobble
                fish.wobble_phase += fish.wobble_speed * self.dt

                # Gentle vertical oscillation
                fish.y += math.sin(fish.wobble_phase) * 0.02

                # Horizontal movement
                fish.x += fish.direction * fish.speed * self.dt * 4

                # Random direction changes
                if random.random() < 0.005:
                    fish.direction *= -1

                # Random vertical drift
                if random.random() < 0.02:
                    fish.vy = random.uniform(-0.3, 0.3)
                fish.y += fish.vy * self.dt * 5
                fish.vy *= 0.98

            # Boundary bouncing
            margin = 3
            if fish.x < margin:
                fish.x = margin
                fish.direction = 1
            elif fish.x > self.width - margin:
                fish.x = self.width - margin
                fish.direction = -1

            water_bottom = self.height - self.sand_height - 2
            if fish.y < self.water_top + 1:
                fish.y = self.water_top + 1
                fish.vy = abs(fish.vy)
            elif fish.y > water_bottom:
                fish.y = water_bottom
                fish.vy = -abs(fish.vy)

        # Update bubbles
        for bubble in self.bubbles:
            bubble.y -= bubble.speed * self.dt * 5
            bubble.wobble_phase += bubble.wobble_speed * self.dt
            bubble.x += math.sin(bubble.wobble_phase) * 0.03

        # Remove bubbles that reached the top
        self.bubbles = [b for b in self.bubbles if b.y > self.water_top]

        # Spawn new bubbles occasionally
        if random.random() < 0.15:
            bx = random.uniform(3, self.width - 3)
            by = self.height - self.sand_height - random.uniform(0, 5)
            b = Bubble(x=bx, y=by, radius=random.uniform(0.5, 1.5), speed=random.uniform(0.3, 0.8))
            self.bubbles.append(b)

        # Bubble from fish mouths occasionally
        if random.random() < 0.03 and self.fish:
            f = random.choice(self.fish)
            bx = f.x + f.direction * 2
            by = f.y - 0.5
            b = Bubble(x=bx, y=by, radius=random.uniform(0.3, 0.8), speed=random.uniform(0.4, 0.7))
            self.bubbles.append(b)

        # Update food
        for food in self.food:
            food.y += food.vy * self.dt * 3
            food.x += food.vx * self.dt * 3
            food.life -= self.dt
            food.vy *= 0.999  # slow down sinking
            # Slight horizontal drift
            food.vx += random.uniform(-0.02, 0.02)
            food.vx *= 0.98

        # Remove expired or eaten food
        bottom = self.height - self.sand_height
        self.food = [f for f in self.food if f.life > 0 and f.y < bottom]

        # Update plant sway
        for plant in self.plants:
            plant.sway_phase += plant.sway_speed * self.dt

    def draw(self):
        """Draw the entire aquarium."""
        self.stdscr.clear()
        h, w = self.height, self.width

        # Draw water background with depth gradient
        for y in range(self.water_top, h - self.sand_height):
            depth_factor = (y - self.water_top) / max(1, (h - self.sand_height - self.water_top))
            r = int(10 + 20 * (1 - depth_factor))
            g = int(40 + 50 * (1 - depth_factor))
            b = int(120 + 40 * (1 - depth_factor))
            # Subtle wave effect
            wave = math.sin(self.time * 0.5 + y * 0.1) * 3
            r = max(0, min(255, r + int(wave)))
            color_pair = self._get_color((r, g, b))

            try:
                self.stdscr.attron(curses.color_pair(color_pair))
                self.stdscr.addstr(y, 0, " " * w)
                self.stdscr.attroff(curses.color_pair(color_pair))
            except curses.error:
                pass

        # Draw water surface
        surface_chars = "≈∼∿≋"
        surface_pair = self._get_color((120, 180, 255))
        try:
            self.stdscr.attron(curses.color_pair(surface_pair))
            for x in range(w):
                idx = int((math.sin(self.time * 2 + x * 0.3) + 1) * 1.5) % len(surface_chars)
                try:
                    self.stdscr.addch(self.water_top, x, ord(surface_chars[idx]))
                except curses.error:
                    pass
            self.stdscr.attroff(curses.color_pair(surface_pair))
        except curses.error:
            pass

        # Draw light rays
        ray_pair = self._get_color((60, 110, 170))
        for i in range(3):
            ray_x = int((self.time * 10 + i * w / 3) % (w + 20)) - 10
            for y in range(self.water_top, h - self.sand_height, 2):
                width_ray = int(2 + (y - self.water_top) * 0.15)
                for dx in range(width_ray):
                    rx = ray_x + dx
                    if 0 <= rx < w:
                        depth = (y - self.water_top) / max(1, h - self.sand_height - self.water_top)
                        alpha = 0.15 * (1 - depth * 0.7)
                        if alpha > 0.02:
                            try:
                                self.stdscr.attron(curses.color_pair(ray_pair) | curses.A_DIM)
                                existing = self.stdscr.inch(y, rx) & 0xFF
                                if existing == ord(' ') or existing == 0:
                                    self.stdscr.addch(y, rx, ord('·'))
                                self.stdscr.attroff(curses.color_pair(ray_pair) | curses.A_DIM)
                            except curses.error:
                                pass

        # Draw rocks
        rock_pair = self._get_color((100, 95, 90))
        for rock in self.rocks:
            for ry, row in enumerate(rock.chars):
                for rx, ch in enumerate(row):
                    draw_x = rock.x + rx
                    draw_y = rock.y + ry
                    if 0 <= draw_x < w and 0 <= draw_y < h:
                        try:
                            self.stdscr.attron(curses.color_pair(rock_pair))
                            self.stdscr.addch(draw_y, draw_x, ord(ch))
                            self.stdscr.attroff(curses.color_pair(rock_pair))
                        except curses.error:
                            pass

        # Draw plants
        for plant in self.plants:
            sway = math.sin(plant.sway_phase + self.time * plant.sway_speed) * 2
            color_pair = self._get_color(plant.plant_type["color"])
            dark_color = darken(plant.plant_type["color"], 0.6)
            dark_pair = self._get_color(dark_color)

            for seg in range(plant.height):
                seg_sway = sway * (seg / plant.height) * 1.5
                draw_x = int(plant.x + seg_sway)
                draw_y = plant.y - seg

                if 0 <= draw_x < w and self.water_top < draw_y < h - self.sand_height:
                    char_idx = min(seg % len(plant.plant_type["chars"]), len(plant.plant_type["chars"]) - 1)
                    ch = plant.plant_type["chars"][char_idx]
                    use_pair = dark_pair if seg > plant.height * 0.6 else color_pair
                    try:
                        self.stdscr.attron(curses.color_pair(use_pair))
                        self.stdscr.addch(draw_y, draw_x, ord(ch))
                        self.stdscr.attroff(curses.color_pair(use_pair))
                    except curses.error:
                        pass

                # Leaf segments
                if seg > 2 and seg % 3 == 0:
                    for leaf_dir in [-1, 1]:
                        lx = draw_x + leaf_dir * 2
                        ly = draw_y
                        if 0 <= lx < w and self.water_top < ly < h - self.sand_height:
                            leaf_pair = dark_pair if seg > plant.height * 0.6 else color_pair
                            try:
                                self.stdscr.attron(curses.color_pair(leaf_pair))
                                self.stdscr.addch(ly, lx, ord("⌇"))
                                self.stdscr.attroff(curses.color_pair(leaf_pair))
                            except curses.error:
                                pass

        # Draw sand
        sand_pair = self._get_color((194, 178, 128))
        dark_sand_pair = self._get_color((170, 150, 100))
        for row_idx, y_pos in enumerate(range(h - self.sand_height, h)):
            use_pair = dark_sand_pair if row_idx > 1 else sand_pair
            try:
                self.stdscr.attron(curses.color_pair(use_pair))
                self.stdscr.addstr(y_pos, 0, self.sand_rows[row_idx] if row_idx < len(self.sand_rows) else " " * w)
                self.stdscr.attroff(curses.color_pair(use_pair))
            except curses.error:
                pass

        # Draw food
        food_pair = self._get_color((255, 200, 50))
        for food in self.food:
            ix, iy = int(food.x), int(food.y)
            if 0 <= ix < w and self.water_top < iy < h - self.sand_height:
                # Twinkle effect
                ch = "●" if int(self.time * 4) % 3 != 0 else "◉"
                try:
                    self.stdscr.attron(curses.color_pair(food_pair) | curses.A_BOLD)
                    self.stdscr.addch(iy, ix, ord(ch))
                    self.stdscr.attroff(curses.color_pair(food_pair) | curses.A_BOLD)
                except curses.error:
                    pass

        # Draw bubbles
        bubble_pair = self._get_color((180, 220, 255))
        for bubble in self.bubbles:
            ix, iy = int(bubble.x), int(bubble.y)
            if 0 <= ix < w and self.water_top < iy < h - self.sand_height:
                try:
                    self.stdscr.attron(curses.color_pair(bubble_pair))
                    self.stdscr.addch(iy, ix, ord(bubble.char))
                    self.stdscr.attroff(curses.color_pair(bubble_pair))
                except curses.error:
                    pass

        # Draw fish
        for fish in self.fish:
            self._draw_fish(fish)

        # Draw info bar
        self._draw_info_bar()

        # Draw message
        if self.message:
            self._draw_message()

        self.stdscr.refresh()

    def _draw_fish(self, fish: Fish):
        """Draw a single fish."""
        ix, iy = int(fish.x), int(fish.y)
        d = fish.direction
        pair = fish.color_pair

        size = fish.size

        # Body
        body_char = fish.species["body"] if d == 1 else fish.species["body"].replace("▸", "◂")
        if body_char == "◂":
            body_char = "◂"
        else:
            body_char = fish.species["body"]

        # Build fish appearance based on size
        tail_char = fish.species["tail"]

        # Determine positions
        dorsal_pos = None
        if d == 1:  # facing right
            positions = [
                (ix - 2, iy, tail_char),
                (ix - 1, iy, body_char),
                (ix, iy, "►" if size > 1.0 else "▸"),
            ]
            # Eye
            eye_pos = (ix + 1, iy)
            # Dorsal fin
            if size > 0.8:
                dorsal_pos = (ix - 1, iy - 1)
        else:  # facing left
            positions = [
                (ix + 2, iy, tail_char),
                (ix + 1, iy, body_char),
                (ix, iy, "◄" if size > 1.0 else "◂"),
            ]
            eye_pos = (ix - 1, iy)
            if size > 0.8:
                dorsal_pos = (ix + 1, iy - 1)

        # Draw main body
        try:
            self.stdscr.attron(curses.color_pair(pair) | curses.A_BOLD)
            for px, py, ch in positions:
                if 0 <= px < self.width and self.water_top < py < self.height - self.sand_height:
                    try:
                        self.stdscr.addch(py, px, ord(ch))
                    except (curses.error, ValueError):
                        pass
            self.stdscr.attroff(curses.color_pair(pair) | curses.A_BOLD)
        except curses.error:
            pass

        # Draw eye
        eye_pair = self._get_color((255, 255, 255))
        ex, ey = eye_pos
        if 0 <= ex < self.width and self.water_top < ey < self.height - self.sand_height:
            try:
                self.stdscr.attron(curses.color_pair(eye_pair) | curses.A_BOLD)
                self.stdscr.addch(ey, ex, ord("•"))
                self.stdscr.attroff(curses.color_pair(eye_pair) | curses.A_BOLD)
            except curses.error:
                pass

        # Draw dorsal fin for larger fish
        if size > 0.8 and dorsal_pos is not None:
            fin_pair = self._get_color(fish.accent_color)
            dx, dy = dorsal_pos
            if 0 <= dx < self.width and self.water_top < dy < self.height - self.sand_height:
                try:
                    self.stdscr.attron(curses.color_pair(fin_pair))
                    self.stdscr.addch(dy, dx, ord("▲"))
                    self.stdscr.attroff(curses.color_pair(fin_pair))
                except curses.error:
                    pass

    def _draw_info_bar(self):
        """Draw top info bar."""
        info_pair = self._get_color((200, 230, 255))
        try:
            self.stdscr.attron(curses.color_pair(info_pair))

            # Title
            title = f" 🐠 Terminal Aquarium 🐟 "
            bar_left = f" Fish: {len(self.fish)} │ Bubbles: {len(self.bubbles)} │ Food: {len(self.food)} │ Time: {self.time:.0f}s "
            bar_right = " [F]eed  [I]nfo  [P]ause  [Q]uit "

            self.stdscr.addstr(0, 0, title[:self.width])
            self.stdscr.addstr(1, 0, bar_left[:self.width])
            remaining = self.width - len(bar_left)
            if remaining > 0:
                self.stdscr.addstr(1, min(len(bar_left), self.width - 1), bar_right[:max(0, remaining)])
            self.stdscr.attroff(curses.color_pair(info_pair))
        except curses.error:
            pass

        if self.show_info:
            try:
                y_start = 2
                self.stdscr.attron(curses.color_pair(info_pair))
                info_lines = ["─── Aquarium Residents ───"]
                for i, fish in enumerate(self.fish[:10]):
                    info_lines.append(f"  {fish.name:10s} ({fish.species['name']:12s}) size={fish.size:.1f} speed={fish.speed:.1f}")
                if len(self.fish) > 10:
                    info_lines.append(f"  ... and {len(self.fish) - 10} more")
                self.stdscr.attroff(curses.color_pair(info_pair))

                for i, line in enumerate(info_lines):
                    if y_start + i < self.water_top:
                        continue
                    # Show in water area briefly
                    if y_start + i < self.height - self.sand_height:
                        try:
                            self.stdscr.attron(curses.color_pair(info_pair) | curses.A_REVERSE)
                            self.stdscr.addstr(y_start + i, 2, line[:self.width - 4])
                            self.stdscr.attroff(curses.color_pair(info_pair) | curses.A_REVERSE)
                        except curses.error:
                            pass
            except curses.error:
                pass

    def _draw_message(self):
        """Draw a centered message at the top."""
        if not self.message:
            return
        msg_pair = self._get_color((255, 255, 200))
        x = max(0, (self.width - len(self.message)) // 2)
        y = self.water_top + 1
        try:
            self.stdscr.attron(curses.color_pair(msg_pair) | curses.A_BOLD)
            self.stdscr.addstr(y, x, self.message[:self.width - x])
            self.stdscr.attroff(curses.color_pair(msg_pair) | curses.A_BOLD)
        except curses.error:
            pass

    def handle_input(self, key):
        """Handle keyboard input."""
        if key == ord('q') or key == ord('Q'):
            return False
        elif key == ord('f') or key == ord('F'):
            self._feed()
        elif key == ord('i') or key == ord('I'):
            self.show_info = not self.show_info
        elif key == ord('p') or key == ord('P'):
            self.paused = not self.paused
            self._show_message("Paused" if self.paused else "Resumed", 2.0)
        elif key == ord('s') or key == ord('S'):
            # Spawn a new fish
            self._spawn_fish()
            self._show_message(f"A new fish appears! Total: {len(self.fish)}")
        elif key == ord('b') or key == ord('B'):
            # Burst of bubbles
            for _ in range(random.randint(5, 15)):
                bx = random.uniform(5, self.width - 5)
                by = self.height - self.sand_height - random.uniform(1, 5)
                b = Bubble(x=bx, y=by, radius=random.uniform(0.5, 2.0), speed=random.uniform(0.5, 1.2))
                self.bubbles.append(b)
        elif key == ord('r') or key == ord('R'):
            # Scare all fish
            for fish in self.fish:
                fish.direction = 1 if fish.x < self.width / 2 else -1
                fish.scared = 3.0
            self._show_message("Splash! The fish scatter!", 2.0)
        return True


def main(stdscr):
    """Main aquarium loop."""
    curses.curs_set(0)  # Hide cursor
    stdscr.nodelay(True)  # Non-blocking input
    stdscr.timeout(66)  # ~15 FPS

    aquarium = Aquarium(stdscr)

    running = True
    while running:
        # Handle input
        try:
            key = stdscr.getch()
            if key != -1:
                if not aquarium.handle_input(key):
                    break
        except curses.error:
            pass

        # Update
        aquarium.update()

        # Draw
        aquarium.draw()

    # Cleanup
    curses.curs_set(1)


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass