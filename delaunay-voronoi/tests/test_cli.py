"""Tests for the CLI interface."""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from delaunay_voronoi.cli import main
from delaunay_voronoi.geometry import Point


class TestCLI:
    def test_diagram(self, tmp_path):
        out = str(tmp_path / "d.svg")
        main(["diagram", "-n", "10", "-w", "200", "--height", "150", "-o", out])
        assert os.path.exists(out)
        with open(out) as f:
            assert "<svg" in f.read()

    def test_info(self, capsys):
        main(["info", "-n", "10", "-w", "200", "--height", "150"])
        captured = capsys.readouterr()
        assert "Points:" in captured.out
        assert "Triangles:" in captured.out

    def test_mesh_stats(self, capsys):
        main(["mesh-stats", "-n", "10", "-w", "200", "--height", "150"])
        captured = capsys.readouterr()
        assert "MESH QUALITY REPORT" in captured.out

    def test_mesh_stats_json(self, tmp_path):
        out = str(tmp_path / "report.json")
        main(["mesh-stats", "-n", "10", "-w", "200", "--height", "150",
              "--json", "-o", out])
        assert os.path.exists(out)
        with open(out) as f:
            data = json.load(f)
        assert "num_points" in data

    def test_json(self, tmp_path):
        out = str(tmp_path / "mesh.json")
        main(["json", "-n", "10", "-w", "200", "--height", "150", "-o", out])
        assert os.path.exists(out)
        with open(out) as f:
            data = json.load(f)
        assert "points" in data
        assert "triangles" in data

    def test_from_json(self, tmp_path):
        # First save
        jpath = str(tmp_path / "mesh.json")
        main(["json", "-n", "10", "-w", "200", "--height", "150", "-o", jpath])
        # Then render from it
        spath = str(tmp_path / "rendered.svg")
        main(["from-json", jpath, "-o", spath])
        assert os.path.exists(spath)

    def test_nearest(self, capsys):
        main(["nearest", "-n", "10", "-w", "200", "--height", "150",
              "--x", "100", "--y", "75"])
        captured = capsys.readouterr()
        assert "Nearest site:" in captured.out

    def test_nearest_knn(self, capsys):
        main(["nearest", "-n", "10", "-w", "200", "--height", "150",
              "--x", "100", "--y", "75", "--knn", "3"])
        captured = capsys.readouterr()
        assert "k-NN" in captured.out

    def test_obj(self, tmp_path):
        out = str(tmp_path / "mesh.obj")
        main(["obj", "-n", "10", "-w", "200", "--height", "150", "-o", out])
        assert os.path.exists(out)
        with open(out) as f:
            content = f.read()
        assert "v " in content
        assert "f " in content

    def test_stl(self, tmp_path):
        out = str(tmp_path / "mesh.stl")
        main(["stl", "-n", "10", "-w", "200", "--height", "150", "-o", out])
        assert os.path.exists(out)
        with open(out) as f:
            content = f.read()
        assert "solid" in content

    def test_png(self, tmp_path):
        out = str(tmp_path / "voronoi.png")
        main(["png", "-n", "5", "-w", "50", "--height", "50", "-o", out])
        assert os.path.exists(out)
        with open(out, "rb") as f:
            assert f.read(8) == b"\x89PNG\r\n\x1a\n"

    def test_ppm(self, tmp_path):
        out = str(tmp_path / "voronoi.ppm")
        main(["ppm", "-n", "5", "-w", "50", "--height", "50", "-o", out])
        assert os.path.exists(out)
        with open(out, "rb") as f:
            assert f.read(3) == b"P6\n"

    def test_boundary(self, capsys):
        main(["boundary", "-n", "10", "-w", "200", "--height", "150"])
        captured = capsys.readouterr()
        assert "Boundary edges:" in captured.out
        assert "Boundary loops:" in captured.out

    def test_boundary_json(self, tmp_path):
        out = str(tmp_path / "boundary.json")
        main(["boundary", "-n", "10", "-w", "200", "--height", "150", "-o", out])
        assert os.path.exists(out)

    def test_compare(self, tmp_path):
        out = str(tmp_path / "compare.svg")
        main(["compare", "-n", "10", "-w", "200", "--height", "150",
              "--lloyd", "3", "-o", out])
        assert os.path.exists(out)

    def test_config_generate(self, tmp_path):
        out = str(tmp_path / "gen.json")
        main(["config", "-o", out])
        assert os.path.exists(out)
        with open(out) as f:
            data = json.load(f)
        assert "render" in data

    def test_refine(self, tmp_path):
        out = str(tmp_path / "refined.svg")
        main(["refine", "-n", "10", "-w", "200", "--height", "150",
              "--min-angle", "20", "-o", out])
        assert os.path.exists(out)

    def test_animate(self, tmp_path):
        out = str(tmp_path / "anim.svg")
        main(["animate", "-n", "5", "-w", "100", "--height", "80",
              "--lloyd", "3", "-o", out])
        assert os.path.exists(out)

    def test_no_command(self):
        with pytest.raises(SystemExit):
            main([])

    def test_help(self):
        with pytest.raises(SystemExit):
            main(["--help"])