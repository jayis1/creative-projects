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

    def test_bad_arm_rejected(self):
        with self.assertRaises(ValueError):
            Arm((1.0, 0.0), (0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
