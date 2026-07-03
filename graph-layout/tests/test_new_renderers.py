"""Tests for new renderers (HTML, Matrix) and config — v3.0.0."""

import sys, os, json, tempfile, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph_layout import (
    Graph, HTMLRenderer, MatrixRenderer, SVGRenderer,
    FruchtermanReingold, petersen_graph,
    load_config, validate_config,
)


class TestHTMLRenderer:
    def test_html_basic(self):
        g = petersen_graph()
        FruchtermanReingold(seed=42, iterations=30).layout(g)
        html = HTMLRenderer(width=600, height=400).render(g)
        assert "<!DOCTYPE html>" in html
        assert "<svg" in html
        assert "</html>" in html

    def test_html_with_metrics(self):
        g = petersen_graph()
        FruchtermanReingold(seed=42, iterations=30).layout(g)
        html = HTMLRenderer(show_metrics=True).render(g)
        assert "Layout Metrics" in html
        assert "<table" in html

    def test_html_dark_theme(self):
        g = petersen_graph()
        FruchtermanReingold(seed=42, iterations=30).layout(g)
        html = HTMLRenderer(theme="dark").render(g)
        assert "#1a1a2e" in html

    def test_html_save(self):
        g = petersen_graph()
        FruchtermanReingold(seed=42, iterations=30).layout(g)
        with tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False) as f:
            HTMLRenderer().save(g, f.name)
            assert os.path.getsize(f.name) > 0
        os.unlink(f.name)


class TestMatrixRenderer:
    def test_matrix_basic(self):
        g = petersen_graph()
        svg = MatrixRenderer().render(g)
        assert "<svg" in svg
        assert "</svg>" in svg
        assert "rect" in svg

    def test_matrix_empty(self):
        g = Graph()
        svg = MatrixRenderer().render(g)
        assert "<svg" in svg

    def test_matrix_save(self):
        g = petersen_graph()
        with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False) as f:
            MatrixRenderer().save(g, f.name)
            assert os.path.getsize(f.name) > 0
        os.unlink(f.name)

    def test_matrix_labels(self):
        g = Graph()
        g.add_edge("A", "B")
        svg = MatrixRenderer(cell_size=30).render(g)
        assert "A" in svg
        assert "B" in svg


class TestConfig:
    def test_load_json_config(self, tmp_path):
        config = {
            "graph": {"generator": "petersen"},
            "layout": {"algorithm": "fr", "width": 800, "height": 600, "seed": 42},
            "render": {"format": "svg", "output": "out.svg"},
            "metrics": True,
        }
        cfg_path = str(tmp_path / "config.json")
        with open(cfg_path, "w") as f:
            json.dump(config, f)
        loaded = load_config(cfg_path)
        assert loaded["layout"]["algorithm"] == "fr"

    def test_validate_config_ok(self):
        validate_config({"layout": {"algorithm": "fr"}})

    def test_validate_config_missing_layout(self):
        with pytest.raises(ValueError):
            validate_config({"graph": {}})

    def test_validate_config_missing_algorithm(self):
        with pytest.raises(ValueError):
            validate_config({"layout": {}})

    def test_validate_config_not_dict(self):
        with pytest.raises(ValueError):
            validate_config("not a dict")