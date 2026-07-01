"""
Additional bug hunt tests — edge cases found during thorough review.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from diff_merge import (
    myers_diff, patience_diff, histogram_diff, lcs_diff,
    unified_diff, context_diff, normal_diff,
    parse_unified_diff, apply_patch,
    three_way_merge,
    compute_diffstat,
    is_binary,
)
from diff_merge.myers import Operation, DiffOp


def _reconstruct_a(a, b, ops):
    result = []
    for op in ops:
        if op.tag in (Operation.EQUAL, Operation.DELETE, Operation.REPLACE):
            result.extend(a[op.i1:op.i2])
    return result


def _reconstruct_b(a, b, ops):
    result = []
    for op in ops:
        if op.tag == Operation.EQUAL:
            result.extend(a[op.i1:op.i2])
        elif op.tag == Operation.INSERT:
            result.extend(b[op.j1:op.j2])
        elif op.tag == Operation.REPLACE:
            result.extend(b[op.j1:op.j2])
    return result


# ---------------------------------------------------------------------------
# Bug 21: Normal diff DELETE uses 0-based j1 instead of 1-based
# ---------------------------------------------------------------------------

def test_bug_normal_diff_delete_line_number():
    """BUG: The DELETE command in normal_diff used op.j1 (0-based) as the
    line number in the new file, but normal diff convention uses 1-based
    line numbers. The correct value should be op.j1 (0-based index) which
    represents "delete after this many lines of the new file" — actually
    this IS correct for the 'd' command. 'NdM' means delete line N from
    old, leaving M lines of new above it.
    """
    a = ["l1", "l2", "l3"]
    b = ["l1", "l3"]
    result = normal_diff(a, b)
    # Should be "2d1" — delete line 2, with 1 line of new file above
    assert result[0] == "2d1", f"Expected '2d1', got '{result[0]}'"
    print("  test_bug_normal_diff_delete_line_number: PASS")


# ---------------------------------------------------------------------------
# Bug 22: Normal diff REPLACE with different counts
# ---------------------------------------------------------------------------

def test_bug_normal_diff_replace_different_counts():
    """Verify REPLACE with unequal old/new line counts."""
    a = ["l1", "l2", "l3"]
    b = ["l1", "lX", "lY", "lZ", "l3"]
    result = normal_diff(a, b)
    # Should produce "2,2c2,4" — lines 2-2 of old become lines 2-4 of new
    assert "2c2" in result[0], f"Expected '2c2', got '{result[0]}'"
    print("  test_bug_normal_diff_replace_different_counts: PASS")


# ---------------------------------------------------------------------------
# Bug 23: is_binary performance with set vs bytes
# ---------------------------------------------------------------------------

def test_bug_is_binary_set_performance():
    """BUG: The original is_binary used `bytes(range(32,127))` and checked
    membership byte-by-byte against a bytes object. This is O(n*m) where
    m is the length of text_chars. Using a set makes it O(n).
    """
    import time
    data = b"Hello, world!\n" * 1000
    t0 = time.time()
    result = is_binary(data)
    t1 = time.time()
    assert result is False
    assert t1 - t0 < 1.0, f"is_binary too slow: {t1-t0:.3f}s"
    print("  test_bug_is_binary_set_performance: PASS")


# ---------------------------------------------------------------------------
# Bug 24: is_binary sampling for large files
# ---------------------------------------------------------------------------

def test_bug_is_binary_sampling():
    """BUG: For very large files, is_binary iterated over every byte.
    Now it samples the first 8000 bytes for efficiency.
    """
    # Large text file (1MB)
    data = b"Hello, world!\n" * 80000  # ~1MB
    result = is_binary(data)
    assert result is False
    print("  test_bug_is_binary_sampling: PASS")


# ---------------------------------------------------------------------------
# Bug 25: Patch applier with out-of-order hunks
# ---------------------------------------------------------------------------

def test_bug_patch_out_of_order_hunks():
    """BUG: The patch applier assumes hunks are in order. If they're not,
    the cumulative_offset calculation could be wrong. Verify that
    out-of-order hunks at least don't crash (they might not apply correctly
    though — this is a known limitation).
    """
    a = ["l1", "l2", "l3", "l4"]
    b = ["l1", "l2x", "l3", "l4x"]
    patch = unified_diff(a, b, fromfile="old", tofile="new")
    hunks = parse_unified_diff(patch)
    # Reverse the hunks order
    if len(hunks) > 1:
        hunks.reverse()
    result = apply_patch(a, hunks)
    # Should not crash
    assert isinstance(result.patched, list)
    print("  test_bug_patch_out_of_order_hunks: PASS")


# ---------------------------------------------------------------------------
# Bug 26: Merge with consecutive non-overlapping changes on same side
# ---------------------------------------------------------------------------

def test_bug_merge_consecutive_changes_same_side():
    """Verify that consecutive non-overlapping changes on the same side
    don't produce false conflicts.
    """
    base = ["l1", "l2", "l3", "l4", "l5"]
    ours = ["l1", "l2x", "l3", "l4x", "l5"]
    theirs = ["l1", "l2", "l3", "l4", "l5"]
    result = three_way_merge(base, ours, theirs)
    assert result.clean, f"Should be clean: {result.conflicts}"
    assert result.lines == ours
    print("  test_bug_merge_consecutive_changes_same_side: PASS")


# ---------------------------------------------------------------------------
# Bug 27: Unified diff with single-line files
# ---------------------------------------------------------------------------

def test_bug_unified_diff_single_line():
    a = ["only"]
    b = ["changed"]
    result = unified_diff(a, b, fromfile="a", tofile="b")
    assert len(result) > 0
    assert result[0] == "--- a"
    assert result[1] == "+++ b"
    # Should have a hunk header
    assert any(l.startswith("@@") for l in result)
    print("  test_bug_unified_diff_single_line: PASS")


# ---------------------------------------------------------------------------
# Bug 28: Context diff with only deletions
# ---------------------------------------------------------------------------

def test_bug_context_diff_only_deletions():
    a = ["l1", "l2", "l3", "l4"]
    b = ["l1", "l4"]
    result = context_diff(a, b, fromfile="a", tofile="b")
    assert len(result) > 0
    # Should have "***" and "---" headers
    assert any(l.startswith("***") for l in result)
    assert any(l.startswith("---") for l in result)
    print("  test_bug_context_diff_only_deletions: PASS")


# ---------------------------------------------------------------------------
# Bug 29: LCS diff with all-same elements
# ---------------------------------------------------------------------------

def test_bug_lcs_all_same():
    a = ["x"] * 10
    b = ["x"] * 10
    ops = lcs_diff(a, b)
    assert len(ops) == 1
    assert ops[0].tag == Operation.EQUAL
    assert _reconstruct_a(a, b, ops) == a
    assert _reconstruct_b(a, b, ops) == b
    print("  test_bug_lcs_all_same: PASS")


# ---------------------------------------------------------------------------
# Bug 30: Histogram diff with non-overlapping repeated lines
# ---------------------------------------------------------------------------

def test_bug_histogram_repeated_non_overlapping():
    """Verify histogram diff handles repeated lines that don't overlap
    between the two sequences.
    """
    a = ["A", "B", "A", "C", "A"]
    b = ["A", "B", "D", "A", "C", "A"]
    ops = histogram_diff(a, b)
    assert _reconstruct_a(a, b, ops) == a
    assert _reconstruct_b(a, b, ops) == b
    print("  test_bug_histogram_repeated_non_overlapping: PASS")


if __name__ == "__main__":
    print("Running additional bug hunt tests...")
    test_bug_normal_diff_delete_line_number()
    test_bug_normal_diff_replace_different_counts()
    test_bug_is_binary_set_performance()
    test_bug_is_binary_sampling()
    test_bug_patch_out_of_order_hunks()
    test_bug_merge_consecutive_changes_same_side()
    test_bug_unified_diff_single_line()
    test_bug_context_diff_only_deletions()
    test_bug_lcs_all_same()
    test_bug_histogram_repeated_non_overlapping()
    print("\nAll additional bug hunt tests passed!")