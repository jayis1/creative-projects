from __future__ import annotations

import json
import unittest

from citygen.analysis import compute_stats, shortest_path, validate_city
from citygen.generator import CityMap, Point, Tile, generate_city
from citygen.render import render_ascii, render_svg


class CityGenTests(unittest.TestCase):
    def test_generation_is_reproducible(self) -> None:
        a = generate_city(width=21, height=17, seed=7, mode="grid", iterations=20)
        b = generate_city(width=21, height=17, seed=7, mode="grid", iterations=20)
        self.assertEqual(a.to_dict(), b.to_dict())

    def test_invalid_size_raises(self) -> None:
        with self.assertRaises(ValueError):
            generate_city(width=5, height=17)

    def test_invalid_zone_weight_raises(self) -> None:
        with self.assertRaises(ValueError):
            generate_city(width=21, height=17, zone_weights={"commercial": -1.0})

    def test_json_round_trip(self) -> None:
        city = generate_city(width=21, height=17, seed=11, mode="organic", iterations=15)
        restored = CityMap.from_dict(json.loads(city.to_json()))
        self.assertEqual(city.to_dict(), restored.to_dict())

    def test_renderers_emit_expected_markers(self) -> None:
        city = generate_city(width=13, height=11, seed=3)
        self.assertIn("#", render_ascii(city))
        self.assertIn("<svg", render_svg(city))
        self.assertIn("Road", render_svg(city))

    def test_stats_cover_entire_grid(self) -> None:
        city = generate_city(width=19, height=19, seed=2)
        stats = compute_stats(city)
        self.assertEqual(sum(stats["counts"].values()), city.width * city.height)
        self.assertGreater(stats["road_cells"], 0)
        self.assertIn("issues", stats)

    def test_road_neighbors_detect_cross(self) -> None:
        city = CityMap(9, 9)
        cross = [Point(4, 4), Point(4, 3), Point(4, 5), Point(3, 4), Point(5, 4)]
        for point in cross:
            city.set_tile(point, Tile.ROAD)
        center = Point(4, 4)
        self.assertEqual(len(city.road_neighbors(center)), 4)

    def test_radial_mode_places_civic_landmarks(self) -> None:
        city = generate_city(width=29, height=29, seed=5, mode="radial", iterations=30, landmark_count=3)
        self.assertEqual(city.mode, "radial")
        self.assertGreaterEqual(len(city.metadata["landmarks"]), 1)
        self.assertGreater(len(city.tile_points(Tile.CIVIC)), 0)

    def test_shortest_path_finds_contiguous_route(self) -> None:
        city = CityMap(9, 9)
        road = [Point(1, 1), Point(2, 1), Point(3, 1), Point(3, 2), Point(3, 3)]
        for point in road:
            city.set_tile(point, Tile.ROAD)
        path = shortest_path(city, Point(1, 1), Point(3, 3))
        self.assertEqual(path[0], Point(1, 1))
        self.assertEqual(path[-1], Point(3, 3))
        self.assertEqual(len(path), 5)

    def test_validate_city_reports_disconnected_roads(self) -> None:
        city = CityMap(9, 9)
        city.set_tile(Point(1, 1), Tile.ROAD)
        city.set_tile(Point(7, 7), Tile.ROAD)
        issues = validate_city(city)
        self.assertTrue(any("disconnected" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
