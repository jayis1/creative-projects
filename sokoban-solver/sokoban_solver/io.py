"""Input helpers for single levels and multi-level packs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .levels import get_level


@dataclass(frozen=True)
class LevelEntry:
    title: str
    text: str


def read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def load_level_text(path: str | None, inline_level: str | None, builtin: str | None) -> str:
    selected = sum(1 for value in (path, inline_level, builtin) if value)
    if selected != 1:
        raise ValueError("provide exactly one of --file, --level, or --builtin")
    if path:
        return read_text(path)
    if inline_level:
        return inline_level.replace("\\n", "\n")
    assert builtin is not None
    return get_level(builtin)


def parse_level_pack(text: str) -> tuple[LevelEntry, ...]:
    """Parse a small Sokoban level pack.

    Format:
    - blank lines separate levels
    - optional title comments before a board can use `; title` or `title: ...`
    """

    entries: list[LevelEntry] = []
    title: str | None = None
    board_lines: list[str] = []

    def flush() -> None:
        nonlocal title, board_lines
        if not board_lines:
            title = None
            return
        block = "\n".join(board_lines).rstrip() + "\n"
        entries.append(LevelEntry(title=title or f"level-{len(entries) + 1}", text=block))
        title = None
        board_lines = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        if stripped.startswith(";") and not board_lines:
            title = stripped[1:].strip() or None
            continue
        if stripped.lower().startswith("title:") and not board_lines:
            title = stripped.split(":", 1)[1].strip() or None
            continue
        board_lines.append(line)
    flush()

    if not entries:
        raise ValueError("level pack is empty")
    return tuple(entries)
