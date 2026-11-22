import math
import unittest

from ik import Arm


class ArmTests(unittest.TestCase):
    def test_forward_kinematics(self):
        self.assertEqual(Arm((2.0, 1.0), (0.0, math.pi / 2)).joints(),
                         [(0.0, 0.0), (2.0, 0.0), (2.0, 1.0)])

    def test_solver_reaches_reachable_target(self):
        arm = Arm((1.0, 1.0, 0.7), (0.0, 0.0, 0.0))
        angles, error, _ = arm.solve((1.5, 1.2))
        self.assertLess(error, 1e-4)
        self.assertLess(math.dist(arm.joints(angles)[-1], (1.5, 1.2)), 1e-4)

    def test_unreachable_target_returns_best_effort(self):
        _, error, _ = Arm((1.0,), (0.0,)).solve((4.0, 0.0))
        self.assertAlmostEqual(error, 3.0)

    def test_joint_limits_are_respected(self):
        arm = Arm((1.0, 1.0), (0.0, 0.0))
        limits = ((-0.1, 0.1), (-0.2, 0.2))
        angles, _, _ = arm.solve((0.0, 2.0), joint_limits=limits)
        for angle, (low, high) in zip(angles, limits):
            self.assertLessEqual(low, angle)
            self.assertLessEqual(angle, high)

    def test_joint_limit_shape_and_order_are_validated(self):
        arm = Arm((1.0,), (0.0,))
        with self.assertRaises(ValueError):
            arm.solve((0.5, 0.5), joint_limits=())
        with self.assertRaises(ValueError):
            arm.solve((0.5, 0.5), joint_limits=((1.0, -1.0),))

    def test_cli_accepts_joint_limits_and_solver_controls(self):
        import json
        import subprocess
        import sys

        completed = subprocess.run(
            [sys.executable, "ik.py", "--lengths", "1,1", "--angles", "0,0",
             "--target", "0,1", "--damping", "0.1", "--max-step", "0.1",
             "--joint-limits", "[[-0.5,0.5],[-1,1]]"],
            check=True, capture_output=True, text=True,
        )
        result = json.loads(completed.stdout)
        self.assertEqual(len(result["angles_radians"]), 2)
        self.assertTrue(-0.5 <= result["angles_radians"][0] <= 0.5)
        self.assertTrue(-1.0 <= result["angles_radians"][1] <= 1.0)

    def test_cli_rejects_invalid_joint_limits(self):
        import subprocess
        import sys

        completed = subprocess.run(
            [sys.executable, "ik.py", "--joint-limits", "not-json"],
            capture_output=True, text=True,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("expecting value", completed.stderr.lower())

    def test_bad_arm_rejected(self):
        with self.assertRaises(ValueError):
            Arm((1.0, 0.0), (0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
