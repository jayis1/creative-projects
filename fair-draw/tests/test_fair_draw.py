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

    def test_invalid_teams_rejected(self):
        for teams in ([], ["solo"], ["A", "A"], ["A", " "]):
            with self.subTest(teams=teams), self.assertRaises(ValueError):
                round_robin(teams)


if __name__ == "__main__":
    unittest.main()
