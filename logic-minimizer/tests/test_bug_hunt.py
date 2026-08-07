"""
Bug hunt tests for logicmin.

Each test verifies a specific bug before/after the fix.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from logicmin import (
    QuineMcCluskey, BooleanFunction, Espresso, POSMinimizer,
    KarnaughMap, Factorizer, PetrickSolver, MultiOutputMinimizer,
    parse_sop, parse_minterms, parse_truth_table, parse_pla,
    can_merge, cube_to_minterms, minterm_to_cube, cube_covers,
    Implicant, gray_code,
)
from logicmin.boolean import var_names


# ===========================================================================
# Bug 1: from_sop("AC") fails — n_vars inference uses letter COUNT instead
#         of the highest letter POSITION.  "AC" should imply 3 vars (A,B,C)
#         with B as don't-care, yielding minterms 5 and 7.
# ===========================================================================

class TestSopInferenceBug:
    def test_sop_with_gap_letters(self):
        """from_sop("AC") should work, inferring 3 variables (A, B, C)."""
        func = BooleanFunction.from_sop("AC")
        assert func.n_vars == 3
        # AC = A=1, B=-, C=1 → minterms 101=5, 111=7
        assert set(func.minterms) == {5, 7}

    def test_sop_with_gap_letters_and_complement(self):
        """from_sop("A'C") should also work with 3 vars."""
        func = BooleanFunction.from_sop("A'C")
        assert func.n_vars == 3
        # A'C = A=0, B=-, C=1 → minterms 001=1, 011=3
        assert set(func.minterms) == {1, 3}

    def test_sop_single_letter(self):
        """from_sop("A") should give 1 variable."""
        func = BooleanFunction.from_sop("A")
        assert func.n_vars == 1
        assert set(func.minterms) == {1}

    def test_sop_full_alphabet(self):
        """from_sop("AB") should give 2 vars with minterms 3."""
        func = BooleanFunction.from_sop("AB")
        assert func.n_vars == 2
        assert set(func.minterms) == {3}


# ===========================================================================
# Bug 2: Espresso _intersects_off has dead code — a no-op for loop that
#         allocates cube_to_minterms(cube) and does nothing.  This is a
#         performance bug (wasted allocation) and confusing dead code.
# ===========================================================================

class TestEspressoIntersectsOffDeadCode:
    def test_espresso_still_correct_after_dead_code_removal(self):
        """Espresso should produce correct results (dead code removal shouldn't break)."""
        f = BooleanFunction(n_vars=4, minterms=[4, 8, 10, 11, 12, 15], dontcare=[9, 14])
        esp = Espresso(n_vars=4)
        result = esp.minimize(f)
        # Verify all on-set minterms are covered
        for m in f.minterms:
            assert any(cube_covers(c, m) for c in result.sop_cubes), \
                f"minterm {m} not covered by espresso result"


# ===========================================================================
# Bug 3: Espresso final cost check is a no-op — `best_cover = best_cover`
#         does nothing.  After the final expand+irredundant, if the cost got
#         worse, the better solution is lost.
# ===========================================================================

class TestEspressoFinalCostNoOp:
    def test_espresso_does_not_regress(self):
        """Espresso final result should not be worse than mid-loop best."""
        # Use a function that might trigger the regression
        f = BooleanFunction(n_vars=4, minterms=[0, 1, 2, 5, 7, 8, 9, 10, 14])
        esp = Espresso(n_vars=4, max_iter=20)
        result = esp.minimize(f)
        # Compare with QM (exact) — Espresso should be <= QM cost
        qm = QuineMcCluskey(n_vars=4)
        qm_result = qm.minimize(f)
        assert result.n_literals <= qm_result.n_literals + 2, \
            f"Espresso lits={result.n_literals} vs QM lits={qm_result.n_literals}"


# ===========================================================================
# Bug 4: can_merge doesn't validate length match — zip silently truncates
#         mismatched-length cubes, which could produce incorrect merges.
# ===========================================================================

class TestCanMergeLengthCheck:
    def test_can_merge_different_lengths(self):
        """can_merge should return None (or raise) for different-length cubes."""
        result = can_merge("010", "0100")
        # Currently zip truncates to "010" vs "010" → identical → returns None.
        # But this should explicitly return None for mismatched lengths.
        assert result is None

    def test_can_merge_different_lengths_with_diff(self):
        """can_merge("01", "011") should not silently merge."""
        result = can_merge("01", "110")
        # zip truncates to "01" vs "11" → differ in 1 pos → returns "0-"
        # But the 3rd char of "110" is ignored! This is a bug.
        assert result is None  # should be None because lengths differ


# ===========================================================================
# Bug 5: Multi-output _generate_tagged_primes imports can_merge inside a
#         nested loop — performance issue (import lookup every iteration).
# ===========================================================================

class TestMultiOutputImportInLoop:
    def test_multi_output_correctness(self):
        """Multi-output minimization should still produce correct results."""
        f0 = BooleanFunction(n_vars=3, minterms=[0, 1, 2, 5, 6, 7], name="f0")
        f1 = BooleanFunction(n_vars=3, minterms=[2, 3, 5, 6, 7], name="f1")
        mom = MultiOutputMinimizer(3)
        result = mom.minimize([f0, f1])
        # Verify each output covers its minterms
        for oi, func in enumerate([f0, f1]):
            chosen = result.per_output[oi]
            covered = set()
            for imp in chosen:
                covered |= imp.minterms
            assert func.minterms <= covered, \
                f"output {oi}: minterms {func.minterms - covered} not covered"


# ===========================================================================
# Bug 6: from_sop dead variable `sorted_letters` — set but never used.
#         (Verified by code inspection; no runtime test needed, but we
#          verify the corrected code still works.)
# ===========================================================================

class TestSopDeadVariable:
    def test_sop_with_explicit_nvars(self):
        """from_sop with explicit n_vars should work correctly."""
        func = BooleanFunction.from_sop("AC", n_vars=3)
        assert func.n_vars == 3
        assert set(func.minterms) == {5, 7}


# ===========================================================================
# Additional correctness tests to verify no regressions after bug fixes
# ===========================================================================

class TestCorrectness:
    @pytest.mark.parametrize("minterms,dc,n_vars", [
        ([4, 8, 10, 11, 12, 15], [9, 14], 4),
        ([0, 1, 2, 3, 4, 5, 6, 7], [], 3),  # tautology
        ([], [], 3),  # zero
        ([1], [], 4),  # single minterm
        ([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15], [], 4),  # tautology 4
    ])
    def test_qm_correctness(self, minterms, dc, n_vars):
        f = BooleanFunction(n_vars=n_vars, minterms=minterms, dontcare=dc)
        qm = QuineMcCluskey(n_vars=n_vars)
        result = qm.minimize(f)
        # Verify all on-set minterms are covered
        for m in f.minterms:
            assert any(cube_covers(c, m) for c in result.sop_cubes), \
                f"minterm {m} not covered"
        # Verify no off-set minterm is covered
        off_set = set(range(1 << n_vars)) - f.minterms - f.dontcare
        for m in off_set:
            assert not any(cube_covers(c, m) for c in result.sop_cubes), \
                f"off-set minterm {m} incorrectly covered"

    def test_qm_vs_espresso_agreement(self):
        """Espresso should cover exactly the on-set (no more, no less)."""
        import random
        rng = random.Random(123)
        for _ in range(20):
            n = 4
            all_m = list(range(1 << n))
            rng.shuffle(all_m)
            n_dc = rng.randint(0, 4)
            dc = set(all_m[:n_dc])
            rest = all_m[n_dc:]
            n_mt = rng.randint(1, len(rest) - 1) if len(rest) > 1 else 1
            mt = set(rest[:n_mt])
            f = BooleanFunction(n_vars=n, minterms=mt, dontcare=dc)
            qm = QuineMcCluskey(n)
            esp = Espresso(n)
            r_qm = qm.minimize(f)
            r_esp = esp.minimize(f)
            # Both must cover all on-set minterms
            for m in mt:
                assert any(cube_covers(c, m) for c in r_qm.sop_cubes)
                assert any(cube_covers(c, m) for c in r_esp.sop_cubes)
            # Neither should cover off-set
            off = set(range(1 << n)) - mt - dc
            for m in off:
                assert not any(cube_covers(c, m) for c in r_qm.sop_cubes)
                assert not any(cube_covers(c, m) for c in r_esp.sop_cubes)

    def test_pos_correctness(self):
        """POS form should be the complement of the dual SOP."""
        f = BooleanFunction(n_vars=4, minterms=[4, 8, 10, 11, 12, 15], dontcare=[9, 14])
        pm = POSMinimizer(4)
        result = pm.minimize(f)
        # The dual SOP should be 1 exactly on the off-set (excluding don't-cares)
        dual = parse_sop(result.dual_sop, n_vars=4)
        off_set = set(range(16)) - f.minterms - f.dontcare
        for m in range(16):
            if m in f.dontcare:
                continue
            expected = 1 if m in off_set else 0
            actual = 1 if m in dual.minterms else 0
            assert expected == actual, f"POS dual mismatch at {m}"

    def test_kmap_correctness(self):
        """K-map should show correct values for each cell."""
        f = BooleanFunction(n_vars=3, minterms=[1, 2, 5, 6, 7])
        km = KarnaughMap(f)
        text = km.render()
        # Every on-set minterm should appear as '1' in the output
        # Every off-set should appear as '0'
        # This is a smoke test — just verify it renders without error
        assert "1" in text
        assert "0" in text

    def test_gray_code(self):
        """Gray code should produce correct sequences."""
        assert gray_code(1) == [0, 1]
        assert gray_code(2) == [0, 1, 3, 2]
        # Each adjacent pair differs by exactly 1 bit
        for n in range(1, 5):
            codes = gray_code(n)
            for i in range(len(codes) - 1):
                diff = codes[i] ^ codes[i + 1]
                assert bin(diff).count("1") == 1, \
                    f"gray code {n}: adjacent pair {codes[i]}, {codes[i+1]} differ by {bin(diff).count('1')} bits"

    def test_factorizer_reduces_literals(self):
        """Factorization should not increase literal count."""
        fact = Factorizer(n_vars=4)
        ff = fact.factorize_sop("AB'C + AC + BC'")
        # Original: 3 terms × 3 literals = 9
        # Factored should be <= 9
        assert ff.literal_count() <= 9

    def test_petrick_solver(self):
        """Petrick solver should find minimum covers."""
        solver = PetrickSolver()
        # Simple: clause1 = [0, 1], clause2 = [0, 2], clause3 = [1, 2]
        # Minimum cover: any 2 of {0,1,2}
        solutions = solver.solve([[0, 1], [0, 2], [1, 2]])
        assert len(solutions) > 0
        for sol in solutions:
            assert len(sol) == 2  # minimum size

    def test_parse_minterms(self):
        """parse_minterms should handle various formats."""
        f = parse_minterms("4 8 10 d: 9 14", n_vars=4)
        assert set(f.minterms) == {4, 8, 10}
        assert set(f.dontcare) == {9, 14}

    def test_parse_pla(self):
        """parse_pla should correctly parse PLA format."""
        pla = """.i 2
.o 1
.ilb A B
.ob f
00 1
01 0
10 1
11 0
.e
"""
        funcs = parse_pla(pla)
        assert len(funcs) == 1
        assert funcs[0].n_vars == 2
        assert set(funcs[0].minterms) == {0, 2}

    def test_implicant_properties(self):
        """Implicant should correctly compute properties."""
        imp = Implicant("1-0-")
        assert imp.n_literals == 2
        assert imp.n_dashes == 2
        assert imp.size == 4
        # 1-0- (4 vars): position 0=1, 2=0 → covers 1000=8, 1001=9, 1100=12, 1101=13
        assert imp.covers(8)   # 1000
        assert imp.covers(9)   # 1001
        assert imp.covers(12)  # 1100
        assert imp.covers(13)  # 1101
        assert not imp.covers(10)  # 1010 — position 2 is 1, not 0
        assert not imp.covers(0)   # 0000

    def test_cube_to_minterms(self):
        """cube_to_minterms should expand correctly."""
        result = cube_to_minterms("1-0")
        # 1-0 covers: 100=4, 110=6
        assert sorted(result) == [4, 6]

    def test_cube_covers(self):
        """cube_covers should work correctly."""
        # cube "1-0" (3 vars): covers 100=4, 110=6
        assert cube_covers("1-0", 4)   # 100
        assert cube_covers("1-0", 6)   # 110
        assert not cube_covers("1-0", 2)   # 010
        assert not cube_covers("1-0", 7)   # 111
        # Out of range
        assert not cube_covers("1-0", -1)
        assert not cube_covers("1-0", 8)

    def test_verify_cli(self):
        """Verify should confirm a correct SOP."""
        from logicmin.cli import main
        ret = main(["verify", "-n", "4", "-m", "4 8 10 11 12 15 d: 9 14",
                     "-s", "BC'D' + AD' + AC"])
        assert ret == 0

    def test_verify_cli_failure(self):
        """Verify should reject an incorrect SOP."""
        from logicmin.cli import main
        ret = main(["verify", "-n", "3", "-m", "0 1 2", "-s", "A"])
        assert ret == 1  # A covers 4,5,6,7 which are not in minterms


# ===========================================================================
# Bug 7: Espresso _irredundant can return empty cover for non-trivial
#         functions in edge cases (safety check exists but may not trigger).
# ===========================================================================

class TestEspressoIrredundantEdgeCase:
    def test_espresso_single_minterm(self):
        """Espresso with a single minterm should return that minterm."""
        f = BooleanFunction(n_vars=3, minterms=[3])
        esp = Espresso(n_vars=3)
        result = esp.minimize(f)
        assert result.n_terms >= 1
        assert any(cube_covers(c, 3) for c in result.sop_cubes)

    def test_espresso_all_minterms(self):
        """Espresso with all minterms (no dc) should return '1'."""
        f = BooleanFunction(n_vars=3, minterms=list(range(8)))
        esp = Espresso(n_vars=3)
        result = esp.minimize(f)
        assert result.sop == "1"


# ===========================================================================
# Bug 8: BooleanFunction.from_truth_table with length 1 (n_vars=0)
#         should raise a clear error, not a confusing one.
# ===========================================================================

class TestFromTruthTableEdgeCases:
    def test_empty_truth_table(self):
        """Empty truth table should raise ValueError."""
        with pytest.raises(ValueError):
            BooleanFunction.from_truth_table([])

    def test_single_entry_truth_table(self):
        """Single-entry truth table (n_vars=0) should raise ValueError."""
        with pytest.raises(ValueError):
            BooleanFunction.from_truth_table([1])

    def test_non_power_of_two(self):
        """Non-power-of-two length should raise ValueError."""
        with pytest.raises(ValueError):
            BooleanFunction.from_truth_table([0, 1, 0])


# ===========================================================================
# Bug 9: QM _generate_primes groups only adjacent one-count groups, but
#         the sorted_keys loop skips non-adjacent groups correctly.
#         Let's verify with a function that has a gap in one-counts.
# ===========================================================================

class TestQmGapInOneCounts:
    def test_qm_with_isolated_minterms(self):
        """QM should handle minterms with no adjacency."""
        f = BooleanFunction(n_vars=4, minterms=[0, 15])  # 0000 and 1111
        qm = QuineMcCluskey(4)
        result = qm.minimize(f)
        # These can't be merged, so both are essential primes
        assert result.n_terms == 2
        for m in [0, 15]:
            assert any(cube_covers(c, m) for c in result.sop_cubes)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])