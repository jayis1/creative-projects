"""
Quick smoke tests for the diff_merge package.
Run with: python3 -m pytest tests/ -v
"""
import sys
import os

# Ensure the package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from diff_merge import (
    myers_diff,
    diff_sequences,
    patience_diff,
    histogram_diff,
    lcs_diff,
    longest_common_subsequence,
    unified_diff,
    context_diff,
    normal_diff,
    parse_unified_diff,
    apply_patch,
    three_way_merge,
)
from diff_merge.myers import Operation, DiffOp


def _ops_to_edit(a, ops):
    """Apply ops to a to reconstruct b."""
    result = []
    for op in ops:
        if op.tag == Operation.EQUAL:
            result.extend(a[op.i1:op.i2])
        elif op.tag == Operation.DELETE:
            pass  # skip
        elif op.tag == Operation.INSERT:
            pass  # will be filled from b
        elif op.tag == Operation.REPLACE:
            pass
    return result


def _reconstruct_b(a, b, ops):
    """Given ops, reconstruct b from a."""
    result = []
    for op in ops:
        if op.tag == Operation.EQUAL:
            result.extend(a[op.i1:op.i2])
        elif op.tag == Operation.DELETE:
            pass
        elif op.tag == Operation.INSERT:
            result.extend(b[op.j1:op.j2])
        elif op.tag == Operation.REPLACE:
            result.extend(b[op.j1:op.j2])
    return result


def _reconstruct_a(a, b, ops):
    """Given ops, reconstruct a from b."""
    result = []
    for op in ops:
        if op.tag == Operation.EQUAL:
            result.extend(a[op.i1:op.i2])
        elif op.tag == Operation.DELETE:
            result.extend(a[op.i1:op.i2])
        elif op.tag == Operation.INSERT:
            pass
        elif op.tag == Operation.REPLACE:
            result.extend(a[op.i1:op.i2])
    return result


# ---- Tests ----

def test_myers_basic():
    a = ["a", "b", "c", "d"]
    b = ["a", "c", "d", "e"]
    ops = myers_diff(a, b)
    assert _reconstruct_a(a, b, ops) == a, f"reconstruct a failed: {ops}"
    assert _reconstruct_b(a, b, ops) == b, f"reconstruct b failed: {ops}"
    print("  test_myers_basic: PASS")


def test_myers_empty_a():
    a = []
    b = ["x", "y", "z"]
    ops = myers_diff(a, b)
    assert _reconstruct_a(a, b, ops) == a
    assert _reconstruct_b(a, b, ops) == b
    print("  test_myers_empty_a: PASS")


def test_myers_empty_b():
    a = ["x", "y", "z"]
    b = []
    ops = myers_diff(a, b)
    assert _reconstruct_a(a, b, ops) == a
    assert _reconstruct_b(a, b, ops) == b
    print("  test_myers_empty_b: PASS")


def test_myers_identical():
    a = ["a", "b", "c"]
    b = ["a", "b", "c"]
    ops = myers_diff(a, b)
    assert len(ops) == 1 and ops[0].tag == Operation.EQUAL
    assert _reconstruct_a(a, b, ops) == a
    assert _reconstruct_b(a, b, ops) == b
    print("  test_myers_identical: PASS")


def test_myers_completely_different():
    a = ["a", "b", "c"]
    b = ["x", "y", "z"]
    ops = myers_diff(a, b)
    assert _reconstruct_a(a, b, ops) == a
    assert _reconstruct_b(a, b, ops) == b
    print("  test_myers_completely_different: PASS")


def test_myers_large():
    import random
    random.seed(42)
    a = [str(random.randint(0, 100)) for _ in range(200)]
    b = a.copy()
    # Make some random changes
    for _ in range(50):
        if random.random() < 0.5:
            idx = random.randint(0, len(b) - 1)
            b[idx] = str(random.randint(0, 100))
        elif random.random() < 0.5:
            idx = random.randint(0, len(b))
            b.insert(idx, str(random.randint(0, 100)))
        else:
            if len(b) > 1:
                idx = random.randint(0, len(b) - 1)
                b.pop(idx)
    ops = myers_diff(a, b)
    assert _reconstruct_a(a, b, ops) == a, "reconstruct a failed"
    assert _reconstruct_b(a, b, ops) == b, "reconstruct b failed"
    print("  test_myers_large: PASS")


def test_lcs_basic():
    a = ["a", "b", "c", "d"]
    b = ["a", "c", "d", "e"]
    ops = lcs_diff(a, b)
    assert _reconstruct_a(a, b, ops) == a
    assert _reconstruct_b(a, b, ops) == b
    print("  test_lcs_basic: PASS")


def test_lcs_lcs():
    a = ["a", "b", "c", "d", "e"]
    b = ["a", "c", "e"]
    lcs = longest_common_subsequence(a, b)
    assert lcs == ["a", "c", "e"], f"got {lcs}"
    print("  test_lcs_lcs: PASS")


def test_patience_basic():
    a = ["a", "b", "c", "d"]
    b = ["a", "c", "d", "e"]
    ops = patience_diff(a, b)
    assert _reconstruct_a(a, b, ops) == a, f"reconstruct a failed: {ops}"
    assert _reconstruct_b(a, b, ops) == b, f"reconstruct b failed: {ops}"
    print("  test_patience_basic: PASS")


def test_patience_large():
    import random
    random.seed(42)
    a = [str(random.randint(0, 100)) for _ in range(200)]
    b = a.copy()
    for _ in range(50):
        if random.random() < 0.5:
            idx = random.randint(0, len(b) - 1)
            b[idx] = str(random.randint(0, 100))
        elif random.random() < 0.5:
            idx = random.randint(0, len(b))
            b.insert(idx, str(random.randint(0, 100)))
        else:
            if len(b) > 1:
                idx = random.randint(0, len(b) - 1)
                b.pop(idx)
    ops = patience_diff(a, b)
    assert _reconstruct_a(a, b, ops) == a, "reconstruct a failed"
    assert _reconstruct_b(a, b, ops) == b, "reconstruct b failed"
    print("  test_patience_large: PASS")


def test_histogram_basic():
    a = ["a", "b", "c", "d"]
    b = ["a", "c", "d", "e"]
    ops = histogram_diff(a, b)
    assert _reconstruct_a(a, b, ops) == a, f"reconstruct a failed: {ops}"
    assert _reconstruct_b(a, b, ops) == b, f"reconstruct b failed: {ops}"
    print("  test_histogram_basic: PASS")


def test_histogram_large():
    import random
    random.seed(42)
    a = [str(random.randint(0, 100)) for _ in range(200)]
    b = a.copy()
    for _ in range(50):
        if random.random() < 0.5:
            idx = random.randint(0, len(b) - 1)
            b[idx] = str(random.randint(0, 100))
        elif random.random() < 0.5:
            idx = random.randint(0, len(b))
            b.insert(idx, str(random.randint(0, 100)))
        else:
            if len(b) > 1:
                idx = random.randint(0, len(b) - 1)
                b.pop(idx)
    ops = histogram_diff(a, b)
    assert _reconstruct_a(a, b, ops) == a, "reconstruct a failed"
    assert _reconstruct_b(a, b, ops) == b, "reconstruct b failed"
    print("  test_histogram_large: PASS")


def test_unified_diff():
    a = ["line1\n", "line2\n", "line3\n", "line4\n"]
    b = ["line1\n", "line2 modified\n", "line3\n", "line4\n"]
    result = unified_diff(a, b, fromfile="old.txt", tofile="new.txt")
    assert len(result) > 0
    assert result[0] == "--- old.txt"
    assert result[1] == "+++ new.txt"
    assert result[2].startswith("@@")
    print("  test_unified_diff: PASS")


def test_context_diff():
    a = ["line1\n", "line2\n", "line3\n", "line4\n"]
    b = ["line1\n", "line2 modified\n", "line3\n", "line4\n"]
    result = context_diff(a, b, fromfile="old.txt", tofile="new.txt")
    assert len(result) > 0
    assert result[0].startswith("***")
    assert result[1].startswith("---")
    print("  test_context_diff: PASS")


def test_normal_diff():
    a = ["line1\n", "line2\n", "line3\n"]
    b = ["line1\n", "line2 modified\n", "line3\n"]
    result = normal_diff(a, b)
    assert len(result) > 0
    assert any("c" in r for r in result)
    print("  test_normal_diff: PASS")


def test_patch_roundtrip():
    a = ["line1\n", "line2\n", "line3\n", "line4\n", "line5\n"]
    b = ["line1\n", "line2 modified\n", "line3\n", "line4\n", "line6\n"]
    patch_text = unified_diff(a, b, fromfile="old", tofile="new")
    hunks = parse_unified_diff(patch_text)
    result = apply_patch(a, hunks)
    assert result.applied_hunks > 0, f"no hunks applied: {patch_text}"
    assert result.patched == b, f"patch roundtrip failed:\nexpected: {b}\ngot: {result.patched}"
    print("  test_patch_roundtrip: PASS")


def test_patch_with_offset():
    a = ["line1\n", "line2\n", "line3\n", "line4\n", "line5\n"]
    b = ["line1\n", "line2 modified\n", "line3\n", "line4\n", "line5\n"]
    patch_text = unified_diff(a, b)
    hunks = parse_unified_diff(patch_text)
    # Apply to a source with an extra line at top (offset)
    shifted = ["extra\n"] + a
    result = apply_patch(shifted, hunks, max_offset=10)
    assert result.applied_hunks > 0, "should find match with offset"
    print("  test_patch_with_offset: PASS")


def test_three_way_merge_clean():
    base = ["line1\n", "line2\n", "line3\n"]
    ours = ["line1\n", "line2 ours\n", "line3\n"]
    theirs = ["line1\n", "line2\n", "line3 theirs\n"]
    result = three_way_merge(base, ours, theirs)
    assert result.clean, f"should be clean merge, conflicts: {result.conflicts}"
    assert result.lines == ["line1\n", "line2 ours\n", "line3 theirs\n"], f"got {result.lines}"
    print("  test_three_way_merge_clean: PASS")


def test_three_way_merge_conflict():
    base = ["line1\n", "line2\n", "line3\n"]
    ours = ["line1\n", "line2 ours\n", "line3\n"]
    theirs = ["line1\n", "line2 theirs\n", "line3\n"]
    result = three_way_merge(base, ours, theirs)
    assert not result.clean, "should have conflict"
    assert len(result.conflicts) == 1, f"expected 1 conflict, got {len(result.conflicts)}"
    print("  test_three_way_merge_conflict: PASS")


def test_algorithms_agree():
    """All four algorithms should produce valid diffs (same reconstruction)."""
    import random
    random.seed(42)
    a = [str(random.randint(0, 50)) for _ in range(100)]
    b = a.copy()
    for _ in range(20):
        if random.random() < 0.5:
            idx = random.randint(0, len(b) - 1)
            b[idx] = str(random.randint(0, 50))
        elif random.random() < 0.5:
            idx = random.randint(0, len(b))
            b.insert(idx, str(random.randint(0, 50)))
        else:
            if len(b) > 1:
                idx = random.randint(0, len(b) - 1)
                b.pop(idx)

    for name, fn in [("myers", myers_diff), ("lcs", lcs_diff),
                     ("patience", patience_diff), ("histogram", histogram_diff)]:
        ops = fn(a, b)
        assert _reconstruct_a(a, b, ops) == a, f"{name}: reconstruct a failed"
        assert _reconstruct_b(a, b, ops) == b, f"{name}: reconstruct b failed"
    print("  test_algorithms_agree: PASS")


if __name__ == "__main__":
    print("Running diff_merge tests...")
    test_myers_basic()
    test_myers_empty_a()
    test_myers_empty_b()
    test_myers_identical()
    test_myers_completely_different()
    test_myers_large()
    test_lcs_basic()
    test_lcs_lcs()
    test_patience_basic()
    test_patience_large()
    test_histogram_basic()
    test_histogram_large()
    test_unified_diff()
    test_context_diff()
    test_normal_diff()
    test_patch_roundtrip()
    test_patch_with_offset()
    test_three_way_merge_clean()
    test_three_way_merge_conflict()
    test_algorithms_agree()
    print("\nAll tests passed!")