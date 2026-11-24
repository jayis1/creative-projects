import unittest
from unittest.mock import patch

import cli


class CliTests(unittest.TestCase):
    def test_demo_has_half_adder_outputs(self):
        circuit, summed, carry = cli.demo(10)
        self.assertEqual((summed.value, carry.value), (1, 0))
        self.assertTrue(circuit.trace)

    def test_negative_time_rejected(self):
        with patch("sys.stderr"):
            with self.assertRaises(SystemExit) as ctx:
                cli.main("--until -1".split())
        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
