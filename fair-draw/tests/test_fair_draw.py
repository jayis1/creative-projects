import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fair_draw import audit, round_robin


class RoundRobinTests(unittest.TestCase):
    def test_even_league_has_all_unique_pairs(self):
        teams = ["A", "B", "C", "D"]
        rounds = round_robin(teams)
        report = audit(rounds, teams)
        self.assertEqual(len(rounds), 3)
        self.assertEqual(report["matches"], 6)
        self.assertTrue(report["pairings_complete"])

    def test_odd_league_has_byes_and_one_game_per_team_per_round(self):
        teams = ["A", "B", "C", "D", "E"]
        rounds = round_robin(teams)
        self.assertEqual([len(r) for r in rounds], [2] * 5)
        for games in rounds:
            playing = [team for match in games for team in (match.home, match.away)]
            self.assertEqual(len(playing), len(set(playing)))
        self.assertEqual(audit(rounds, teams)["matches"], 10)

    def test_double_round_robin_swaps_venues_and_doubles_games(self):
        from fair_draw import double_round_robin
        teams = ["A", "B", "C", "D", "E"]
        rounds = double_round_robin(teams)
        half = len(rounds) // 2
        self.assertEqual(len(rounds), 10)
        for first, second in zip(rounds[:half], rounds[half:]):
            self.assertEqual([(m.home, m.away) for m in first],
                             [(m.away, m.home) for m in second])
        self.assertEqual(audit(rounds, teams, double=True)["matches"], 20)

    def test_audit_rejects_double_fixture_without_reversed_return_venue(self):
        from fair_draw import Match
        rounds = [[Match(1, "A", "B")], [Match(2, "A", "B")]]
        with self.assertRaisesRegex(ValueError, "both venues"):
            audit(rounds, ["A", "B"], double=True)

    def test_invalid_teams_rejected(self):
        for teams in ([], ["solo"], ["A", "A"], ["A", " "]):
            with self.subTest(teams=teams), self.assertRaises(ValueError):
                round_robin(teams)


if __name__ == "__main__":
    unittest.main()
