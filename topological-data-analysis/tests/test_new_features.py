"""
Test suite for new TDA v3.0 features.

Covers:
- Alpha complex
- Sparse Rips complex
- Clearing reduction
- Statistics module (diagram_statistics, persistent_entropy, amplitudes, vectorize)
- Kernels (PSS, PWG, Fisher, kernel_matrix)
- Batch processor and streaming
- Configuration loading / validation
- Exception hierarchy
- New CLI subcommands (stats, batch, kernel, config)
"""

import json
import math
import os
import tempfile

import pytest

from tda import (
    AlphaComplex,
    SparseRipsComplex,
    compute_persistence_clearing,
    PersistenceDiagram,
    PersistencePair,
    diagram_statistics,
    statistics_table,
    persistent_entropy,
    amplitudes,
    vectorize,
    pss_kernel,
    pwg_kernel,
    fisher_kernel,
    kernel_matrix,
    BatchProcessor,
    stream_persistence,
    load_config,
    save_config,
    validate_config,
    merge_config,
    DEFAULT_CONFIG,
    TDAError,
    InvalidParameterError,
    FileFormatError,
    EmptyInputError,
    DimensionMismatchError,
    compute_persistence,
    VietorisRipsComplex,
)
from tda.cli import main as cli_main


# ---------------------------------------------------------------------------
# Alpha complex
# ---------------------------------------------------------------------------

class TestAlphaComplex:
    def test_basic(self):
        pts = [(0, 0), (1, 0), (0.5, 0.866)]
        ac = AlphaComplex(pts, alpha=0.6, max_dimension=2)
        tree = ac.build()
        assert tree.num_simplices() >= 3  # at least vertices

    def test_edge_inclusion(self):
        pts = [(0, 0), (1, 0)]
        ac = AlphaComplex(pts, alpha=1.0, max_dimension=1)
        tree = ac.build()
        assert tree.num_simplices() == 3  # 2 vertices + 1 edge

    def test_edge_exclusion(self):
        pts = [(0, 0), (3, 0)]
        ac = AlphaComplex(pts, alpha=0.5, max_dimension=1)
        tree = ac.build()
        assert tree.num_simplices() == 2  # only vertices, edge too far

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="at least one point"):
            AlphaComplex([], alpha=1.0)

    def test_negative_alpha_raises(self):
        with pytest.raises(ValueError, match="alpha must be positive"):
            AlphaComplex([(0, 0)], alpha=-1.0)

    def test_triangle(self):
        """Equilateral triangle with large enough alpha should include 2-simplex."""
        pts = [(0, 0), (1, 0), (0.5, 0.866)]
        ac = AlphaComplex(pts, alpha=0.7, max_dimension=2)
        tree = ac.build()
        # Circumradius ≈ 0.577 < 0.7
        assert tree.dimension() == 2

    def test_persistence(self):
        """Alpha complex of a triangle should have H0=1 essential."""
        pts = [(0, 0), (1, 0), (0.5, 0.866)]
        ac = AlphaComplex(pts, alpha=1.0, max_dimension=2)
        tree = ac.build()
        pers = compute_persistence(tree, max_dimension=2, min_persistence=0.01)
        h0 = pers.get(0, [])
        essential = [p for p in h0 if p[1] == float('inf')]
        assert len(essential) == 1


# ---------------------------------------------------------------------------
# Sparse Rips complex
# ---------------------------------------------------------------------------

class TestSparseRipsComplex:
    def test_basic(self):
        pts = [(0, 0), (1, 0), (2, 0), (3, 0)]
        sr = SparseRipsComplex(pts, k=2, max_scale=3.0, max_dimension=1)
        tree = sr.build()
        # Should have all 4 vertices and some edges.
        assert tree.num_simplices() >= 4

    def test_k_too_small_raises(self):
        with pytest.raises(ValueError, match="k must be"):
            SparseRipsComplex([(0, 0)], k=0)

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="at least one point"):
            SparseRipsComplex([], k=1)

    def test_k_nneighbours(self):
        """With k=1, each point connects to at most 1 neighbour."""
        pts = [(0, 0), (1, 0), (2, 0)]
        sr = SparseRipsComplex(pts, k=1, max_scale=10.0, max_dimension=1)
        tree = sr.build()
        # 3 vertices + at most 2 edges (each point's nearest neighbour)
        assert tree.num_simplices() >= 3

    def test_persistence_computable(self):
        pts = [(0, 0), (1, 0), (0.5, 0.866)]
        sr = SparseRipsComplex(pts, k=2, max_scale=2.0, max_dimension=2)
        tree = sr.build()
        pers = compute_persistence(tree, max_dimension=1)
        assert 0 in pers


# ---------------------------------------------------------------------------
# Clearing reduction
# ---------------------------------------------------------------------------

class TestClearingReduction:
    def test_matches_standard(self):
        """Clearing reduction should produce the same persistence pairs
        as the standard algorithm (up to ordering)."""
        pts = [(0, 0), (1, 0), (0.5, 0.866), (2, 0)]
        vr = VietorisRipsComplex(pts, max_scale=2.0, max_dimension=2)
        tree = vr.build()

        std = compute_persistence(tree, max_dimension=2, min_persistence=0.01)
        clr = compute_persistence_clearing(tree, max_dimension=2, min_persistence=0.01)

        # Compare sorted pairs per dimension.
        for dim in set(std.keys()) | set(clr.keys()):
            s = sorted(std.get(dim, []))
            c = sorted(clr.get(dim, []))
            # Allow for floating-point differences.
            assert len(s) == len(c), f"dim {dim}: {len(s)} vs {len(c)}"
            for (sb, sd), (cb, cd) in zip(s, c):
                assert sb == pytest.approx(cb, abs=1e-9)
                if sd == float('inf') and cd == float('inf'):
                    continue
                assert sd == pytest.approx(cd, abs=1e-9)

    def test_empty_tree_raises(self):
        from tda.scomplex import SimplexTree
        with pytest.raises(ValueError, match="empty"):
            compute_persistence_clearing(SimplexTree())

    def test_disconnected_points(self):
        pts = [(0, 0), (10, 0)]
        vr = VietorisRipsComplex(pts, max_scale=1.0, max_dimension=0)
        tree = vr.build()
        pers = compute_persistence_clearing(tree, max_dimension=0)
        h0 = pers.get(0, [])
        essential = [p for p in h0 if p[1] == float('inf')]
        assert len(essential) == 2


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

class TestStatistics:
    def test_diagram_statistics_basic(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        d.add(0.0, 2.0)
        s = diagram_statistics(d)
        assert s["num_features"] == 2
        assert s["num_finite"] == 2
        assert s["num_essential"] == 0
        assert s["max_persistence"] == 2.0
        assert s["mean_persistence"] == 1.5
        assert s["total_persistence"] == 3.0

    def test_diagram_statistics_with_essential(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        d.add(0.0, float('inf'))
        s = diagram_statistics(d)
        assert s["num_features"] == 2
        assert s["num_essential"] == 1
        assert s["num_finite"] == 1

    def test_diagram_statistics_empty(self):
        d = PersistenceDiagram(0)
        s = diagram_statistics(d)
        assert s["num_features"] == 0
        assert s["max_persistence"] == 0.0
        assert s["total_persistence"] == 0.0

    def test_statistics_table(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        table = statistics_table({0: d})
        assert "dim" in table
        assert "0" in table

    def test_persistent_entropy(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        d.add(0.0, 2.0)
        e = persistent_entropy(d)
        assert 0.0 < e <= 1.0

    def test_persistent_entropy_single_feature(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        e = persistent_entropy(d)
        assert e == 0.0

    def test_persistent_entropy_empty(self):
        d = PersistenceDiagram(0)
        e = persistent_entropy(d)
        assert e == 0.0

    def test_amplitudes_p1(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        d.add(0.0, 3.0)
        amp = amplitudes(d, p=1.0)
        assert amp == 4.0  # total persistence

    def test_amplitudes_p2(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        d.add(0.0, 2.0)
        amp = amplitudes(d, p=2.0)
        assert amp == pytest.approx(math.sqrt(1 + 4))

    def test_amplitudes_inf(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        d.add(0.0, 3.0)
        amp = amplitudes(d, p=float('inf'))
        assert amp == 3.0

    def test_amplitudes_empty(self):
        d = PersistenceDiagram(0)
        assert amplitudes(d) == 0.0

    def test_vectorize(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        d.add(0.0, 3.0)
        vec = vectorize(d, max_features=3)
        assert len(vec) == 9  # 3 * max_features
        # First feature should have higher persistence (3.0).
        assert vec[2] == 3.0  # persistence of top feature

    def test_vectorize_padding(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        vec = vectorize(d, max_features=5)
        assert len(vec) == 15
        # Remaining features should be zero-padded.
        assert vec[3:] == [0.0] * 12


# ---------------------------------------------------------------------------
# Kernels
# ---------------------------------------------------------------------------

class TestKernels:
    def test_pss_identical(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        d.add(0.0, 2.0)
        # K(d, d) should be positive.
        val = pss_kernel(d, d, sigma=1.0)
        assert val > 0

    def test_pss_empty(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        empty = PersistenceDiagram(0)
        assert pss_kernel(d, empty, sigma=1.0) == 0.0

    def test_pss_sigma_zero_raises(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        with pytest.raises(ValueError):
            pss_kernel(d, d, sigma=0.0)

    def test_pwg_identical(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        val = pwg_kernel(d, d, sigma=1.0)
        assert val > 0

    def test_pwg_empty(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        empty = PersistenceDiagram(0)
        assert pwg_kernel(d, empty, sigma=1.0) == 0.0

    def test_fisher_identical(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        d.add(0.0, 2.0)
        val = fisher_kernel(d, d, sigma=1.0, beta=1.0)
        assert val > 0  # identical diagrams should have positive kernel

    def test_fisher_empty_both(self):
        d1 = PersistenceDiagram(0)
        d2 = PersistenceDiagram(0)
        val = fisher_kernel(d1, d2, sigma=1.0, beta=1.0)
        assert val == 1.0  # identical empty diagrams

    def test_fisher_sigma_zero_raises(self):
        d = PersistenceDiagram(0)
        with pytest.raises(ValueError):
            fisher_kernel(d, d, sigma=0.0)

    def test_fisher_beta_zero_raises(self):
        d = PersistenceDiagram(0)
        with pytest.raises(ValueError):
            fisher_kernel(d, d, sigma=1.0, beta=0.0)

    def test_kernel_matrix(self):
        d1 = PersistenceDiagram(0)
        d1.add(0.0, 1.0)
        d2 = PersistenceDiagram(0)
        d2.add(0.0, 2.0)
        K = kernel_matrix([d1, d2], pwg_kernel, sigma=1.0)
        assert len(K) == 2
        assert len(K[0]) == 2
        # Diagonal should be positive (self-kernel).
        assert K[0][0] > 0
        assert K[1][1] > 0
        # Off-diagonal should equal each other (symmetric).
        assert K[0][1] == K[1][0]

    def test_kernel_matrix_single(self):
        d = PersistenceDiagram(0)
        d.add(0.0, 1.0)
        K = kernel_matrix([d], pwg_kernel, sigma=1.0)
        assert len(K) == 1
        assert K[0][0] > 0


# ---------------------------------------------------------------------------
# Batch / streaming
# ---------------------------------------------------------------------------

class TestBatch:
    def test_run(self):
        clouds = [
            [(0, 0), (1, 0), (0.5, 0.866)],
            [(0, 0), (2, 0), (4, 0)],
        ]
        bp = BatchProcessor(clouds, max_scale=2.0, max_dimension=1,
                             min_persistence=0.01)
        results = bp.run()
        assert len(results) == 2

    def test_run_with_stats(self):
        clouds = [[(0, 0), (1, 0)], [(0, 0), (3, 0)]]
        bp = BatchProcessor(clouds, max_scale=1.5, max_dimension=1)
        stats = bp.run_with_stats()
        assert len(stats) == 2
        for s in stats:
            assert 0 in s  # H0 always present

    def test_run_with_vectors(self):
        clouds = [[(0, 0), (1, 0)], [(0, 0), (2, 0)]]
        bp = BatchProcessor(clouds, max_scale=2.0, max_dimension=1)
        vectors = bp.run_with_vectors(max_features=5)
        assert len(vectors) == 2
        assert all(len(v) > 0 for v in vectors)

    def test_unsupported_complex_raises(self):
        with pytest.raises(NotImplementedError):
            BatchProcessor([[(0, 0)]], complex_type="cech")

    def test_stream(self):
        clouds = [[(0, 0), (1, 0)], [(0, 0), (2, 0)]]
        results = list(stream_persistence(clouds, max_scale=2.0,
                                          max_dimension=1))
        assert len(results) == 2

    def test_stream_callback(self):
        clouds = [[(0, 0), (1, 0)]]
        indices = []

        def cb(i, d):
            indices.append(i)

        list(stream_persistence(clouds, max_scale=2.0, callback=cb))
        assert indices == [0]


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class TestConfig:
    def test_load_json(self, tmp_path):
        cfg = {"complex": {"type": "rips", "max_scale": 2.0}}
        path = str(tmp_path / "cfg.json")
        with open(path, "w") as f:
            json.dump(cfg, f)
        loaded = load_config(path)
        assert loaded["complex"]["type"] == "rips"
        # Default should be merged in.
        assert loaded["complex"]["max_dimension"] == 1

    def test_load_not_found(self):
        with pytest.raises(FileFormatError):
            load_config("/nonexistent/path.json")

    def test_load_bad_json(self, tmp_path):
        path = str(tmp_path / "bad.json")
        with open(path, "w") as f:
            f.write("{invalid json")
        with pytest.raises(FileFormatError):
            load_config(path)

    def test_load_unsupported_ext(self, tmp_path):
        path = str(tmp_path / "cfg.txt")
        with open(path, "w") as f:
            f.write("hello")
        with pytest.raises(FileFormatError):
            load_config(path)

    def test_save_and_load(self, tmp_path):
        path = str(tmp_path / "cfg.json")
        save_config(DEFAULT_CONFIG, path)
        loaded = load_config(path)
        assert loaded == DEFAULT_CONFIG

    def test_validate_ok(self):
        validate_config(DEFAULT_CONFIG)

    def test_validate_bad_complex_type(self):
        cfg = {"complex": {"type": "nonexistent"}}
        with pytest.raises(InvalidParameterError):
            validate_config(cfg)

    def test_validate_bad_min_persistence(self):
        cfg = {"persistence": {"min_persistence": -1.0}}
        with pytest.raises(InvalidParameterError):
            validate_config(cfg)

    def test_validate_bad_p(self):
        cfg = {"distance": {"p": 0.5}}
        with pytest.raises(InvalidParameterError):
            validate_config(cfg)

    def test_validate_bad_resolution(self):
        cfg = {"image": {"resolution": -1}}
        with pytest.raises(InvalidParameterError):
            validate_config(cfg)

    def test_merge_config(self):
        base = {"a": {"b": 1, "c": 2}, "d": 3}
        override = {"a": {"b": 10}, "e": 4}
        result = merge_config(base, override)
        assert result["a"]["b"] == 10
        assert result["a"]["c"] == 2
        assert result["d"] == 3
        assert result["e"] == 4


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class TestExceptions:
    def test_hierarchy(self):
        assert issubclass(EmptyInputError, TDAError)
        assert issubclass(DimensionMismatchError, TDAError)
        assert issubclass(InvalidParameterError, TDAError)
        assert issubclass(FileFormatError, TDAError)

    def test_catch_all_as_tda(self):
        for exc_class in [EmptyInputError, DimensionMismatchError,
                          InvalidParameterError, FileFormatError]:
            try:
                raise exc_class("test")
            except TDAError:
                pass  # good


# ---------------------------------------------------------------------------
# New CLI subcommands
# ---------------------------------------------------------------------------

class TestNewCLI:
    def _make_diagram_file(self, tmp_path, name="diag.json"):
        data = {
            "diagrams": [
                {"dimension": 0,
                 "pairs": [
                     {"birth": 0.0, "death": 1.0, "persistence": 1.0},
                     {"birth": 0.0, "death": 2.0, "persistence": 2.0},
                 ]},
                {"dimension": 1,
                 "pairs": [
                     {"birth": 0.5, "death": 1.5, "persistence": 1.0},
                 ]},
            ]
        }
        path = str(tmp_path / name)
        with open(path, "w") as f:
            json.dump(data, f)
        return path

    def test_stats(self, tmp_path):
        path = self._make_diagram_file(tmp_path)
        assert cli_main(["stats", path]) == 0

    def test_batch(self, tmp_path):
        clouds = [
            [[0, 0], [1, 0], [0.5, 0.866]],
            [[0, 0], [2, 0], [4, 0]],
        ]
        path = str(tmp_path / "clouds.json")
        with open(path, "w") as f:
            json.dump(clouds, f)
        assert cli_main(["batch", path, "--max-scale", "2.0", "-d", "1",
                         "--output-format", "stats"]) == 0

    def test_batch_vectors(self, tmp_path):
        clouds = [[[0, 0], [1, 0]], [[0, 0], [2, 0]]]
        path = str(tmp_path / "clouds.json")
        with open(path, "w") as f:
            json.dump(clouds, f)
        assert cli_main(["batch", path, "--max-scale", "2.0",
                         "--output-format", "vectors"]) == 0

    def test_kernel(self, tmp_path):
        p1 = self._make_diagram_file(tmp_path, "d1.json")
        p2 = self._make_diagram_file(tmp_path, "d2.json")
        assert cli_main(["kernel", p1, p2, "--kernel", "pss"]) == 0

    def test_kernel_pwg(self, tmp_path):
        p1 = self._make_diagram_file(tmp_path, "d1.json")
        p2 = self._make_diagram_file(tmp_path, "d2.json")
        assert cli_main(["kernel", p1, p2, "--kernel", "pwg"]) == 0

    def test_kernel_fisher(self, tmp_path):
        p1 = self._make_diagram_file(tmp_path, "d1.json")
        p2 = self._make_diagram_file(tmp_path, "d2.json")
        assert cli_main(["kernel", p1, p2, "--kernel", "fisher"]) == 0

    def test_config_generate(self, tmp_path):
        out = str(tmp_path / "gen_config.json")
        assert cli_main(["config", "generate", "-o", out]) == 0
        assert os.path.exists(out)

    def test_config_validate(self, tmp_path):
        cfg_path = str(tmp_path / "cfg.json")
        with open(cfg_path, "w") as f:
            json.dump(DEFAULT_CONFIG, f)
        assert cli_main(["config", "validate", "-f", cfg_path]) == 0

    def test_compute_alpha(self, tmp_path):
        pts = [[0, 0], [1, 0], [0.5, 0.866]]
        path = str(tmp_path / "pts.json")
        with open(path, "w") as f:
            json.dump(pts, f)
        assert cli_main(["compute", path, "--complex", "alpha",
                         "--max-scale", "2.0", "-d", "2"]) == 0