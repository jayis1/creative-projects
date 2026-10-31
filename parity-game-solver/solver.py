"""Solve finite parity games using Zielonka's recursive attractor algorithm."""
from __future__ import annotations
import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

@dataclass(frozen=True)
class Game:
    owners: Mapping[int, int]
    priorities: Mapping[int, int]
    edges: Mapping[int, tuple[int, ...]]

    def validate(self) -> None:
        vertices = set(self.owners)
        if not vertices or set(self.priorities) != vertices or set(self.edges) != vertices:
            raise ValueError("owners, priorities, and edges must define the same non-empty vertices")
        if any(o not in (0, 1) for o in self.owners.values()):
            raise ValueError("each owner must be player 0 or 1")
        if any(not isinstance(p, int) or p < 0 for p in self.priorities.values()):
            raise ValueError("priorities must be non-negative integers")
        for v, successors in self.edges.items():
            if not successors:
                raise ValueError(f"vertex {v} has no outgoing edge")
            if any(w not in vertices for w in successors):
                raise ValueError(f"vertex {v} references an unknown successor")

def attractor(game: Game, target: set[int], player: int, universe: set[int]) -> set[int]:
    """Least fixed point of vertices from which player can force reaching target."""
    result = set(target) & universe
    changed = True
    while changed:
        changed = False
        for v in universe - result:
            successors = [w for w in game.edges[v] if w in universe]
            if (game.owners[v] == player and any(w in result for w in successors)) or (
                game.owners[v] != player and successors and all(w in result for w in successors)
            ):
                result.add(v)
                changed = True
    return result

def solve(game: Game) -> tuple[set[int], set[int], dict[int, int]]:
    """Return winning regions for players 0/1 and a positional strategy map."""
    game.validate()
    strategy: dict[int, int] = {}
    def recurse(universe: set[int]) -> tuple[set[int], set[int]]:
        if not universe:
            return set(), set()
        top = max(game.priorities[v] for v in universe)
        player = top % 2
        top_vertices = {v for v in universe if game.priorities[v] == top}
        attr = attractor(game, top_vertices, player, universe)
        p0, p1 = recurse(universe - attr)
        opponent_region = p1 if player == 0 else p0
        if not opponent_region:
            for v in attr:
                if game.owners[v] == player:
                    choices = [w for w in game.edges[v] if w in attr]
                    if choices:
                        strategy[v] = min(choices)
            return (p0 | attr, p1) if player == 0 else (p0, p1 | attr)
        counter = attractor(game, opponent_region, 1 - player, universe)
        q0, q1 = recurse(universe - counter)
        if player == 0:
            return q0, q1 | counter
        return q0 | counter, q1
    p0, p1 = recurse(set(game.owners))
    return p0, p1, strategy

def load_game(path: Path) -> Game:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        game = Game({int(k): v for k, v in data["owners"].items()},
                    {int(k): v for k, v in data["priorities"].items()},
                    {int(k): tuple(v) for k, v in data["edges"].items()})
        game.validate()
        return game
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid game file: {exc}") from exc

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game", type=Path, help="JSON game description")
    args = parser.parse_args(argv)
    try:
        game = load_game(args.game)
        p0, p1, strategy = solve(game)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    print(json.dumps({"player0": sorted(p0), "player1": sorted(p1),
                      "strategy": {str(k): v for k, v in sorted(strategy.items())}}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
