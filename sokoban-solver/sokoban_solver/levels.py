"""Built-in Sokoban levels for demos and benchmarks."""

from __future__ import annotations

BUILTIN_LEVELS: dict[str, str] = {
    "tiny-one": """
#####
#@$.#
#####
""",
    "tiny-two": """
######
# .  #
# $$ #
# @. #
######
""",
    "corridor": """
########
#@ $ . #
#  ##  #
#      #
########
""",
    "room-shift": """
########
#   .  #
# $$   #
# # ## #
# @ .  #
########
""",
    "detour-two": """
#########
#@  #  .#
# $   $ #
#  ###  #
# .     #
#########
""",
    "mini-warehouse": """
#########
#   .   #
# $$#   #
# @   . #
#   #   #
#########
""",
}


def list_levels() -> list[str]:
    return sorted(BUILTIN_LEVELS)


def get_level(name: str) -> str:
    try:
        return BUILTIN_LEVELS[name]
    except KeyError as exc:  # pragma: no cover - tiny guard
        raise ValueError(f"unknown builtin level: {name}") from exc
