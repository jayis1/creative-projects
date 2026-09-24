import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from resolver import PackageIndex, Requirement, ResolutionError, Resolver, Version


class ResolverTests(unittest.TestCase):
    def setUp(self):
        self.index = PackageIndex.from_dict({"packages": [
            {"name": "app", "version": "1.0.0", "dependencies": {"core": "^1.0.0", "plugin": ">=2.0.0"}},
            {"name": "core", "version": "1.1.0"},
            {"name": "core", "version": "1.0.0"},
            {"name": "plugin", "version": "2.1.0", "dependencies": {"core": "<1.1.0"}},
            {"name": "plugin", "version": "2.0.0", "dependencies": {"core": ">=1.1.0"}},
        ]})

    def test_version_ordering_and_prerelease(self):
        self.assertLess(Version.parse("1.0.0-alpha"), Version.parse("1.0.0"))
        self.assertGreater(Version.parse("2.0.0"), Version.parse("1.9.9"))

    def test_requirement_ranges(self):
        self.assertTrue(Requirement("x", "^1.2.0").matches(Version.parse("1.9.0")))
        self.assertFalse(Requirement("x", "^1.2.0").matches(Version.parse("2.0.0")))
        self.assertTrue(Requirement("x", "1.x").matches(Version.parse("1.8.2")))

    def test_backtracking_finds_compatible_plugin(self):
        result = Resolver(self.index).resolve([Requirement("app", "=1.0.0")])
        self.assertEqual(str(result["plugin"].version), "2.0.0")
        self.assertEqual(str(result["core"].version), "1.1.0")

    def test_conflict_is_reported(self):
        index = PackageIndex.from_dict({"packages": [
            {"name": "a", "version": "1.0.0", "dependencies": {"x": "^1.0.0"}},
            {"name": "b", "version": "1.0.0", "dependencies": {"x": "^2.0.0"}},
            {"name": "x", "version": "1.0.0"}, {"name": "x", "version": "2.0.0"},
        ]})
        with self.assertRaises(ResolutionError):
            Resolver(index).resolve([Requirement("a"), Requirement("b")])

    def test_cli_outputs_sorted_lock(self):
        document = {"dependencies": {"app": "1.0.0"}, "packages": [
            {"name": "app", "version": "1.0.0"}
        ]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            run = subprocess.run([sys.executable, str(Path(__file__).parents[1] / "resolver.py"), str(path)], capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(run.stdout), {"app": "1.0.0"})


if __name__ == "__main__":
    unittest.main()
