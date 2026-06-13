#!/usr/bin/env python3
"""
CellLab — Interactive Cellular Automata Laboratory
Explore 1D elementary automata and 2D Game of Life variants in the terminal.
"""

import argparse
import curses
import math
import random
import sys
import time
from enum import Enum
from typing import List, Tuple


# ─── Color Palette ───────────────────────────────────────────────────────────

class Palette:
    """Color indices for curses."""
    DEAD = 0
    ALIVE = 1
    GRID = 2
    BORN = 3
    DYING = 4
    HEADER = 5
    AGE_COLORS = [6, 7, 8, 9, 10]  # Age-based coloring


# ─── 1D Elementary Cellular Automaton ─────────────────────────────────────────

class ElementaryCA:
    """Wolfram's 1D elementary cellular automata (rules 0–255)."""

    def __init__(self, rule: int = 110, width: int = 120):
        self.rule = rule
        self.width = width
        self.rule_bits = self._parse_rule(rule)
        self.reset()

    def _parse_rule(self, rule: int) -> dict:
        bits = format(rule, '08b')
        mapping = {}
        for i in range(8):
            pattern = format(i, '03b')
            mapping[pattern] = int(bits[7 - i])
        return mapping

    def reset(self, seed: str = None):
        if seed == "random":
            self.state = [random.randint(0, 1) for _ in range(self.width)]
        elif seed == "center":
            self.state = [0] * self.width
            self.state[self.width // 2] = 1
        else:
            self.state = [0] * self.width
            self.state[self.width // 2] = 1
        self.history = [self.state[:]]

    def step(self):
        new_state = []
        for i in range(self.width):
            left = self.state[(i - 1) % self.width]
            center = self.state[i]
            right = self.state[(i + 1) % self.width]
            pattern = f"{left}{center}{right}"
            new_state.append(self.rule_bits[pattern])
        self.state = new_state
        self.history.append(self.state[:])

    def to_display(self, height: int) -> List[List[int]]:
        """Return a 2D grid of the history, trimming to height."""
        rows = self.history[-height:]
        return rows


# ─── 2D Cellular Automaton (General) ─────────────────────────────────────────

class LifeLikeCA:
    """2D 'Life-like' cellular automaton with B/S notation."""

    def __init__(self, birth: List[int] = None, survive: List[int] = None,
                 width: int = 80, height: int = 40):
        self.birth = birth or [3]
        self.survive = survive or [2, 3]
        self.width = width
        self.height = height
        self.rule_str = f"B{''.join(map(str, self.birth))}/S{''.join(map(str, self.survive))}"
        self.reset()

    def reset(self, pattern: str = "random"):
        self.grid = [[0] * self.width for _ in range(self.height)]
        self.age = [[0] * self.width for _ in range(self.height)]
        self.generation = 0

        if pattern == "random":
            density = 0.25
            for r in range(self.height):
                for c in range(self.width):
                    if random.random() < density:
                        self.grid[r][c] = 1
                        self.age[r][c] = 1
        elif pattern == "glider_gun":
            self._place_gosper_gun(2, 2)
        elif pattern == "pulsar":
            self._place_pulsar(self.height // 2 - 6, self.width // 2 - 6)
        elif pattern == "lwss":
            self._place_lwss(self.height // 2, self.width // 4)

    def _place_gosper_gun(self, r: int, c: int):
        cells = [
            (0, 24), (1, 22), (1, 24), (2, 12), (2, 13), (2, 20), (2, 21), (2, 34), (2, 35),
            (3, 11), (3, 15), (3, 20), (3, 21), (3, 34), (3, 35), (4, 0), (4, 1), (4, 10),
            (4, 16), (4, 20), (4, 21), (5, 0), (5, 1), (5, 10), (5, 14), (5, 16), (5, 17),
            (5, 22), (5, 24), (6, 10), (6, 16), (6, 24), (7, 11), (7, 15), (8, 12), (8, 13),
        ]
        for dr, dc in cells:
            rr, cc = r + dr, c + dc
            if 0 <= rr < self.height and 0 <= cc < self.width:
                self.grid[rr][cc] = 1
                self.age[rr][cc] = 1

    def _place_pulsar(self, r: int, c: int):
        offsets = [
            (0, 2), (0, 3), (0, 4), (0, 8), (0, 9), (0, 10),
            (2, 0), (2, 5), (2, 7), (2, 12),
            (3, 0), (3, 5), (3, 7), (3, 12),
            (4, 0), (4, 5), (4, 7), (4, 12),
            (5, 2), (5, 3), (5, 4), (5, 8), (5, 9), (5, 10),
        ]
        for dr, dc in offsets:
            for sr, sc in [(0, 0), (0, 12), (12, 0), (12, 12)]:
                rr, cc = r + abs(dr - sr), c + abs(dc - sc)
                # Mirror
                if 0 <= rr < self.height and 0 <= cc < self.width:
                    self.grid[rr][cc] = 1
                    self.age[rr][cc] = 1

    def _place_lwss(self, r: int, c: int):
        cells = [(0, 1), (0, 4), (1, 0), (2, 0), (2, 4), (3, 0), (3, 1), (3, 2), (3, 3)]
        for dr, dc in cells:
            rr, cc = r + dr, c + dc
            if 0 <= rr < self.height and 0 <= cc < self.width:
                self.grid[rr][cc] = 1
                self.age[rr][cc] = 1

    def count_neighbors(self, r: int, c: int) -> int:
        count = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr = (r + dr) % self.height
                nc = (c + dc) % self.width
                count += self.grid[nr][nc]
        return count

    def step(self):
        new_grid = [[0] * self.width for _ in range(self.height)]
        new_age = [[0] * self.width for _ in range(self.height)]
        for r in range(self.height):
            for c in range(self.width):
                n = self.count_neighbors(r, c)
                if self.grid[r][c] == 1:
                    if n in self.survive:
                        new_grid[r][c] = 1
                        new_age[r][c] = self.age[r][c] + 1
                else:
                    if n in self.birth:
                        new_grid[r][c] = 1
                        new_age[r][c] = 1
        self.grid = new_grid
        self.age = new_age
        self.generation += 1

    def population(self) -> int:
        return sum(sum(row) for row in self.grid)


# ─── Preset Rules ────────────────────────────────────────────────────────────

PRESETS = {
    "life":      {"birth": [3], "survive": [2, 3], "desc": "Conway's Game of Life"},
    "highlife":   {"birth": [3, 6], "survive": [2, 3], "desc": "HighLife — replicators!"},
    "seeds":      {"birth": [2], "survive": [], "desc": "Seeds — explosive growth"},
    "daynight":   {"birth": [3, 6, 7, 8], "survive": [3, 4, 6, 7, 8], "desc": "Day & Night — symmetric"},
    "diamoeba":   {"birth": [3, 5, 6, 7, 8], "survive": [5, 6, 7, 8], "desc": "Diamoeba — blobby"},
    "maze":       {"birth": [3], "survive": [1, 2, 3, 4, 5], "desc": "Maze generator"},
    "coral":      {"birth": [3], "survive": [4, 5, 6, 7, 8], "desc": "Coral — slow growth"},
    "anneal":     {"birth": [4, 6, 7, 8], "survive": [3, 5, 6, 7, 8], "desc": "Anneal — smooths noise"},
    "2x2":        {"birth": [3, 6], "survive": [1, 2, 5], "desc": "2x2 — blocky patterns"},
    "replicator": {"birth": [1, 3, 5, 7], "survive": [1, 3, 5, 7], "desc": "Replicator — copies itself"},
}


# ─── curses Interactive UI ──────────────────────────────────────────────────

class Mode(Enum):
    RULE_1D = "1D"
    RULE_2D = "2D"


class CellLabUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.mode = Mode.RULE_2D
        self.running = True
        self.paused = False
        self.speed = 10  # steps per second
        self.step_count = 0

        # 1D state
        self.rule_1d = 110
        self.ca_1d = None

        # 2D state
        self.preset_name = "life"
        self.ca_2d = None
        self.pattern = "random"
        self.custom_birth = [3]
        self.custom_survive = [2, 3]

        # Cursor for editing
        self.cursor_r = 0
        self.cursor_c = 0
        self.draw_mode = False  # True = drawing cells

        self._init_curses()
        self._init_automata()

    def _init_curses(self):
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        curses.start_color()
        if curses.can_change_color():
            curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)   # ALIVE
            curses.init_pair(2, curses.COLOR_BLUE, curses.COLOR_BLACK)     # GRID
            curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)     # BORN
            curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)      # DYING
            curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_BLACK)   # HEADER
            curses.init_pair(6, curses.COLOR_GREEN, curses.COLOR_BLACK)    # AGE 1
            curses.init_pair(7, curses.COLOR_YELLOW, curses.COLOR_BLACK)   # AGE 2
            curses.init_pair(8, curses.COLOR_RED, curses.COLOR_BLACK)      # AGE 3
            curses.init_pair(9, curses.COLOR_MAGENTA, curses.COLOR_BLACK)  # AGE 4
            curses.init_pair(10, curses.COLOR_WHITE, curses.COLOR_BLACK)   # AGE 5+
        else:
            for i in range(1, 11):
                curses.init_pair(i, curses.COLOR_WHITE, curses.COLOR_BLACK)

    def _init_automata(self):
        h, w = self._grid_size()
        self.ca_1d = ElementaryCA(rule=self.rule_1d, width=w)
        self.ca_1d.reset("center")

        preset = PRESETS[self.preset_name]
        self.custom_birth = preset["birth"]
        self.custom_survive = preset["survive"]
        self.ca_2d = LifeLikeCA(
            birth=self.custom_birth,
            survive=self.custom_survive,
            width=w, height=h
        )
        self.ca_2d.reset(self.pattern)

    def _grid_size(self) -> Tuple[int, int]:
        h, w = self.stdscr.getmaxyx()
        return max(h - 4, 10), max(w, 20)

    def _age_color(self, age: int) -> int:
        if age <= 0:
            return 0
        idx = min(age - 1, len(Palette.AGE_COLORS) - 1)
        return Palette.AGE_COLORS[idx]

    def run(self):
        last_step = time.time()
        while self.running:
            ch = self.stdscr.getch()
            if ch != -1:
                self._handle_key(ch)

            now = time.time()
            if not self.paused and (now - last_step) >= (1.0 / max(self.speed, 1)):
                self._step()
                last_step = now

            self._draw()
            self.stdscr.refresh()
            time.sleep(0.01)

    def _step(self):
        self.step_count += 1
        if self.mode == Mode.RULE_1D:
            self.ca_1d.step()
        else:
            self.ca_2d.step()

    def _handle_key(self, ch):
        # Global keys
        if ch == ord('q') or ch == 27:
            self.running = False
            return
        elif ch == ord(' '):
            self.paused = not self.paused
            return
        elif ch == ord('r'):
            self.step_count = 0
            if self.mode == Mode.RULE_1D:
                self.ca_1d.reset("center")
            else:
                self.ca_2d.reset(self.pattern)
            return
        elif ch == ord('R'):
            self.step_count = 0
            if self.mode == Mode.RULE_1D:
                self.ca_1d.reset("random")
            else:
                self.ca_2d.reset("random")
            return
        elif ch == ord('\t'):
            # Toggle mode
            if self.mode == Mode.RULE_1D:
                self.mode = Mode.RULE_2D
            else:
                self.mode = Mode.RULE_1D
            self.step_count = 0
            self._init_automata()
            return
        elif ch == ord('+') or ch == ord('='):
            self.speed = min(self.speed + 5, 120)
            return
        elif ch == ord('-') or ch == ord('_'):
            self.speed = max(self.speed - 5, 1)
            return
        elif ch == ord('.'):
            # Single step
            self.paused = True
            self._step()
            return

        # Mode-specific keys
        if self.mode == Mode.RULE_1D:
            self._handle_1d_keys(ch)
        else:
            self._handle_2d_keys(ch)

    def _handle_1d_keys(self, ch):
        if ch == ord('n'):
            self.rule_1d = (self.rule_1d + 1) % 256
            self.ca_1d = ElementaryCA(rule=self.rule_1d, width=self.ca_1d.width)
            self.ca_1d.reset("center")
            self.step_count = 0
        elif ch == ord('p'):
            self.rule_1d = (self.rule_1d - 1) % 256
            self.ca_1d = ElementaryCA(rule=self.rule_1d, width=self.ca_1d.width)
            self.ca_1d.reset("center")
            self.step_count = 0
        elif ch == ord('0'):
            self.rule_1d = 0
            self.ca_1d = ElementaryCA(rule=0, width=self.ca_1d.width)
            self.ca_1d.reset("center")
            self.step_count = 0
        elif ch == ord('3'):
            self.rule_1d = 30
            self.ca_1d = ElementaryCA(rule=30, width=self.ca_1d.width)
            self.ca_1d.reset("center")
            self.step_count = 0
        elif ch == ord('9'):
            self.rule_1d = 90
            self.ca_1d = ElementaryCA(rule=90, width=self.ca_1d.width)
            self.ca_1d.reset("center")
            self.step_count = 0
        elif ch == ord('1') and not (ch == ord('3') or ch == ord('9')):
            self.rule_1d = 110
            self.ca_1d = ElementaryCA(rule=110, width=self.ca_1d.width)
            self.ca_1d.reset("center")
            self.step_count = 0

    def _handle_2d_keys(self, ch):
        if ch == ord('n'):
            # Next preset
            keys = list(PRESETS.keys())
            idx = keys.index(self.preset_name)
            self.preset_name = keys[(idx + 1) % len(keys)]
            self._apply_preset()
        elif ch == ord('p'):
            keys = list(PRESETS.keys())
            idx = keys.index(self.preset_name)
            self.preset_name = keys[(idx - 1) % len(keys)]
            self._apply_preset()
        elif ch == ord('g'):
            self.pattern = "glider_gun"
            self._apply_preset()
        elif ch == ord('u'):
            self.pattern = "pulsar"
            self._apply_preset()
        elif ch == ord('l'):
            self.pattern = "lwss"
            self._apply_preset()
        elif ch == ord('d'):
            self.draw_mode = not self.draw_mode
        elif ch == curses.KEY_UP or ch == ord('w'):
            self.cursor_r = max(0, self.cursor_r - 1)
            if self.draw_mode:
                self._toggle_cell()
        elif ch == curses.KEY_DOWN or ch == ord('s'):
            self.cursor_r = min(self.ca_2d.height - 1, self.cursor_r + 1)
            if self.draw_mode:
                self._toggle_cell()
        elif ch == curses.KEY_LEFT or ch == ord('a'):
            self.cursor_c = max(0, self.cursor_c - 1)
            if self.draw_mode:
                self._toggle_cell()
        elif ch == curses.KEY_RIGHT or ch == ord('d') and not self.draw_mode:
            self.cursor_c = min(self.ca_2d.width - 1, self.cursor_c + 1)
            if self.draw_mode:
                self._toggle_cell()
        elif ch == ord('e'):
            self._toggle_cell()

    def _apply_preset(self):
        preset = PRESETS[self.preset_name]
        self.custom_birth = preset["birth"]
        self.custom_survive = preset["survive"]
        self.ca_2d = LifeLikeCA(
            birth=self.custom_birth,
            survive=self.custom_survive,
            width=self.ca_2d.width,
            height=self.ca_2d.height
        )
        self.ca_2d.reset(self.pattern)
        self.step_count = 0

    def _toggle_cell(self):
        r, c = self.cursor_r, self.cursor_c
        if 0 <= r < self.ca_2d.height and 0 <= c < self.ca_2d.width:
            self.ca_2d.grid[r][c] = 1 - self.ca_2d.grid[r][c]
            if self.ca_2d.grid[r][c]:
                self.ca_2d.age[r][c] = 1
            else:
                self.ca_2d.age[r][c] = 0

    def _draw(self):
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()

        if self.mode == Mode.RULE_1D:
            self._draw_1d(h, w)
        else:
            self._draw_2d(h, w)

    def _draw_1d(self, h: int, w: int):
        rows = self.ca_1d.to_display(h - 3)
        rule_bits = format(self.rule_1d, '08b')

        # Header
        header = f" CellLab 1D │ Rule {self.rule_1d} ({rule_bits}) │ Step {self.step_count} │ Speed {self.speed}/s │ {'▶' if not self.paused else '⏸'}"
        try:
            self.stdscr.addstr(0, 0, header[:w-1], curses.color_pair(Palette.HEADER) | curses.A_BOLD)
        except curses.error:
            pass

        # Draw automaton
        for ri, row in enumerate(rows):
            for ci, cell in enumerate(row):
                if ci >= w - 1:
                    break
                ch = '█' if cell else ' '
                color = curses.color_pair(Palette.ALIVE) if cell else curses.color_pair(Palette.DEAD)
                try:
                    self.stdscr.addch(ri + 1, ci, ch, color)
                except curses.error:
                    pass

        # Footer
        footer = " n/p: next/prev rule │ r: reset center │ R: random │ 3:rule30 9:rule90 1:rule110 │ Tab:2D │ q:quit"
        try:
            self.stdscr.addstr(h - 1, 0, footer[:w-1], curses.color_pair(Palette.HEADER))
        except curses.error:
            pass

    def _draw_2d(self, h: int, w: int):
        gh = h - 3  # Grid height
        gw = w      # Grid width

        preset = PRESETS.get(self.preset_name, {})
        desc = preset.get("desc", "")
        rule_str = self.ca_2d.rule_str if self.ca_2d else ""

        pop = self.ca_2d.population() if self.ca_2d else 0

        header = f" CellLab 2D │ {self.preset_name}: {desc} │ {rule_str} │ Pop {pop} │ Step {self.step_count} │ {'▶' if not self.paused else '⏸'}"
        try:
            self.stdscr.addstr(0, 0, header[:w-1], curses.color_pair(Palette.HEADER) | curses.A_BOLD)
        except curses.error:
            pass

        if self.ca_2d:
            for r in range(min(gh, self.ca_2d.height)):
                for c in range(min(gw - 1, self.ca_2d.width)):
                    if self.ca_2d.grid[r][c]:
                        age = self.ca_2d.age[r][c]
                        ci = self._age_color(age)
                        ch = '█'
                    else:
                        ci = Palette.DEAD
                        ch = '·'
                    try:
                        self.stdscr.addch(r + 1, c, ch, curses.color_pair(ci))
                    except curses.error:
                        pass

            # Draw cursor
            if self.draw_mode:
                try:
                    cr, cc = self.cursor_r + 1, self.cursor_c
                    if 0 <= cr < h and 0 <= cc < w:
                        self.stdscr.addch(cr, cc, 'X', curses.color_pair(Palette.HEADER) | curses.A_REVERSE)
                except curses.error:
                    pass

        footer = " n/p: preset │ g:gun u:pulsar l:lwss │ r:reset R:random │ d:draw e:toggle │ +/-:speed │ Tab:1D │ q:quit"
        try:
            self.stdscr.addstr(h - 1, 0, footer[:w-1], curses.color_pair(Palette.HEADER))
        except curses.error:
            pass


# ─── Non-interactive mode: render to terminal ────────────────────────────────

def render_1d(rule: int, width: int = 120, height: int = 50):
    """Render a 1D elementary CA as plain text."""
    ca = ElementaryCA(rule=rule, width=width)
    ca.reset("center")
    for _ in range(height):
        line = ''.join('█' if c else ' ' for c in ca.state)
        print(line)
        ca.step()


def render_2d(preset: str, width: int = 80, height: int = 40, steps: int = 100,
              delay: float = 0.05, animate: bool = True):
    """Render a 2D Life-like CA as plain text."""
    if preset not in PRESETS:
        print(f"Unknown preset '{preset}'. Available: {', '.join(PRESETS.keys())}")
        return

    p = PRESETS[preset]
    ca = LifeLikeCA(birth=p["birth"], survive=p["survive"], width=width, height=height)
    ca.reset("random")

    for step in range(steps):
        # Clear screen if animating
        if animate:
            print(f"\033[2J\033[H", end='')  # ANSI clear screen + cursor home

        print(f"  {preset}: {p['desc']} | B{''.join(map(str,p['birth']))}/S{''.join(map(str,p['survive']))} | Step {step} | Pop {ca.population()}")
        print("  " + '─' * min(width, 78))

        for r in range(height):
            line = ''
            for c in range(width):
                line += '█' if ca.grid[r][c] else '·'
            print(line)

        print("  " + '─' * min(width, 78))
        print("  Ctrl+C to stop")

        ca.step()
        if animate:
            time.sleep(delay)

    if not animate:
        print(f"\n  Completed {steps} steps of {preset} ({p['desc']})")


def list_presets():
    """Print all available presets."""
    print("\n  CellLab — Available Presets\n")
    print(f"  {'Name':<14} {'Rule':<12} {'Description'}")
    print(f"  {'─'*14} {'─'*12} {'─'*40}")
    for name, p in PRESETS.items():
        rule = f"B{''.join(map(str,p['birth']))}/S{''.join(map(str,p['survive']))}"
        print(f"  {name:<14} {rule:<12} {p['desc']}")
    print()


def list_rules():
    """Print interesting 1D rules."""
    print("\n  CellLab — Notable 1D Rules\n")
    notable = {
        30: "Chaotic — random number generator",
        90: "Sierpinski triangle",
        110: "Turing complete",
        184: "Traffic flow model",
        150: "XOR-based symmetry",
        60: "Nested structures",
        73: "Complex behavior",
        22: "Triangle patterns",
    }
    for r, desc in sorted(notable.items()):
        print(f"  Rule {r:>3}: {desc}")
    print(f"\n  Any rule 0–255 can be used.\n")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="CellLab — Interactive Cellular Automata Laboratory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cellab                          Interactive mode (2D Game of Life)
  cellab --1d --rule 30           Interactive 1D Rule 30
  cellab --render-1d 90           Render Rule 90 to terminal
  cellab --render-2d highlife     Render HighLife to terminal
  cellab --list-presets           Show all 2D presets
  cellab --list-rules             Show notable 1D rules
        """
    )

    parser.add_argument('--one-d', dest='one_d', action='store_true', help='Start in 1D mode')
    parser.add_argument('--rule', type=int, default=110, help='1D rule number (0-255)')
    parser.add_argument('--preset', type=str, default='life', help='2D preset name')
    parser.add_argument('--render-1d', type=int, metavar='RULE', help='Non-interactive: render 1D rule')
    parser.add_argument('--render-2d', type=str, metavar='PRESET', help='Non-interactive: render 2D preset')
    parser.add_argument('--steps', type=int, default=200, help='Steps for non-interactive mode')
    parser.add_argument('--delay', type=float, default=0.05, help='Delay between steps (seconds)')
    parser.add_argument('--width', type=int, default=120, help='Grid width')
    parser.add_argument('--height', type=int, default=50, help='Grid height')
    parser.add_argument('--no-animate', action='store_true', help='Don\'t clear screen in render mode')
    parser.add_argument('--list-presets', action='store_true', help='List 2D presets')
    parser.add_argument('--list-rules', action='store_true', help='List notable 1D rules')

    args = parser.parse_args()

    if args.list_presets:
        list_presets()
        return

    if args.list_rules:
        list_rules()
        return

    if args.render_1d is not None:
        render_1d(rule=args.render_1d, width=args.width, height=args.height)
        return

    if args.render_2d is not None:
        render_2d(args.render_2d, width=args.width, height=args.height,
                  steps=args.steps, delay=args.delay, animate=not args.no_animate)
        return

    # Interactive mode
    def _main(stdscr):
        ui = CellLabUI(stdscr)
        if args.one_d:
            ui.mode = Mode.RULE_1D
            ui.rule_1d = args.rule
        else:
            if args.preset in PRESETS:
                ui.preset_name = args.preset
        ui._init_automata()
        ui.run()

    try:
        curses.wrapper(_main)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()