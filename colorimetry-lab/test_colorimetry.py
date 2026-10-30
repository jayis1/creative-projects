import unittest

from colorimetry import rgb_to_lab, srgb_to_xyz, xyz_to_lab


class ConversionTests(unittest.TestCase):
    def test_black_maps_to_zero(self):
        self.assertEqual(srgb_to_xyz((0, 0, 0)), (0.0, 0.0, 0.0))
        self.assertAlmostEqual(rgb_to_lab((0, 0, 0))[0], 0.0)

    def test_srgb_red_reference(self):
        xyz = srgb_to_xyz((1, 0, 0))
        for got, want in zip(xyz, (0.4124564, 0.2126729, 0.0193339)):
            self.assertAlmostEqual(got, want, places=7)
        lab = rgb_to_lab((1, 0, 0))
        for got, want in zip(lab, (53.2408, 80.0925, 67.2032)):
            self.assertAlmostEqual(got, want, places=3)

    def test_xyz_lab_white(self):
        lab = xyz_to_lab((0.95047, 1.0, 1.08883))
        self.assertAlmostEqual(lab[0], 100.0, places=6)
        self.assertAlmostEqual(lab[1], 0.0, places=6)
        self.assertAlmostEqual(lab[2], 0.0, places=6)

    def test_rejects_bad_rgb(self):
        for rgb in ((-0.1, 0, 0), (1.1, 0, 0), (float("nan"), 0, 0), (0, 0)):
            with self.subTest(rgb=rgb), self.assertRaises(ValueError):
                srgb_to_xyz(rgb)

    def test_delta_e76_known_distance(self):
        from colorimetry import delta_e76
        self.assertEqual(delta_e76((0, 0, 0), (3, 4, 0)), 5.0)
        self.assertEqual(delta_e76((1, 2, 3), (1, 2, 3)), 0.0)

    def test_delta_e76_rejects_unrepresentable_distance(self):
        from colorimetry import delta_e76
        with self.assertRaises(ValueError):
            delta_e76((1.7e308, 0, 0), (-1.7e308, 0, 0))


if __name__ == "__main__":
    unittest.main()
