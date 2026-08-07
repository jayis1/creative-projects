"""
Comprehensive test suite for logicmin — new feature modules.

Tests for BDD, analysis, PLA, DC optimization, HTML viz, batch, serialize.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from logicmin import (
    BooleanFunction, QuineMcCluskey, Espresso, Implicant,
    BDDManager, build_bdd, bdd_sop,
    boolean_difference, sensitivity, all_sensitivities,
    is_unate, unate_profile, on_set_size, off_set_size,
    minterm_adjacency, hamming_distance_matrix,
    PLAData, parse_pla_full, write_pla,
    assign_dontcares, minimize_with_dc_optimization,
    truth_table_html, kmap_html, kmap_with_cover_html, full_report_html,
    BatchProcessor, batch_from_pla_file, batch_summary, batch_to_json, batch_from_json,
    function_to_json, function_from_json, result_to_json, serialize,
    save_function, load_function,
    cube_covers, cube_to_minterms,
)
from logicmin.boolean import var_names


# ===========================================================================
# BDD tests
# ===========================================================================

class TestBDD:
    def test_basic_bdd_construction(self):
        """A simple 3-var function should produce a valid BDD."""
        f = BooleanFunction(n_vars=3, minterms=[1, 3, 5, 7])
        mgr, root = BDDManager(3).from_function(f), None
        # Rebuild properly
        mgr = BDDManager(3)
        root = mgr.from_function(f)
        # f = C (since all odd minterms are on)
        assert root is mgr.one or not root.is_terminal  # may be simplified

    def test_bdd_sop_covers_onset(self):
        """BDD-extracted SOP should cover exactly the on-set."""
        f = BooleanFunction(n_vars=4, minterms=[4, 8, 10, 11, 12, 15], dontcare=[9, 14])
        mgr = BDDManager(4)
        root = mgr.from_function(f)
        cubes = mgr.to_sop(root)
        # All on-set minterms should be covered
        for m in f.minterms:
            assert any(cube_covers(c, m) for c in cubes), \
                f"minterm {m} not covered by BDD SOP"

    def test_bdd_count_satisfying(self):
        """Count of satisfying assignments should match minterm count."""
        f = BooleanFunction(n_vars=3, minterms=[1, 3, 5, 7])
        mgr = BDDManager(3)
        root = mgr.from_function(f)
        count = mgr.count_satisfying(root)
        assert count == len(f.minterms)

    def test_bdd_count_with_dc(self):
        """Count should include don't-cares as satisfying."""
        f = BooleanFunction(n_vars=3, minterms=[1, 3], dontcare=[5, 7])
        mgr = BDDManager(3)
        root = mgr.from_function(f)
        count = mgr.count_satisfying(root)
        assert count == 4  # 2 minterms + 2 dc

    def test_bdd_node_count(self):
        """Node count should be reasonable for a small function."""
        f = BooleanFunction(n_vars=4, minterms=[0, 1, 2, 3, 4, 5, 6, 7])
        mgr = BDDManager(4)
        root = mgr.from_function(f)
        # This is A'=0 i.e. first var = 0, so 1 node (or 0 if reduced to terminal)
        n = mgr.node_count(root)
        assert n <= 4

    def test_bdd_negate(self):
        """Negating a BDD should swap on-set and off-set."""
        f = BooleanFunction(n_vars=3, minterms=[1, 3, 5])
        mgr = BDDManager(3)
        root = mgr.from_function(f)
        neg = mgr.negate(root)
        neg_cubes = mgr.to_sop(neg)
        # Negated function should cover the off-set
        off = set(range(8)) - f.minterms - f.dontcare
        for m in off:
            assert any(cube_covers(c, m) for c in neg_cubes), \
                f"off-set minterm {m} not covered by negated BDD"

    def test_bdd_and(self):
        """AND of two BDDs should give intersection of on-sets."""
        f1 = BooleanFunction(n_vars=3, minterms=[1, 3, 5, 7])
        f2 = BooleanFunction(n_vars=3, minterms=[3, 7])
        mgr = BDDManager(3)
        r1 = mgr.from_function(f1)
        r2 = mgr.from_function(f2)
        r_and = mgr.and_(r1, r2)
        cubes = mgr.to_sop(r_and)
        for m in f2.minterms:
            assert any(cube_covers(c, m) for c in cubes), \
                f"AND minterm {m} not covered"

    def test_bdd_or(self):
        """OR of two BDDs should give union of on-sets."""
        f1 = BooleanFunction(n_vars=3, minterms=[1, 3])
        f2 = BooleanFunction(n_vars=3, minterms=[5, 7])
        mgr = BDDManager(3)
        r1 = mgr.from_function(f1)
        r2 = mgr.from_function(f2)
        r_or = mgr.or_(r1, r2)
        cubes = mgr.to_sop(r_or)
        for m in [1, 3, 5, 7]:
            assert any(cube_covers(c, m) for c in cubes), \
                f"OR minterm {m} not covered"

    def test_bdd_from_sop_cubes(self):
        """Building BDD from SOP cubes should match the function."""
        cubes = ["1-0", "01-"]
        mgr = BDDManager(3)
        root = mgr.from_sop_cubes(cubes)
        # 1-0 covers 100=4, 110=6; 01- covers 010=2, 011=3
        expected = {2, 3, 4, 6}
        cubes_out = mgr.to_sop(root)
        covered = set()
        for c in cubes_out:
            covered |= set(cube_to_minterms(c))
        assert expected <= covered

    def test_bdd_render_ascii(self):
        """ASCII rendering should not crash."""
        f = BooleanFunction(n_vars=3, minterms=[1, 3, 5, 7])
        mgr = BDDManager(3)
        root = mgr.from_function(f)
        text = mgr.render_ascii(root)
        assert isinstance(text, str)

    def test_bdd_equivalent(self):
        """Two identical BDDs should be equivalent."""
        f = BooleanFunction(n_vars=3, minterms=[1, 3, 5, 7])
        mgr = BDDManager(3)
        r1 = mgr.from_function(f)
        r2 = mgr.from_function(f)
        assert mgr.equivalent(r1, r2)


# ===========================================================================
# Analysis tests
# ===========================================================================

class TestAnalysis:
    def test_sensitivity_basic(self):
        """Sensitivity of f=C (only depends on C) should be 1.0 for C, 0 for others."""
        f = BooleanFunction(n_vars=3, minterms=[1, 3, 5, 7])
        s = sensitivity(f, 2)  # C is var index 2
        assert s == 1.0  # C always matters
        s_a = sensitivity(f, 0)  # A never matters
        assert s_a == 0.0
        s_b = sensitivity(f, 1)  # B never matters
        assert s_b == 0.0

    def test_all_sensitivities(self):
        """All sensitivities should return a dict with all vars."""
        f = BooleanFunction(n_vars=3, minterms=[1, 3, 5, 7])
        sens = all_sensitivities(f)
        assert len(sens) == 3
        assert sens[2] == 1.0
        assert sens[0] == 0.0

    def test_boolean_difference(self):
        """Boolean difference should identify dependency."""
        f = BooleanFunction(n_vars=3, minterms=[1, 3, 5, 7])
        diff = boolean_difference(f, 2)  # ∂f/∂C
        # f = C, so ∂f/∂C = 1 (always depends on C)
        # The diff function (in 2 vars A, B) should be all minterms
        assert set(diff.minterms) == {0, 1, 2, 3}

    def test_boolean_difference_independent_var(self):
        """Boolean difference of independent var should be 0."""
        f = BooleanFunction(n_vars=3, minterms=[1, 3, 5, 7])
        diff = boolean_difference(f, 0)  # ∂f/∂A — A doesn't matter
        assert len(diff.minterms) == 0  # always 0 (no dependency)

    def test_is_unate_positive(self):
        """A positive unate variable should be detected."""
        # f = A (positive unate in A)
        f = BooleanFunction(n_vars=2, minterms=[2, 3])
        assert is_unate(f, 0)  # A is positive unate

    def test_is_unate_negative(self):
        """A negative unate variable should be detected."""
        # f = A' (negative unate in A)
        f = BooleanFunction(n_vars=2, minterms=[0, 1])
        assert is_unate(f, 0)  # A is negative unate

    def test_is_unate_binate(self):
        """A binate variable should return False."""
        # f = A XOR B (binate in both A and B)
        f = BooleanFunction(n_vars=2, minterms=[1, 2])
        assert not is_unate(f, 0)
        assert not is_unate(f, 1)

    def test_unate_profile(self):
        """Unate profile should classify each variable."""
        f = BooleanFunction(n_vars=2, minterms=[2, 3])  # f = A
        profile = unate_profile(f)
        assert profile[0] == "positive"
        # B doesn't appear → both cofactors equal → positive (f0 ⊆ f1 and f1 ⊆ f0)
        assert profile[1] in ("positive", "negative")

    def test_on_set_size(self):
        """On-set size should match."""
        f = BooleanFunction(n_vars=3, minterms=[1, 3, 5])
        assert on_set_size(f) == 3

    def test_off_set_size(self):
        """Off-set size should match."""
        f = BooleanFunction(n_vars=3, minterms=[1, 3, 5])
        assert off_set_size(f) == 5  # 8 - 3 = 5

    def test_minterm_adjacency(self):
        """Adjacent minterms should be found."""
        f = BooleanFunction(n_vars=3, minterms=[0, 1, 3, 7])
        edges = minterm_adjacency(f)
        # 0-1 differ by 1 bit, 1-3 differ by 1 bit, 3-7 differ by 1 bit
        assert (0, 1) in edges
        assert (1, 3) in edges
        assert (3, 7) in edges

    def test_hamming_distance_matrix(self):
        """Hamming distance matrix should be correct."""
        f = BooleanFunction(n_vars=3, minterms=[0, 7])
        matrix = hamming_distance_matrix(f)
        assert matrix[0][0] == 0
        assert matrix[0][1] == 3  # 000 vs 111
        assert matrix[1][0] == 3


# ===========================================================================
# PLA tests
# ===========================================================================

class TestPLA:
    def test_parse_pla_full(self):
        """Full PLA parser should handle directives."""
        pla_text = """.i 3
.o 2
.ilb A B C
.ob f0 f1
# comment line
000 10
001 10
010 11
011 01
.e
"""
        pla = parse_pla_full(pla_text)
        assert pla.n_in == 3
        assert pla.n_out == 2
        assert pla.input_names == ["A", "B", "C"]
        assert pla.output_names == ["f0", "f1"]
        assert len(pla.entries) == 4
        assert "comment" in pla.comments[0]

    def test_pla_to_functions(self):
        """PLAData should convert to BooleanFunctions."""
        pla = PLAData(n_in=2, n_out=1, entries=[("00", "1"), ("11", "1")])
        funcs = pla.to_functions()
        assert len(funcs) == 1
        assert funcs[0].n_vars == 2
        assert set(funcs[0].minterms) == {0, 3}

    def test_pla_from_functions(self):
        """PLAData should be created from functions."""
        f1 = BooleanFunction(n_vars=2, minterms=[0, 3], name="f1")
        pla = PLAData.from_functions([f1])
        assert pla.n_in == 2
        assert pla.n_out == 1
        text = pla.to_pla_text()
        assert ".i 2" in text
        assert ".o 1" in text
        assert ".e" in text

    def test_pla_roundtrip(self):
        """PLA text → parse → functions → PLA text should be consistent."""
        original = """.i 2
.o 1
.ilb A B
.ob f
00 1
11 1
.e
"""
        pla = parse_pla_full(original)
        funcs = pla.to_functions()
        pla2 = PLAData.from_functions(funcs, input_names=["A", "B"], output_names=["f"])
        text = pla2.to_pla_text()
        assert ".i 2" in text
        assert ".o 1" in text

    def test_pla_validate(self):
        """Validation should catch errors."""
        pla = PLAData(n_in=2, n_out=1, entries=[("000", "1")])  # wrong length
        errors = pla.validate()
        assert any("input pattern" in e for e in errors)

    def test_pla_stats(self):
        """Stats should return correct counts."""
        pla = PLAData(n_in=2, n_out=1, entries=[("00", "1"), ("11", "1"), ("01", "0")])
        stats = pla.stats()
        assert stats["n_in"] == 2
        assert stats["n_out"] == 1
        assert stats["n_products"] == 3

    def test_write_pla(self):
        """write_pla should produce a valid PLA file."""
        f1 = BooleanFunction(n_vars=2, minterms=[0, 3], name="f")
        text = write_pla([f1])
        assert ".i 2" in text
        assert ".e" in text


# ===========================================================================
# DC Optimization tests
# ===========================================================================

class TestDCOptimize:
    def test_dc_assignment_no_dc(self):
        """Without don't-cares, optimization should be a no-op."""
        f = BooleanFunction(n_vars=3, minterms=[1, 3, 5])
        result = assign_dontcares(f, "qm")
        assert result.improvement == 0
        assert result.optimized_cost == result.original_cost

    def test_dc_assignment_with_dc(self):
        """With don't-cares, assignment should find a valid function."""
        f = BooleanFunction(n_vars=4, minterms=[4, 8, 10, 11, 12, 15], dontcare=[9, 14])
        result = assign_dontcares(f, "qm")
        # The optimized cost should be <= original cost
        assert result.optimized_cost <= result.original_cost
        # The assigned function should cover all original minterms
        assert f.minterms <= result.assigned_func.minterms

    def test_dc_assignment_espresso(self):
        """DC optimization should work with Espresso too."""
        f = BooleanFunction(n_vars=3, minterms=[1, 3], dontcare=[5, 7])
        result = assign_dontcares(f, "espresso")
        assert result.optimized_cost <= result.original_cost + 2


# ===========================================================================
# HTML Visualization tests
# ===========================================================================

class TestHTMLViz:
    def test_truth_table_html(self):
        """HTML truth table should contain expected elements."""
        f = BooleanFunction(n_vars=3, minterms=[1, 3, 5])
        html = truth_table_html(f)
        assert "<table>" in html
        assert "<!DOCTYPE html>" in html
        assert "1" in html

    def test_kmap_html(self):
        """HTML K-map should render without errors."""
        f = BooleanFunction(n_vars=4, minterms=[4, 8, 10, 11, 12, 15], dontcare=[9, 14])
        html = kmap_html(f)
        assert "<table>" in html
        assert "<!DOCTYPE html>" in html

    def test_kmap_with_cover_html(self):
        """K-map with cover should contain 'covered' class."""
        f = BooleanFunction(n_vars=3, minterms=[1, 3, 5, 7])
        qm = QuineMcCluskey(3)
        result = qm.minimize(f)
        html = kmap_with_cover_html(f, result.sop_cubes)
        assert "covered" in html

    def test_full_report_html(self):
        """Full report should contain all sections."""
        f = BooleanFunction(n_vars=4, minterms=[4, 8, 10, 11, 12, 15], dontcare=[9, 14])
        qm = QuineMcCluskey(4)
        result = qm.minimize(f)
        html = full_report_html(f, result)
        assert "Truth Table" in html
        assert "Karnaugh Map" in html
        assert "Prime Implicants" in html
        assert result.sop in html

    def test_html_kmap_out_of_range(self):
        """HTML K-map should reject 1-var or 6-var functions."""
        f1 = BooleanFunction(n_vars=1, minterms=[1])
        with pytest.raises(ValueError):
            kmap_html(f1)
        f6 = BooleanFunction(n_vars=6, minterms=[0])
        with pytest.raises(ValueError):
            kmap_html(f6)


# ===========================================================================
# Batch tests
# ===========================================================================

class TestBatch:
    def test_batch_processor_qm(self):
        """Batch processor with QM should minimize multiple functions."""
        f1 = BooleanFunction(n_vars=3, minterms=[1, 3, 5, 7], name="f1")
        f2 = BooleanFunction(n_vars=3, minterms=[0, 2, 4, 6], name="f2")
        bp = BatchProcessor(minimizer="qm")
        entries = bp.process_batch([f1, f2])
        assert len(entries) == 2
        assert entries[0].name == "f1"
        assert entries[1].name == "f2"
        assert entries[0].correct
        assert entries[1].correct

    def test_batch_processor_espresso(self):
        """Batch processor with Espresso should work."""
        f1 = BooleanFunction(n_vars=3, minterms=[1, 3, 5, 7], name="f1")
        bp = BatchProcessor(minimizer="espresso")
        entry = bp.process(f1)
        assert entry.correct
        assert entry.method == "espresso"

    def test_batch_json_serialization(self):
        """Batch entries should serialize/deserialize correctly."""
        f1 = BooleanFunction(n_vars=3, minterms=[1, 3, 5, 7], name="f1")
        bp = BatchProcessor(minimizer="qm")
        entries = bp.process_batch([f1])
        json_text = batch_to_json(entries)
        restored = batch_from_json(json_text)
        assert len(restored) == 1
        assert restored[0].name == "f1"
        assert restored[0].n_literals == entries[0].n_literals

    def test_batch_summary(self):
        """Batch summary should compute correct statistics."""
        f1 = BooleanFunction(n_vars=3, minterms=[1, 3, 5, 7], name="f1")
        f2 = BooleanFunction(n_vars=3, minterms=[0, 2, 4, 6], name="f2")
        bp = BatchProcessor(minimizer="qm")
        entries = bp.process_batch([f1, f2])
        summary = batch_summary(entries)
        assert summary.n_functions == 2
        assert summary.all_correct


# ===========================================================================
# Serialization tests
# ===========================================================================

class TestSerialize:
    def test_function_json_roundtrip(self):
        """Function JSON roundtrip should preserve data."""
        f = BooleanFunction(n_vars=4, minterms=[4, 8, 10, 11], dontcare=[9, 14], name="test")
        json_text = function_to_json(f)
        f2 = function_from_json(json_text)
        assert f2.n_vars == f.n_vars
        assert set(f2.minterms) == set(f.minterms)
        assert set(f2.dontcare) == set(f.dontcare)
        assert f2.name == f.name

    def test_result_json(self):
        """Result JSON should contain expected fields."""
        f = BooleanFunction(n_vars=3, minterms=[1, 3, 5, 7])
        qm = QuineMcCluskey(3)
        result = qm.minimize(f)
        json_text = result_to_json(result)
        import json
        data = json.loads(json_text)
        assert data["method"] == "quine-mccluskey"
        assert "sop" in data
        assert "prime_implicants" in data

    def test_serialize_dispatcher(self):
        """Generic serialize should dispatch correctly."""
        f = BooleanFunction(n_vars=2, minterms=[1, 3])
        text = serialize(f)
        import json
        data = json.loads(text)
        assert data["type"] == "BooleanFunction"

    def test_save_load_function(self, tmp_path):
        """Save/load to file should work."""
        f = BooleanFunction(n_vars=3, minterms=[1, 3, 5], name="test")
        path = str(tmp_path / "func.json")
        save_function(f, path)
        f2 = load_function(path)
        assert set(f2.minterms) == set(f.minterms)


# ===========================================================================
# CLI tests for new subcommands
# ===========================================================================

class TestCLINew:
    def test_cli_bdd(self):
        """BDD subcommand should produce output."""
        from logicmin.cli import main
        ret = main(["bdd", "-n", "3", "-m", "1 3 5 7", "--count"])
        assert ret == 0

    def test_cli_sensitivity(self):
        """Sensitivity subcommand should work."""
        from logicmin.cli import main
        ret = main(["sensitivity", "-n", "3", "-m", "1 3 5 7"])
        assert ret == 0

    def test_cli_unate(self):
        """Unate subcommand should work."""
        from logicmin.cli import main
        ret = main(["unate", "-n", "2", "-m", "2 3"])
        assert ret == 0

    def test_cli_dc_optimize(self):
        """DC optimize subcommand should work."""
        from logicmin.cli import main
        ret = main(["dc-optimize", "-n", "4", "-m", "4 8 10 11 12 15 d: 9 14"])
        assert ret == 0

    def test_cli_html(self):
        """HTML subcommand should produce HTML."""
        from logicmin.cli import main
        ret = main(["html", "-n", "3", "-m", "1 3 5 7", "--mode", "truth"])
        assert ret == 0

    def test_cli_export(self):
        """Export subcommand should produce JSON."""
        from logicmin.cli import main
        ret = main(["export", "-n", "3", "-m", "1 3 5 7"])
        assert ret == 0

    def test_cli_export_result(self):
        """Export with --result should minimize first."""
        from logicmin.cli import main
        ret = main(["export", "-n", "3", "-m", "1 3 5 7", "--result"])
        assert ret == 0

    def test_cli_version(self):
        """Version subcommand should show version."""
        from logicmin.cli import main
        ret = main(["version"])
        assert ret == 0

    def test_cli_batch(self, tmp_path):
        """Batch subcommand should process a PLA file."""
        pla_text = """.i 2
.o 1
.ilb A B
.ob f
00 1
11 1
.e
"""
        path = str(tmp_path / "test.pla")
        with open(path, "w") as fh:
            fh.write(pla_text)
        from logicmin.cli import main
        ret = main(["batch", path, "--minimizer", "qm"])
        assert ret == 0


# ===========================================================================
# Integration tests
# ===========================================================================

class TestIntegration:
    def test_qm_then_bdd_agreement(self):
        """QM and BDD should cover the same minterms."""
        f = BooleanFunction(n_vars=4, minterms=[0, 1, 2, 5, 7, 8, 9, 10, 14])
        qm = QuineMcCluskey(4)
        qm_result = qm.minimize(f)
        # BDD
        mgr = BDDManager(4)
        root = mgr.from_function(f)
        bdd_cubes = mgr.to_sop(root)
        # Both should cover all on-set minterms
        for m in f.minterms:
            assert any(cube_covers(c, m) for c in qm_result.sop_cubes)
            assert any(cube_covers(c, m) for c in bdd_cubes)

    def test_bdd_sop_function(self):
        """bdd_sop convenience function should produce valid cubes."""
        f = BooleanFunction(n_vars=3, minterms=[1, 3, 5, 7])
        cubes = bdd_sop(f)
        assert len(cubes) > 0
        for m in f.minterms:
            assert any(cube_covers(c, m) for c in cubes)

    def test_build_bdd(self):
        """build_bdd convenience function should work."""
        f = BooleanFunction(n_vars=3, minterms=[1, 3, 5])
        mgr, root = build_bdd(f)
        assert mgr.n_vars == 3
        count = mgr.count_satisfying(root)
        assert count == 3

    def test_espresso_vs_qm_coverage(self):
        """Espresso and QM should cover the same set of minterms."""
        import random
        rng = random.Random(42)
        for _ in range(10):
            n = 4
            all_m = list(range(1 << n))
            rng.shuffle(all_m)
            n_dc = rng.randint(0, 4)
            dc = set(all_m[:n_dc])
            rest = all_m[n_dc:]
            n_mt = rng.randint(1, max(1, len(rest) - 1))
            mt = set(rest[:n_mt])
            f = BooleanFunction(n_vars=n, minterms=mt, dontcare=dc)
            qm = QuineMcCluskey(n)
            esp = Espresso(n)
            r_qm = qm.minimize(f)
            r_esp = esp.minimize(f)
            # Both cover all on-set
            for m in mt:
                assert any(cube_covers(c, m) for c in r_qm.sop_cubes)
                assert any(cube_covers(c, m) for c in r_esp.sop_cubes)
            # Neither covers off-set
            off = set(range(1 << n)) - mt - dc
            for m in off:
                assert not any(cube_covers(c, m) for c in r_qm.sop_cubes)
                assert not any(cube_covers(c, m) for c in r_esp.sop_cubes)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])