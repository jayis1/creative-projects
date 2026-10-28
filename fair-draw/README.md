# Fair Draw

Why this exists: round-robin fixture generators often treat home/away as decoration; Fair Draw constructs pair-complete schedules while balancing venue advantage, including leagues with an odd number of teams.

A standard-library Python toolkit for generating, rendering, and auditing a single round-robin tournament schedule.

## Try it

From the repository root:

```sh
python3 fair-draw/fair_draw.py
```

Pass team names directly:

```sh
python3 fair-draw/fair_draw.py Falcons Owls Tigers
```

## How it works

The circle method rotates teams around a fixed position. For an odd number of entrants it adds a bye, so each real team plays at most once per round. Home/away designation alternates deterministically. `audit()` checks complete unique pairings, valid teams, and one appearance per round, then reports home counts.

## Usage

Import `round_robin(teams)` to get a list of rounds containing `Match(round, home, away)` values. `audit(rounds, teams)` returns pairing and home/away metrics. The `--json` command-line option emits a machine-readable fixture and audit report. With no names the CLI uses a five-team sample league.

Input requires at least two non-empty unique team names. The project has no third-party dependencies.

## Tests

Run `python3 -m unittest discover -s fair-draw/tests -v` from the repository root.
