import unittest
from solver import Game, attractor, solve

class SolverTests(unittest.TestCase):
    def test_single_even_self_loop(self):
        game = Game({0: 0}, {0: 2}, {0: (0,)})
        self.assertEqual(solve(game)[:2], ({0}, set()))

    def test_odd_cycle_wins_player_one(self):
        game = Game({0: 0}, {0: 3}, {0: (0,)})
        self.assertEqual(solve(game)[:2], (set(), {0}))

    def test_player_can_choose_winning_successor(self):
        game = Game({0: 0, 1: 0}, {0: 1, 1: 2}, {0: (0, 1), 1: (1,)})
        p0, p1, strategy = solve(game)
        self.assertEqual(p0, {0, 1})
        self.assertEqual(p1, set())

    def test_attractor_uses_universal_opponent_choices(self):
        game = Game({0: 1, 1: 0, 2: 0}, {0: 0, 1: 2, 2: 2}, {0: (1, 2), 1: (1,), 2: (2,)})
        self.assertEqual(attractor(game, {1}, 0, {0, 1, 2}), {1})

    def test_rejects_dead_end(self):
        with self.assertRaisesRegex(ValueError, "no outgoing"):
            solve(Game({0: 0}, {0: 0}, {0: ()}))

if __name__ == "__main__":
    unittest.main()
