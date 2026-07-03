"""Tests for CLI new commands (analyze, pipeline) — v3.0.0."""

import sys, os, json, tempfile, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph_layout import save_edge_list, save_json, petersen_graph, path_graph
from graph_layout.cli import main


class TestCLIAnalyze:
    def test_analyze_bfs(self, capsys):
        g = path_graph(5)
        with tempfile.NamedTemporaryFile(suffix=".edges", mode="w", delete=False) as f:
            save_edge_list(g, f.name)
            path = f.name
        main(["analyze", path, "--analysis", "bfs", "--start", "0"])
        os.unlink(path)

    def test_analyze_dfs(self, capsys):
        g = path_graph(5)
        with tempfile.NamedTemporaryFile(suffix=".edges", mode="w", delete=False) as f:
            save_edge_list(g, f.name)
            path = f.name
        main(["analyze", path, "--analysis", "dfs", "--start", "0"])
        os.unlink(path)

    def test_analyze_dijkstra(self, capsys):
        g = path_graph(5)
        with tempfile.NamedTemporaryFile(suffix=".edges", mode="w", delete=False) as f:
            save_edge_list(g, f.name)
            path = f.name
        main(["analyze", path, "--analysis", "dijkstra", "--start", "0"])
        os.unlink(path)

    def test_analyze_degree(self, capsys):
        g = petersen_graph()
        with tempfile.NamedTemporaryFile(suffix=".edges", mode="w", delete=False) as f:
            save_edge_list(g, f.name)
            path = f.name
        main(["analyze", path, "--analysis", "degree"])
        os.unlink(path)

    def test_analyze_mst(self, capsys):
        g = petersen_graph()
        with tempfile.NamedTemporaryFile(suffix=".edges", mode="w", delete=False) as f:
            save_edge_list(g, f.name)
            path = f.name
        main(["analyze", path, "--analysis", "mst"])
        os.unlink(path)

    def test_analyze_cycle(self, capsys):
        g = path_graph(5)
        with tempfile.NamedTemporaryFile(suffix=".edges", mode="w", delete=False) as f:
            save_edge_list(g, f.name)
            path = f.name
        main(["analyze", path, "--analysis", "cycle"])
        os.unlink(path)

    def test_analyze_community(self, capsys):
        g = petersen_graph()
        with tempfile.NamedTemporaryFile(suffix=".edges", mode="w", delete=False) as f:
            save_edge_list(g, f.name)
            path = f.name
        main(["analyze", path, "--analysis", "community"])
        os.unlink(path)

    def test_analyze_closeness(self, capsys):
        g = petersen_graph()
        with tempfile.NamedTemporaryFile(suffix=".edges", mode="w", delete=False) as f:
            save_edge_list(g, f.name)
            path = f.name
        main(["analyze", path, "--analysis", "closeness"])
        os.unlink(path)

    def test_analyze_betweenness(self, capsys):
        g = petersen_graph()
        with tempfile.NamedTemporaryFile(suffix=".edges", mode="w", delete=False) as f:
            save_edge_list(g, f.name)
            path = f.name
        main(["analyze", path, "--analysis", "betweenness"])
        os.unlink(path)


class TestCLIPipeline:
    def test_pipeline_petersen(self, tmp_path):
        config = {
            "graph": {"generator": "petersen"},
            "layout": {"algorithm": "fr", "width": 600, "height": 400, "seed": 42},
            "render": {"format": "svg", "output": str(tmp_path / "out.svg")},
            "metrics": True,
        }
        cfg_path = str(tmp_path / "config.json")
        with open(cfg_path, "w") as f:
            json.dump(config, f)
        main(["pipeline", cfg_path])
        assert os.path.exists(str(tmp_path / "out.svg"))

    def test_pipeline_html_output(self, tmp_path):
        config = {
            "graph": {"generator": "petersen"},
            "layout": {"algorithm": "drgraph", "width": 600, "height": 400, "seed": 42},
            "render": {"format": "html", "output": str(tmp_path / "out.html")},
            "metrics": False,
        }
        cfg_path = str(tmp_path / "config.json")
        with open(cfg_path, "w") as f:
            json.dump(config, f)
        main(["pipeline", cfg_path])
        assert os.path.exists(str(tmp_path / "out.html"))

    def test_pipeline_from_input(self, tmp_path):
        g = petersen_graph()
        edges_path = str(tmp_path / "graph.edges")
        save_edge_list(g, edges_path)
        config = {
            "graph": {"input": edges_path, "format": "edges"},
            "layout": {"algorithm": "circular", "width": 600, "height": 400},
            "render": {"format": "json", "output": str(tmp_path / "out.json")},
        }
        cfg_path = str(tmp_path / "config.json")
        with open(cfg_path, "w") as f:
            json.dump(config, f)
        main(["pipeline", cfg_path])
        assert os.path.exists(str(tmp_path / "out.json"))


class TestCLINewLayouts:
    def test_layout_drgraph(self, tmp_path):
        g = petersen_graph()
        edges_path = str(tmp_path / "graph.edges")
        save_edge_list(g, edges_path)
        out_path = str(tmp_path / "out.svg")
        main(["layout", edges_path, "-o", out_path, "-a", "drgraph"])
        assert os.path.exists(out_path)

    def test_layout_pivot_mds(self, tmp_path):
        g = petersen_graph()
        edges_path = str(tmp_path / "graph.edges")
        save_edge_list(g, edges_path)
        out_path = str(tmp_path / "out.svg")
        main(["layout", edges_path, "-o", out_path, "-a", "pivot-mds"])
        assert os.path.exists(out_path)

    def test_layout_html_output(self, tmp_path):
        g = petersen_graph()
        edges_path = str(tmp_path / "graph.edges")
        save_edge_list(g, edges_path)
        out_path = str(tmp_path / "out.html")
        main(["layout", edges_path, "-o", out_path, "-a", "fr",
              "--output-format", "html"])
        assert os.path.exists(out_path)

    def test_layout_matrix_output(self, tmp_path):
        g = petersen_graph()
        edges_path = str(tmp_path / "graph.edges")
        save_edge_list(g, edges_path)
        out_path = str(tmp_path / "out.svg")
        main(["layout", edges_path, "-o", out_path, "-a", "fr",
              "--output-format", "matrix"])
        assert os.path.exists(out_path)

    def test_compare_includes_new_layouts(self, capsys, tmp_path):
        g = petersen_graph()
        edges_path = str(tmp_path / "graph.edges")
        save_edge_list(g, edges_path)
        main(["compare", edges_path])
        captured = capsys.readouterr()
        assert "drgraph" in captured.out
        assert "pivot-mds" in captured.out