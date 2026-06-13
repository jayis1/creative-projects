#!/usr/bin/env python3
"""
Terminal Slides — A terminal-based presentation tool.
Feed it a Markdown file and it renders beautiful slides in your terminal.

Supports:
  - Slide separators (---)
  - Headers, bold, italic, inline code, code blocks
  - Ordered & unordered lists
  - Blockquotes
  - Markdown links [text](url)
  - Speaker notes (lines starting with ???)
  - Horizontal rules (rendered as decorative lines)
  - Theming (dark/light/monochrome)
  - Progress bar with timestamp
  - Keyboard navigation (arrows, space, q to quit, n for notes, number+Enter for goto)
  - Auto-play mode with configurable interval
  - --list to show slide titles
  - Export slides to plain text
  - --version flag
"""

import sys
import os
import re
import shutil
import argparse
import textwrap
import select
import time

__version__ = "1.2.0"

# ──────────────────────────────────────────────
# ANSI helpers
# ──────────────────────────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"
BLINK = "\033[5m"
REVERSE = "\033[7m"

# Color palette
COLORS = {
    "black":   "\033[30m",
    "red":     "\033[31m",
    "green":   "\033[32m",
    "yellow":  "\033[33m",
    "blue":    "\033[34m",
    "magenta": "\033[35m",
    "cyan":    "\033[36m",
    "white":   "\033[37m",
    "bright_black":   "\033[90m",
    "bright_red":     "\033[91m",
    "bright_green":   "\033[92m",
    "bright_yellow":  "\033[93m",
    "bright_blue":    "\033[94m",
    "bright_magenta": "\033[95m",
    "bright_cyan":    "\033[96m",
    "bright_white":   "\033[97m",
}

BG_COLORS = {
    "black":   "\033[40m",
    "red":     "\033[41m",
    "green":   "\033[42m",
    "yellow":  "\033[43m",
    "blue":    "\033[44m",
    "magenta": "\033[45m",
    "cyan":    "\033[46m",
    "white":   "\033[47m",
}

# ──────────────────────────────────────────────
# Themes
# ──────────────────────────────────────────────

THEMES = {
    "dark": {
        "title":       ("bright_cyan",  "bold"),
        "subtitle":    ("cyan",         "bold"),
        "heading2":    ("bright_green", "bold"),
        "heading3":    ("green",        "bold"),
        "body":        ("white",        "normal"),
        "dim":         ("bright_black", "dim"),
        "code_inline": ("bright_yellow","normal"),
        "code_block":  ("bright_green", "normal"),
        "quote":       ("bright_magenta","italic"),
        "quote_bar":   ("magenta",      "normal"),
        "bullet":      ("bright_yellow","bold"),
        "number":      ("bright_yellow","bold"),
        "bold":        ("bright_white", "bold"),
        "italic":      ("bright_cyan",  "italic"),
        "link":        ("bright_blue",  "underline"),
        "progress":    ("cyan",         "normal"),
        "progress_bg": ("bright_black", "normal"),
        "slide_num":   ("bright_black", "dim"),
        "hr":          ("bright_black", "dim"),
        "notes":       ("bright_yellow", "dim"),
        "notes_bar":   ("yellow",       "dim"),
    },
    "light": {
        "title":       ("blue",         "bold"),
        "subtitle":    ("blue",         "normal"),
        "heading2":    ("green",        "bold"),
        "heading3":    ("green",        "normal"),
        "body":        ("black",        "normal"),
        "dim":         ("bright_black", "dim"),
        "code_inline": ("magenta",      "normal"),
        "code_block":  ("green",        "normal"),
        "quote":       ("magenta",      "italic"),
        "quote_bar":   ("magenta",      "normal"),
        "bullet":      ("red",          "bold"),
        "number":      ("red",          "bold"),
        "bold":        ("black",        "bold"),
        "italic":      ("blue",         "italic"),
        "link":        ("blue",         "underline"),
        "progress":    ("blue",         "normal"),
        "progress_bg": ("bright_black", "normal"),
        "slide_num":   ("bright_black", "dim"),
        "hr":          ("bright_black", "dim"),
        "notes":       ("bright_black", "dim"),
        "notes_bar":   ("bright_black", "dim"),
    },
    "monochrome": {
        "title":       ("white",        "bold"),
        "subtitle":    ("white",        "normal"),
        "heading2":    ("white",        "bold"),
        "heading3":    ("white",        "underline"),
        "body":        ("white",        "normal"),
        "dim":         ("bright_black", "dim"),
        "code_inline": ("white",        "bold"),
        "code_block":  ("white",        "normal"),
        "quote":       ("bright_black", "italic"),
        "quote_bar":   ("bright_black", "normal"),
        "bullet":      ("white",        "bold"),
        "number":      ("white",        "bold"),
        "bold":        ("white",        "bold"),
        "italic":      ("white",        "italic"),
        "link":        ("white",        "underline"),
        "progress":    ("white",        "normal"),
        "progress_bg": ("bright_black", "normal"),
        "slide_num":   ("bright_black", "dim"),
        "hr":          ("bright_black", "dim"),
        "notes":       ("bright_black", "dim"),
        "notes_bar":   ("bright_black", "dim"),
    },
}

# ──────────────────────────────────────────────
# Slide parser
# ──────────────────────────────────────────────

class SlideParser:
    """Parse a Markdown string into a list of slides.

    Each slide is a list of element dicts. Supported element types:
      heading1, heading2, heading3, text, code_block, quote,
      unordered_list, ordered_list, hr, note
    """

    HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$')
    BOLD_RE = re.compile(r'\*\*(.+?)\*\*')
    ITALIC_RE = re.compile(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)')
    CODE_INLINE_RE = re.compile(r'`(.+?)`')
    LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    QUOTE_RE = re.compile(r'^>\s?(.*)$')
    UNORDERED_RE = re.compile(r'^[\s]*[-*+]\s+(.+)$')
    ORDERED_RE = re.compile(r'^[\s]*(\d+)\.\s+(.+)$')
    HORIZONTAL_RE = re.compile(r'^-{4,}\s*$')
    CODE_FENCE_RE = re.compile(r'^```(\w*)$')
    NOTE_RE = re.compile(r'^\?\?\?\s*(.*)$')

    def __init__(self, text: str):
        self.slides: list[list[dict]] = []
        self._parse(text)

    def _parse(self, text: str):
        # Normalize CRLF to LF (handle Windows line endings)
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        # Handle --- at the very start of the file (skip it as a separator)
        text = re.sub(r'^---\s*\n', '', text)
        # Split on slide separators: --- on its own line (allowing trailing whitespace)
        raw_slides = re.split(r'\n---\s*\n|\n---\s*$', text)
        for raw in raw_slides:
            slide = self._parse_slide(raw.strip())
            if slide:
                self.slides.append(slide)

    def _parse_slide(self, text: str) -> list[dict]:
        lines = text.split('\n')
        elements = []
        i = 0
        while i < len(lines):
            line = lines[i]

            # Code fence
            m = self.CODE_FENCE_RE.match(line)
            if m:
                lang = m.group(1)
                code_lines = []
                i += 1
                while i < len(lines) and not self.CODE_FENCE_RE.match(lines[i]):
                    code_lines.append(lines[i])
                    i += 1
                if i < len(lines):
                    i += 1  # skip closing ```
                elements.append({"type": "code_block", "lang": lang, "text": "\n".join(code_lines)})
                continue

            # Speaker note (lines starting with ???)
            m = self.NOTE_RE.match(line)
            if m:
                note_lines = [m.group(1)]
                i += 1
                while i < len(lines):
                    m2 = self.NOTE_RE.match(lines[i])
                    if m2:
                        note_lines.append(m2.group(1))
                        i += 1
                    else:
                        break
                elements.append({"type": "note", "text": self._inline_format(" ".join(note_lines))})
                continue

            # Heading
            m = self.HEADING_RE.match(line)
            if m:
                level = len(m.group(1))
                content = m.group(2)
                elements.append({"type": f"heading{min(level, 3)}", "text": self._inline_format(content)})
                i += 1
                continue

            # Blockquote
            m = self.QUOTE_RE.match(line)
            if m:
                quote_lines = [m.group(1)]
                i += 1
                while i < len(lines):
                    m2 = self.QUOTE_RE.match(lines[i])
                    if m2:
                        quote_lines.append(m2.group(1))
                        i += 1
                    else:
                        break
                elements.append({"type": "quote", "text": self._inline_format(" ".join(quote_lines))})
                continue

            # Unordered list
            m = self.UNORDERED_RE.match(line)
            if m:
                items = [m.group(1)]
                i += 1
                while i < len(lines):
                    m2 = self.UNORDERED_RE.match(lines[i])
                    if m2:
                        items.append(m2.group(1))
                        i += 1
                    else:
                        break
                elements.append({"type": "unordered_list", "items": [self._inline_format(it) for it in items]})
                continue

            # Ordered list
            m = self.ORDERED_RE.match(line)
            if m:
                items = [(int(m.group(1)), m.group(2))]
                i += 1
                while i < len(lines):
                    m2 = self.ORDERED_RE.match(lines[i])
                    if m2:
                        items.append((int(m2.group(1)), m2.group(2)))
                        i += 1
                    else:
                        break
                elements.append({"type": "ordered_list", "items": [(n, self._inline_format(t)) for n, t in items]})
                continue

            # Horizontal rule (render as decorative separator)
            if self.HORIZONTAL_RE.match(line):
                elements.append({"type": "hr"})
                i += 1
                continue

            # Blank line
            if line.strip() == '':
                i += 1
                continue

            # Regular text
            elements.append({"type": "text", "text": self._inline_format(line)})
            i += 1

        return elements

    def _inline_format(self, text: str) -> str:
        """Store inline format markers; we'll render them later with theme colors."""
        BOLD_OPEN = "<<BOLD>>"
        BOLD_CLOSE = "<</BOLD>>"
        ITALIC_OPEN = "<<ITALIC>>"
        ITALIC_CLOSE = "<</ITALIC>>"
        CODE_OPEN = "<<CODE>>"
        CODE_CLOSE = "<</CODE>>"
        LINK_OPEN = "<<LINK:"
        LINK_MID = ">>"
        LINK_CLOSE = "<</LINK>>"
        # Process links first so bold/italic inside link text still works
        text = self.LINK_RE.sub(lambda m: f'{LINK_OPEN}{m.group(2)}{LINK_MID}{m.group(1)}{LINK_CLOSE}', text)
        text = self.BOLD_RE.sub(BOLD_OPEN + r'\1' + BOLD_CLOSE, text)
        text = self.ITALIC_RE.sub(ITALIC_OPEN + r'\1' + ITALIC_CLOSE, text)
        text = self.CODE_INLINE_RE.sub(CODE_OPEN + r'\1' + CODE_CLOSE, text)
        return text

    def get_slide_titles(self) -> list[str]:
        """Return a list of slide titles (first heading or first text line per slide)."""
        titles = []
        for slide in self.slides:
            title = None
            for elem in slide:
                if elem["type"] in ("heading1", "heading2", "heading3"):
                    # Strip inline format markers for a clean title
                    title = re.sub(r'<<.*?>>', '', elem["text"])
                    break
                if elem["type"] == "text" and title is None:
                    title = re.sub(r'<<.*?>>', '', elem["text"])
            titles.append(title or "(untitled)")
        return titles


# ──────────────────────────────────────────────
# Renderer
# ──────────────────────────────────────────────

class Renderer:
    """Renders parsed slide elements into ANSI-decorated strings."""

    def __init__(self, theme_name: str = "dark"):
        self.theme_name = theme_name
        self.theme = THEMES.get(theme_name, THEMES["dark"])
        self.cols, self.rows = shutil.get_terminal_size((80, 24))
        self.cols = max(self.cols, 40)
        self.rows = max(self.rows, 12)

    def _color(self, element: str) -> str:
        color_name, style = self.theme.get(element, ("white", "normal"))
        prefix = COLORS.get(color_name, COLORS["white"])
        if style == "bold":
            prefix += BOLD
        elif style == "dim":
            prefix += DIM
        elif style == "italic":
            prefix += ITALIC
        elif style == "underline":
            prefix += UNDERLINE
        return prefix

    def _render_inline(self, text: str) -> str:
        """Replace inline format markers with ANSI sequences."""
        text = text.replace('<<BOLD>>', self._color("bold"))
        text = text.replace('<</BOLD>>', self._color("body"))
        text = text.replace('<<ITALIC>>', self._color("italic"))
        text = text.replace('<</ITALIC>>', self._color("body"))
        text = text.replace('<<CODE>>', self._color("code_inline"))
        text = text.replace('<</CODE>>', self._color("body"))
        # Links: <<LINK:url>>text<</LINK>> → url-rendered text
        def _link_replace(m):
            url = m.group(1)
            link_text = m.group(2)
            return f"{self._color('link')}{link_text} {DIM}({url}){RESET}{self._color('body')}"
        text = re.sub(r'<<LINK:(.*?)>>(.*?)<</LINK>>', _link_replace, text)
        return text

    def _center(self, line: str, width: int = 0) -> str:
        """Center a line in the terminal, accounting for ANSI codes."""
        visible = re.sub(r'\033\[[0-9;]*m', '', line)
        vis_len = len(visible)
        target_w = width or self.cols
        pad = max(0, (target_w - vis_len) // 2)
        return " " * pad + line

    def _wrap_text(self, text: str, indent: int = 2, max_width: int = 0) -> list[str]:
        """Wrap a long line of text to fit within terminal width, preserving ANSI codes.

        When text contains inline format markers (<<BOLD>>, etc.), we strip them
        for measurement, wrap the clean text, then re-apply formatting by mapping
        segments from the original to the wrapped lines.
        """
        if not max_width:
            max_width = self.cols - indent - 2
        # Strip ANSI and inline format markers for measurement
        clean = re.sub(r'\033\[[0-9;]*m', '', text)
        # Also strip our inline format markers for length check
        clean_no_fmt = re.sub(r'<<.*?>>', '', clean)
        if len(clean_no_fmt) <= max_width:
            return [text]
        # For wrapped text, wrap the clean (marker-stripped) version
        # then re-render each wrapped segment through _render_inline
        wrapped = textwrap.wrap(clean_no_fmt, width=max_width)
        return wrapped

    def render_slide(self, slide: list[dict], slide_num: int, total: int, show_notes: bool = False) -> str:
        lines = []
        body_color = self._color("body")
        dim_color = self._color("dim")

        # Top padding
        lines.append("")

        for elem in slide:
            # Skip notes unless show_notes is True
            if elem["type"] == "note" and not show_notes:
                continue

            if elem["type"] == "heading1":
                text = self._render_inline(elem["text"])
                # Wrap long headings to fit terminal width
                clean_text = re.sub(r'\033\[[0-9;]*m', '', text)
                max_w = self.cols - 4
                if len(clean_text) > max_w:
                    wrapped = textwrap.wrap(clean_text, width=max_w)
                    for w_line in wrapped:
                        lines.append(self._center(f"{self._color('title')}{BOLD}{w_line}{RESET}"))
                else:
                    lines.append(self._center(f"{self._color('title')}{BOLD}{text}{RESET}"))
                lines.append(self._center(f"{dim_color}{'━' * min(40, self.cols - 4)}{RESET}"))
                lines.append("")

            elif elem["type"] == "heading2":
                text = self._render_inline(elem["text"])
                # Wrap long h2 headings
                clean_text = re.sub(r'\033\[[0-9;]*m', '', text)
                max_w = self.cols - 4
                if len(clean_text) > max_w:
                    wrapped = textwrap.wrap(clean_text, width=max_w)
                    for w_line in wrapped:
                        lines.append(f"  {self._color('heading2')}{BOLD}{w_line}{RESET}")
                else:
                    lines.append(f"  {self._color('heading2')}{BOLD}{text}{RESET}")
                lines.append("")

            elif elem["type"] == "heading3":
                text = self._render_inline(elem["text"])
                # Wrap long h3 headings
                clean_text = re.sub(r'\033\[[0-9;]*m', '', text)
                max_w = self.cols - 4
                if len(clean_text) > max_w:
                    wrapped = textwrap.wrap(clean_text, width=max_w)
                    for w_line in wrapped:
                        lines.append(f"  {self._color('heading3')}{UNDERLINE}{w_line}{RESET}")
                else:
                    lines.append(f"  {self._color('heading3')}{UNDERLINE}{text}{RESET}")
                lines.append("")

            elif elem["type"] == "text":
                text = self._render_inline(elem["text"])
                wrapped = self._wrap_text(text)
                for wl in wrapped:
                    lines.append(f"  {body_color}{wl}{RESET}")

            elif elem["type"] == "code_block":
                lang = elem.get("lang", "")
                code = elem["text"]
                # Box inner width (between the vertical bars)
                inner_w = self.cols - 6  # "  │" (3) + content + "│" (1) = cols - 2
                bar = f"  {self._color('code_inline')}┌{'─' * inner_w}┐{RESET}"
                lines.append(f"  {dim_color}{lang}{RESET}")
                lines.append(bar)
                for code_line in code.split('\n'):
                    # Truncate long lines to fit inside the box
                    max_code_w = inner_w - 2  # subtract "│ " prefix and " │" suffix padding
                    vis_len = len(code_line)
                    if vis_len > max_code_w:
                        code_line = code_line[:max_code_w - 1] + "…"
                        vis_len = len(code_line)
                    pad = max(0, inner_w - 2 - vis_len)
                    lines.append(f"  {self._color('code_block')}│ {code_line}{' ' * pad} │{RESET}")
                bar2 = f"  {self._color('code_inline')}└{'─' * inner_w}┘{RESET}"
                lines.append(bar2)
                lines.append("")

            elif elem["type"] == "quote":
                text = self._render_inline(elem["text"])
                bar_char = f"{self._color('quote_bar')}┃{RESET}"
                max_w = self.cols - 6
                # Wrap the clean text for quoting (strip both ANSI and format markers)
                clean_text = re.sub(r'\033\[[0-9;]*m', '', text)
                clean_text = re.sub(r'<<.*?>>', '', clean_text)
                wrapped = textwrap.wrap(clean_text, width=max_w)
                for w_line in wrapped:
                    lines.append(f"  {bar_char} {self._color('quote')}{w_line}{RESET}")
                lines.append("")

            elif elem["type"] == "unordered_list":
                bullet = f"{self._color('bullet')}•{RESET}"
                for item in elem["items"]:
                    item_rendered = self._render_inline(item)
                    # Wrap long list items to fit terminal width
                    prefix = f"    {bullet} {body_color}"
                    prefix_visible_len = 6  # "    • " = 6 visible chars
                    max_item_w = max(20, self.cols - prefix_visible_len - 2)
                    clean_item = re.sub(r'\033\[[0-9;]*m', '', item_rendered)
                    clean_item = re.sub(r'<<.*?>>', '', clean_item)
                    if len(clean_item) > max_item_w:
                        wrapped = textwrap.wrap(clean_item, width=max_item_w)
                        for j, w_line in enumerate(wrapped):
                            if j == 0:
                                lines.append(f"{prefix}{w_line}{RESET}")
                            else:
                                lines.append(f"      {body_color}{w_line}{RESET}")
                    else:
                        lines.append(f"{prefix}{item_rendered}{RESET}")
                lines.append("")

            elif elem["type"] == "ordered_list":
                for num, item_text in elem["items"]:
                    item_rendered = self._render_inline(item_text)
                    # Wrap long list items to fit terminal width
                    num_prefix = f"    {self._color('number')}{num}.{RESET} {body_color}"
                    num_visible_len = len(f"    {num}. ")  # visible chars for prefix
                    max_item_w = max(20, self.cols - num_visible_len - 2)
                    clean_item = re.sub(r'\033\[[0-9;]*m', '', item_rendered)
                    clean_item = re.sub(r'<<.*?>>', '', clean_item)
                    if len(clean_item) > max_item_w:
                        wrapped = textwrap.wrap(clean_item, width=max_item_w)
                        for j, w_line in enumerate(wrapped):
                            if j == 0:
                                lines.append(f"{num_prefix}{w_line}{RESET}")
                            else:
                                lines.append(f"      {body_color}{w_line}{RESET}")
                    else:
                        lines.append(f"{num_prefix}{item_rendered}{RESET}")
                lines.append("")

            elif elem["type"] == "hr":
                hr_char = "─"
                line_len = min(60, self.cols - 4)
                lines.append(f"  {self._color('hr')}{hr_char * line_len}{RESET}")
                lines.append("")

            elif elem["type"] == "note":
                # Speaker notes displayed at the bottom
                note_text = self._render_inline(elem["text"])
                bar_char = f"{self._color('notes_bar')}│{RESET}"
                # Build a note box that fits within terminal width
                # Box structure: "  ┌─ Notes ────...──┐" (total visible = note_box_w)
                note_box_w = min(60, self.cols - 4)  # total visible width of the box
                # Header: "  ┌─ Notes " (11 visible) + dashes + "┐"
                header_dashes = note_box_w - 11 - 1  # -1 for ┐, -11 for prefix
                lines.append(f"  {self._color('notes_bar')}┌─ Notes {'─' * header_dashes}┐{RESET}")
                # Wrap notes — strip both ANSI and inline format markers for measurement
                clean_note = re.sub(r'\033\[[0-9;]*m', '', note_text)
                clean_note = re.sub(r'<<.*?>>', '', clean_note)
                max_w = note_box_w - 6  # "  │ " (4) + content + " │" (2) = note_box_w
                if clean_note.strip():  # skip wrapping empty notes
                    wrapped = textwrap.wrap(clean_note, width=max_w)
                    for wl in wrapped:
                        lines.append(f"  {bar_char} {self._color('notes')}{wl} {bar_char}")
                else:
                    lines.append(f"  {bar_char}  {bar_char}")
                # Footer: "  └─────...───┘" — total visible width matches header
                footer_dashes = note_box_w - 4  # "  └" (3) + dashes + "┘" (1) = note_box_w
                lines.append(f"  {self._color('notes_bar')}└{'─' * footer_dashes}┘{RESET}")
                lines.append("")

        # Add vertical fill
        while len(lines) < self.rows - 3:
            lines.append("")

        # Progress bar with timestamp
        pct = (slide_num + 1) / total if total > 0 else 0
        bar_w = self.cols - 28
        filled = int(pct * bar_w)
        empty = bar_w - filled
        now = time.strftime("%H:%M")
        progress = (
            f"  {self._color('progress')}{'█' * filled}{self._color('progress_bg')}{'░' * empty}{RESET}"
            f"  {self._color('slide_num')}{slide_num + 1}/{total}{RESET}"
            f"  {dim_color}{now}{RESET}"
        )
        lines.append(progress)

        return "\n".join(lines)


# ──────────────────────────────────────────────
# Terminal input (no curses dependency)
# ──────────────────────────────────────────────

def _get_key() -> str:
    """Read a single keypress from stdin without echo.

    Returns action strings like 'NEXT', 'PREV', 'QUIT', etc.
    Also supports number entry for goto-slide (returns 'GOTO:N').
    """
    import tty, termios
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            seq = sys.stdin.read(2)
            if seq == '[A':
                return 'UP'
            elif seq == '[B':
                return 'DOWN'
            elif seq == '[C':
                return 'RIGHT'
            elif seq == '[D':
                return 'LEFT'
            elif seq == '[5':
                # Page Up: read trailing ~
                sys.stdin.read(1)
                return 'PREV'
            elif seq == '[6':
                # Page Down: read trailing ~
                sys.stdin.read(1)
                return 'NEXT'
            return 'ESC'
        elif ch == 'q' or ch == '\x03':  # q or Ctrl-C
            return 'QUIT'
        elif ch == ' ':
            return 'NEXT'
        elif ch == '\n' or ch == '\r':
            return 'NEXT'
        elif ch == 'h' or ch == 'b':
            return 'PREV'
        elif ch == 'j':
            return 'NEXT'
        elif ch == 'k':
            return 'PREV'
        elif ch == 'g':
            return 'FIRST'
        elif ch == 'G':
            return 'LAST'
        elif ch == 'n':
            return 'NOTES'
        elif ch == 'l':
            return 'LIST'
        elif ch == 'r':
            return 'REFRESH'
        elif ch in '0123456789':
            # Number entry mode: accumulate digits until Enter
            digits = ch
            # Set a brief timeout for subsequent digits
            new_old = termios.tcgetattr(fd)
            new_old[3] = new_old[3] & ~termios.ICANON
            # Wait for more digits or Enter
            while True:
                # Check if there's input available (brief timeout)
                import select as _sel
                ready, _, _ = _sel.select([sys.stdin], [], [], 0.5)
                if ready:
                    next_ch = sys.stdin.read(1)
                    if next_ch == '\n' or next_ch == '\r':
                        break
                    elif next_ch.isdigit():
                        digits += next_ch
                    elif next_ch == '\x1b':
                        # Escape cancels
                        return 'ESC'
                    else:
                        break
                else:
                    # Timeout - treat as goto
                    break
            if digits:
                return f'GOTO:{digits}'
            return 'ESC'
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _is_interactive_terminal() -> bool:
    """Check if stdin is connected to an interactive terminal (TTY)."""
    return sys.stdin.isatty()


# ──────────────────────────────────────────────
# Presentation runner
# ──────────────────────────────────────────────

class Presenter:
    """Interactive terminal presentation with keyboard navigation."""

    def __init__(self, slides: list[list[dict]], theme: str = "dark", auto: float = 0):
        self.slides = slides
        self.theme = theme
        self.auto = auto
        self.current = 0
        self.show_notes = False

    def run(self):
        if not _is_interactive_terminal():
            print("Error: Terminal Slides requires an interactive terminal (TTY).", file=sys.stderr)
            print("  Tip: Use --export to write slides to a file instead.", file=sys.stderr)
            sys.exit(1)

        renderer = Renderer(self.theme)

        # Save cursor & switch to alternate screen
        sys.stdout.write("\033[?1049h")  # alternate screen buffer
        sys.stdout.write("\033[?25l")     # hide cursor
        sys.stdout.flush()

        try:
            if self.auto > 0:
                self._auto_play(renderer)
            else:
                self._interactive(renderer)
        except KeyboardInterrupt:
            pass
        finally:
            sys.stdout.write("\033[?25h")   # show cursor
            sys.stdout.write("\033[?1049l") # back to main screen
            sys.stdout.flush()

    def _draw(self, renderer: Renderer):
        sys.stdout.write("\033[H\033[J")  # clear screen
        content = renderer.render_slide(self.slides[self.current], self.current, len(self.slides), show_notes=self.show_notes)
        sys.stdout.write(content)
        sys.stdout.flush()

    def _interactive(self, renderer: Renderer):
        self._draw(renderer)
        while True:
            key = _get_key()
            if key == 'QUIT':
                break
            elif key in ('NEXT', 'RIGHT', 'DOWN'):
                if self.current < len(self.slides) - 1:
                    self.current += 1
                    self._draw(renderer)
                else:
                    break  # past last slide = end
            elif key in ('PREV', 'LEFT', 'UP'):
                if self.current > 0:
                    self.current -= 1
                    self._draw(renderer)
            elif key == 'FIRST':
                self.current = 0
                self._draw(renderer)
            elif key == 'LAST':
                self.current = len(self.slides) - 1
                self._draw(renderer)
            elif key == 'NOTES':
                self.show_notes = not self.show_notes
                self._draw(renderer)
            elif key == 'REFRESH':
                # Re-render with current terminal size
                renderer.cols, renderer.rows = shutil.get_terminal_size((80, 24))
                renderer.cols = max(renderer.cols, 40)
                renderer.rows = max(renderer.rows, 12)
                self._draw(renderer)
            elif key.startswith('GOTO:'):
                target = int(key[5:]) - 1  # 1-indexed for user
                if 0 <= target < len(self.slides):
                    self.current = target
                    self._draw(renderer)
            elif key == 'ESC':
                pass  # ignore stray escape sequences

    def _auto_play(self, renderer: Renderer):
        import time
        for i in range(len(self.slides)):
            self.current = i
            self._draw(renderer)
            if i < len(self.slides) - 1:
                time.sleep(self.auto)
        # Pause at the end briefly
        time.sleep(2)


# ──────────────────────────────────────────────
# Demo slides (built-in sample)
# ──────────────────────────────────────────────

DEMO_SLIDES = """\
# Terminal Slides

A presentation tool that runs entirely in your terminal

---

## Why Terminal Slides?

* No GUI required — works over SSH
* Distraction-free presenting
* Markdown-based — use your favorite editor
* Lightweight and fast

???

Remember to mention SSH use-case for remote teams!

---

## Features

1. **Multiple themes** — dark, light, monochrome
2. `Inline code` highlighting
3. Code blocks with language labels
4. Beautiful blockquotes
5. Ordered and unordered lists
6. Speaker notes — press `n` to toggle
7. Links rendered inline

---

> The best presentations are the ones where the tool gets out of the way and lets your ideas shine.

---

## Code Blocks

```python
def greet(name: str) -> str:
    return f"Hello, {name}!"

print(greet("Terminal Slides"))
```

---

## Links & More

Learn more at [GitHub](https://github.com) or visit [Python.org](https://python.org)

---

---

## Keyboard Navigation

* `→` or `Space` — next slide
* `←` or `h` — previous slide
* `g` — first slide
* `G` — last slide
* `n` — toggle speaker notes
* `1`-`9` then `Enter` — jump to slide
* `r` — refresh (re-read terminal size)
* `q` — quit

---

# Thank You!

Built with ❤️ and ANSI escape codes

Try: `python slides.py demo --theme light`
"""

# ──────────────────────────────────────────────
# Export to plain text
# ──────────────────────────────────────────────

def export_text(slides: list[list[dict]], output: str, theme: str = "dark"):
    """Export slides to a plain-text file (ANSI codes stripped)."""
    renderer = Renderer(theme)
    lines = []
    for i, slide in enumerate(slides):
        rendered = renderer.render_slide(slide, i, len(slides), show_notes=True)
        # Strip ANSI codes for plain text
        clean = re.sub(r'\033\[[0-9;]*m', '', rendered)
        lines.append(clean)
        lines.append("\n" + "=" * 60 + "\n")
    with open(output, 'w') as f:
        f.write('\n'.join(lines))
    print(f"Exported {len(slides)} slides to {output}")


def list_slides(slides: list[list[dict]], parser: SlideParser):
    """Print slide titles to stdout."""
    titles = parser.get_slide_titles()
    for i, title in enumerate(titles):
        print(f"  {i+1:3d}. {title}")
    print(f"\n  Total: {len(titles)} slides")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Terminal Slides — Present Markdown slides in your terminal",
        prog="slides"
    )
    parser.add_argument("file", nargs="?", help="Markdown file with slides (separated by ---)")
    parser.add_argument("--theme", choices=list(THEMES.keys()), default="dark", help="Color theme (default: dark)")
    parser.add_argument("--auto", type=float, default=0, metavar="SECONDS", help="Auto-advance interval in seconds (0 = manual)")
    parser.add_argument("--export", metavar="FILE", help="Export slides to plain text file instead of presenting")
    parser.add_argument("--list", action="store_true", help="List slide titles and exit")
    parser.add_argument("--demo", action="store_true", help="Run the built-in demo presentation")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    args = parser.parse_args()

    if args.demo:
        md_text = DEMO_SLIDES
    elif args.file:
        try:
            with open(args.file, 'r') as f:
                md_text = f.read()
        except FileNotFoundError:
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        except PermissionError:
            print(f"Error: Permission denied: {args.file}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    parser_obj = SlideParser(md_text)
    slides = parser_obj.slides

    if not slides:
        print("No slides found. Separate slides with --- in your Markdown.", file=sys.stderr)
        sys.exit(1)

    if args.list:
        list_slides(slides, parser_obj)
        return

    if args.export:
        export_text(slides, args.export, args.theme)
    else:
        presenter = Presenter(slides, args.theme, args.auto)
        presenter.run()


if __name__ == "__main__":
    main()