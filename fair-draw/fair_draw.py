"""Round-robin tournament fixture generation and fairness diagnostics."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class Match:
    round: int
    home: str
    away: str


def round_robin(teams: Sequence[str]) -> list[list[Match]]:
    """Build a single round robin using the circle method (bye for odd counts)."""
    names = list(teams)
    if len(names) < 2:
        raise ValueError("at least two teams are required")
    if len(set(names)) != len(names) or any(not n.strip() for n in names):
        raise ValueError("team names must be non-empty and unique")
    players: list[str | None] = names + ([None] if len(names) % 2 else [])
    rounds: list[list[Match]] = []
    for r in range(len(players) - 1):
        games: list[Match] = []
        for i in range(len(players) // 2):
            left, right = players[i], players[-1 - i]
            if left is not None and right is not None:
                home, away = (left, right) if (r + i) % 2 == 0 else (right, left)
                games.append(Match(r + 1, home, away))
        rounds.append(games)
        players = [players[0], players[-1], *players[1:-1]]
    return rounds


def audit(rounds: Sequence[Sequence[Match]], teams: Sequence[str]) -> dict[str, object]:
    """Return fixture invariants and per-team home/away counts."""
    appearances = {team: 0 for team in teams}
    home_counts = {team: 0 for team in teams}
    pairs: list[frozenset[str]] = []
    for games in rounds:
        playing: set[str] = set()
        for game in games:
            if game.home not in appearances or game.away not in appearances or game.home == game.away:
                raise ValueError("fixture contains an unknown or self-playing team")
            if game.home in playing or game.away in playing:
                raise ValueError("team appears more than once in a round")
            playing.update((game.home, game.away))
            appearances[game.home] += 1
            appearances[game.away] += 1
            home_counts[game.home] += 1
            pairs.append(frozenset((game.home, game.away)))
    expected = len(teams) * (len(teams) - 1) // 2
    if len(pairs) != expected or len(set(pairs)) != expected:
        raise ValueError("fixtures do not contain every pairing exactly once")
    return {"matches": len(pairs), "pairings_complete": True,
            "appearances_per_team": appearances,
            "home_matches": home_counts,
            "home_away_balance_spread": max(home_counts.values()) - min(home_counts.values())}


def render(rounds: Sequence[Sequence[Match]]) -> str:
    lines = []
    for idx, games in enumerate(rounds, 1):
        fixtures = " | ".join(f"{m.home} vs {m.away}" for m in games) or "BYE"
        lines.append(f"Round {idx}: {fixtures}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate fair round-robin fixtures")
    parser.add_argument("teams", nargs="*", help="team names (default: sample league)")
    parser.add_argument("--json", action="store_true", help="emit fixtures and audit as JSON")
    args = parser.parse_args(argv)
    teams = args.teams or ["Aster", "Birch", "Cedar", "Dune", "Elm"]
    try:
        rounds = round_robin(teams)
        report = audit(rounds, teams)
    except ValueError as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps({"rounds": [[asdict(m) for m in games] for games in rounds], "audit": report}, indent=2))
    else:
        print(render(rounds))
        print(f"\n{report['matches']} matches; home/away spread: {report['home_away_balance_spread']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
