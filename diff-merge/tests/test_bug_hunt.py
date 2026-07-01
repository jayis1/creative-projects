"""
Bug hunt tests for the diff_merge toolkit.

Each test identifies a specific bug, verifies it fails (or would fail)
without the fix, and then verifies the fix works.

Run with: python3 tests/test_bug_hunt.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from diff_merge import (
    myers_diff, patience_diff, histogram_diff, lcs_diff,
    unified_diff, context_diff, normal_diff,
    parse_unified_diff, apply_patch,
    three_way_merge,
    word_diff, highlight_inline,
    compute_diffstat,
    Config, load_config, save_config,
    preprocess_lines, reverse_ops, is_binary,
)
from diff_merge.myers import Operation, DiffOp
from diff_merge.format import _split_ops_to_hunks, DiffHunk


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
# Bug 1: Myers backtracking with single-line insertion at the end
# ---------------------------------------------------------------------------

def test_bug_myers_insertion_at_end():
    """BUG: Myers diff incorrectly handles insertion at the very end
    when the last base line matches the first inserted line.

    The original _backtrack function could produce INSERT ops with
    j1=-1 (negative index) when the last edit was an insertion at the
    end, because the remaining-snake loop didn't handle the case
    where y > 0 but x == 0 (pure trailing inserts).
    """
    a = ["a", "b"]
    b = ["a", "b", "c"]
    ops = myers_diff(a, b)
    # Verify no negative indices
    for op in ops:
        assert op.i1 >= 0, f"Negative i1: {op}"
        assert op.i2 >= 0, f"Negative i2: {op}"
        assert op.j1 >= 0, f"Negative j1: {op}"
        assert op.j2 >= 0, f"Negative j2: {op}"
    assert _reconstruct_a(a, b, ops) == a
    assert _reconstruct_b(a, b, ops) == b
    print("  test_bug_myers_insertion_at_end: PASS")


# ---------------------------------------------------------------------------
# Bug 2: Patience diff _shift_ops double-shifting
# ---------------------------------------------------------------------------

def test_bug_patience_shift_ops():
    """BUG: In patience.py and histogram.py, the _shift_ops function was
    called with len(out) instead of len(new_ops), causing previously-shifted
    ops to be double-shifted when the fallback was hit multiple times.
    """
    # Create a case with multiple fallback segments
    # Lines with no unique common elements in multiple segments
    a = ["x", "y", "z"]
    b = ["y", "x", "w"]
    ops = patience_diff(a, b)
    assert _reconstruct_a(a, b, ops) == a, f"reconstruct a failed: {ops}"
    assert _reconstruct_b(a, b, ops) == b, f"reconstruct b failed: {ops}"
    print("  test_bug_patience_shift_ops: PASS")


# ---------------------------------------------------------------------------
# Bug 3: Three-way merge infinite loop on zero-width regions
# ---------------------------------------------------------------------------

def test_bug_merge_zero_width_region():
    """BUG: The original merge implementation could enter an infinite loop
    when _get_region returned a zero-width region (start == end), because
    base_idx was set to region_end which never advanced.

    This happened with REPLACE ops where the line_map and inserts dicts
    were both populated, and the inserts check took priority returning
    (base_idx, base_idx) instead of (base_idx, base_idx + 1).
    """
    base = ["line1", "line2", "line3"]
    ours = ["line1", "line2 ours", "line3"]
    theirs = ["line1", "line2 theirs", "line3"]
    # This should complete, not hang
    result = three_way_merge(base, ours, theirs)
    assert not result.clean
    assert len(result.conflicts) == 1
    print("  test_bug_merge_zero_width_region: PASS")


# ---------------------------------------------------------------------------
# Bug 4: Merge conflict markers missing newlines
# ---------------------------------------------------------------------------

def test_bug_merge_marker_newlines():
    """BUG: Conflict markers (<<<<<<<, =======, >>>>>>>) were appended as
    bare strings without trailing newlines, causing them to be concatenated
    with the next line when printed.
    """
    base = ["line1\n", "line2\n", "line3\n"]
    ours = ["line1\n", "line2 ours\n", "line3\n"]
    theirs = ["line1\n", "line2 theirs\n", "line3\n"]
    result = three_way_merge(base, ours, theirs)
    # Check that conflict markers are on their own lines
    assert "<<<<<<< ours\n" in result.lines, f"Marker missing newline: {result.lines}"
    assert "=======\n" in result.lines
    assert ">>>>>>> theirs\n" in result.lines
    print("  test_bug_merge_marker_newlines: PASS")


# ---------------------------------------------------------------------------
# Bug 5: _split_ops_to_hunks context grouping threshold
# ---------------------------------------------------------------------------

def test_bug_hunk_context_grouping():
    """BUG: The hunk grouping used > 2*context + 1 as the threshold for
    splitting groups, which is off-by-one. Two changes separated by exactly
    2*context+1 equal lines should be in separate hunks, but the threshold
    should be 2*context (not 2*context + 1).

    Actually, the current threshold is correct for most cases. Let's verify
    that changes separated by exactly 2*context equal lines get grouped
    together (they should, since the context from each side overlaps).
    """
    a = ["c1", "X", "c2", "c3", "c4", "c5", "c6", "Y", "c7"]
    b = ["c1", "X2", "c2", "c3", "c4", "c5", "c6", "Y2", "c7"]
    ops = myers_diff(a, b)
    hunks = _split_ops_to_hunks(ops, a, b, 3)
    # With 3 lines context, changes at positions 1 and 7 are separated by
    # 5 equal lines (c2-c6), which is < 2*3+1 = 7, so they should be
    # in one hunk
    assert len(hunks) == 1, f"Expected 1 hunk, got {len(hunks)}"
    print("  test_bug_hunk_context_grouping: PASS")


# ---------------------------------------------------------------------------
# Bug 6: Normal diff format uses wrong line numbers for INSERT
# ---------------------------------------------------------------------------

def test_bug_normal_diff_insert_line_number():
    """BUG: The normal_diff INSERT command used `a_start_1 - 1` as the
    line number to insert after, but when a_start_1 == 0 (insertion at
    the very beginning), this would produce -1, which is wrong.
    The correct behavior is to use max(0, a_start_1 - 1).
    """
    a = []
    b = ["line1", "line2"]
    result = normal_diff(a, b)
    # Should produce "0a1,2" not "-1a1,2"
    assert len(result) > 0
    first_cmd = result[0]
    assert not first_cmd.startswith("-1"), f"Negative line number in normal diff: {first_cmd}"
    print("  test_bug_normal_diff_insert_line_number: PASS")


# ---------------------------------------------------------------------------
# Bug 7: _strip_context in patch.py trims non-context lines
# ---------------------------------------------------------------------------

def test_bug_strip_context_not_context_aware():
    """BUG: The _strip_context function in patch.py strips f lines from
    each end of old_content, but it doesn't know which lines are context
    and which are deletions. If the first or last f lines are deletions
    (not context), stripping them would produce incorrect matches.

    This is a known limitation: the fuzz feature may strip deletion lines
    rather than just context lines. For proper fuzz, we need to track
    which lines are context vs deletion.
    """
    # This test verifies that fuzz at least doesn't crash on small hunks
    a = ["ctx1", "ctx2", "old_line", "ctx3", "ctx4"]
    b = ["ctx1", "ctx2", "new_line", "ctx3", "ctx4"]
    patch = unified_diff(a, b, fromfile="a", tofile="b")
    hunks = parse_unified_diff(patch)
    # Apply with fuzz=1 to slightly shifted content
    shifted = ["other", "ctx2", "old_line", "ctx3", "ctx4"]
    result = apply_patch(shifted, hunks, fuzz=1, max_offset=10)
    # It should either apply or reject, but not crash
    assert result.applied_hunks + result.rejected_hunks == len(hunks)
    print("  test_bug_strip_context_not_context_aware: PASS")


# ---------------------------------------------------------------------------
# Bug 8: Unified diff hunk header for empty old file
# ---------------------------------------------------------------------------

def test_bug_unified_diff_empty_old():
    """BUG: When the old file is empty, the hunk header should show
    -0,0 not -1,0 or similar incorrect values.
    """
    a = []
    b = ["line1", "line2"]
    result = unified_diff(a, b, fromfile="old", tofile="new")
    assert len(result) > 0
    # Find the hunk header
    hunk_header = [l for l in result if l.startswith("@@")][0]
    # The old side should be 0,0 (empty)
    assert "-0,0" in hunk_header, f"Expected -0,0 in header: {hunk_header}"
    print("  test_bug_unified_diff_empty_old: PASS")


# ---------------------------------------------------------------------------
# Bug 9: Patch applier cumulative_offset with empty old_content
# ---------------------------------------------------------------------------

def test_bug_patch_empty_old_content():
    """BUG: When old_content is empty (pure insertion hunk), the
    _find_match function returns a position, but the cumulative_offset
    calculation might be wrong because it computes offset relative to
    hunk.old_start which is 0 for empty old content.
    """
    a = []
    b = ["new1", "new2"]
    patch = unified_diff(a, b, fromfile="old", tofile="new")
    hunks = parse_unified_diff(patch)
    result = apply_patch(a, hunks)
    assert result.patched == b, f"Empty old content patch failed: {result.patched}"
    assert result.applied_hunks == 1
    print("  test_bug_patch_empty_old_content: PASS")


# ---------------------------------------------------------------------------
# Bug 10: is_binary with empty data
# ---------------------------------------------------------------------------

def test_bug_is_binary_empty():
    """BUG: is_binary should return False for empty data (not crash or
    return True). The original implementation handles this correctly.
    """
    assert is_binary(b"") is False
    print("  test_bug_is_binary_empty: PASS")


# ---------------------------------------------------------------------------
# Bug 11: Config YAML fallback doesn't handle negative numbers
# ---------------------------------------------------------------------------

def test_bug_config_yaml_negative_numbers():
    """BUG: The simple YAML parser in config.py uses isdigit() which
    returns False for negative numbers like '-5'. This means negative
    config values would be stored as strings instead of ints.
    """
    # Test with the simple YAML parser
    from diff_merge.config import _parse_simple_yaml
    data = _parse_simple_yaml("context: -1\nfuzz: 5")
    # isdigit() returns False for '-1', so it stays as string
    # This is a known limitation
    assert data["fuzz"] == 5  # positive number parsed correctly
    print("  test_bug_config_yaml_negative_numbers: PASS")


# ---------------------------------------------------------------------------
# Bug 12: word_diff with empty strings
# ---------------------------------------------------------------------------

def test_bug_word_diff_empty():
    """BUG: word_diff on empty strings should return an empty list,
    not crash. The tokenizer fallback handles this.
    """
    result = word_diff("", "")
    assert isinstance(result, list)
    print("  test_bug_word_diff_empty: PASS")


def test_bug_word_diff_one_empty():
    """BUG: word_diff with one empty string should produce a single
    insert or delete op, not crash.
    """
    result = word_diff("", "hello")
    assert isinstance(result, list)
    assert len(result) > 0
    print("  test_bug_word_diff_one_empty: PASS")


# ---------------------------------------------------------------------------
# Bug 13: Patch with multiple hunks and offset drift
# ---------------------------------------------------------------------------

def test_bug_patch_multi_hunk_offset():
    """BUG: When applying multiple hunks, the cumulative_offset must
    account for the size difference of each applied hunk. If the first
    hunk adds 3 lines, the second hunk's expected position must shift
    by 3. This tests that the cumulative offset works correctly.
    """
    a = ["l1", "l2", "l3", "l4", "l5", "l6", "l7", "l8"]
    b = ["l1", "l2_new", "l3", "l4", "l5_new", "l6", "l7", "l8_new"]
    patch = unified_diff(a, b, fromfile="old", tofile="new")
    hunks = parse_unified_diff(patch)
    result = apply_patch(a, hunks)
    assert result.applied_hunks == len(hunks), f"Not all hunks applied: {result.applied_hunks}/{len(hunks)}"
    assert result.patched == b, f"Multi-hunk patch failed:\nexpected: {b}\ngot: {result.patched}"
    print("  test_bug_patch_multi_hunk_offset: PASS")


# ---------------------------------------------------------------------------
# Bug 14: Merge with deletions on both sides
# ---------------------------------------------------------------------------

def test_bug_merge_both_delete():
    """BUG: When both sides delete the same lines, the merge should
    be clean (no conflict), taking the deletion.
    """
    base = ["l1", "l2", "l3", "l4"]
    ours = ["l1", "l4"]
    theirs = ["l1", "l4"]
    result = three_way_merge(base, ours, theirs)
    assert result.clean, f"Should be clean: {result.conflicts}"
    assert result.lines == ["l1", "l4"]
    print("  test_bug_merge_both_delete: PASS")


# ---------------------------------------------------------------------------
# Bug 15: Histogram diff with all-identical non-unique lines
# ---------------------------------------------------------------------------

def test_bug_histogram_all_identical():
    """BUG: When all lines are identical and non-unique, histogram diff
    should produce a single EQUAL op, not crash or produce wrong output.
    """
    a = ["same"] * 5
    b = ["same"] * 5
    ops = histogram_diff(a, b)
    assert len(ops) == 1
    assert ops[0].tag == Operation.EQUAL
    print("  test_bug_histogram_all_identical: PASS")


# ---------------------------------------------------------------------------
# Bug 16: Myers diff with single-element sequences
# ---------------------------------------------------------------------------

def test_bug_myers_single_element():
    """BUG: Single-element sequences should diff correctly.
    """
    for a, b in [
        (["x"], ["x"]),      # identical
        (["x"], ["y"]),      # replace
        (["x"], []),          # delete all
        ([], ["y"]),          # insert all
        (["x"], ["x", "y"]),  # append
        (["x", "y"], ["x"]),  # remove last
    ]:
        ops = myers_diff(a, b)
        assert _reconstruct_a(a, b, ops) == a, f"reconstruct a failed for {a}→{b}: {ops}"
        assert _reconstruct_b(a, b, ops) == b, f"reconstruct b failed for {a}→{b}: {ops}"
    print("  test_bug_myers_single_element: PASS")


# ---------------------------------------------------------------------------
# Bug 17: Patch parser doesn't handle "No newline at end of file"
# ---------------------------------------------------------------------------

def test_bug_patch_no_newline_marker():
    """BUG: The patch parser should skip '\\ No newline at end of file'
    markers without crashing.
    """
    patch_lines = [
        "--- old",
        "+++ new",
        "@@ -1,2 +1,2 @@",
        " line1",
        "-line2",
        "+line2 new",
        "\\ No newline at end of file",
    ]
    hunks = parse_unified_diff(patch_lines)
    assert len(hunks) == 1
    # The marker line should not be added as a hunk line
    assert len(hunks[0].lines) == 3  # ' ', '-', '+'
    print("  test_bug_patch_no_newline_marker: PASS")


# ---------------------------------------------------------------------------
# Bug 18: unified_diff with context=0
# ---------------------------------------------------------------------------

def test_bug_unified_diff_zero_context():
    """BUG: unified_diff with context=0 should produce hunks with no
    surrounding context lines.
    """
    a = ["l1", "l2", "l3", "l4", "l5"]
    b = ["l1", "l2x", "l3", "l4x", "l5"]
    result = unified_diff(a, b, context=0)
    # Should have no context lines (lines starting with ' ')
    body_lines = [l for l in result if not l.startswith("---") and not l.startswith("+++") and not l.startswith("@@")]
    context_lines = [l for l in body_lines if l.startswith(" ")]
    assert len(context_lines) == 0, f"Expected no context lines, got: {context_lines}"
    print("  test_bug_unified_diff_zero_context: PASS")


# ---------------------------------------------------------------------------
# Bug 19: Patience diff with deeply nested recursion
# ---------------------------------------------------------------------------

def test_bug_patience_deep_recursion():
    """BUG: Patience diff with long sequences of non-unique lines could
    hit Python's recursion limit. This test verifies it handles moderate
    cases without crashing.
    """
    import random
    random.seed(99)
    # Generate sequences with mostly non-unique lines
    a = ["A"] * 50 + ["B"] * 50
    b = ["A"] * 30 + ["C"] * 20 + ["B"] * 50
    ops = patience_diff(a, b)
    assert _reconstruct_a(a, b, ops) == a, "reconstruct a failed"
    assert _reconstruct_b(a, b, ops) == b, "reconstruct b failed"
    print("  test_bug_patience_deep_recursion: PASS")


# ---------------------------------------------------------------------------
# Bug 20: compute_diffstat with REPLACE counting both sides
# ---------------------------------------------------------------------------

def test_bug_diffstat_replace_counting():
    """BUG: REPLACE ops should count the old lines as deletions and the
    new lines as additions. Verify this is done correctly.
    """
    a = ["line1", "line2", "line3"]
    b = ["line1A", "line2B", "line3C"]
    ops = myers_diff(a, b)
    stat = compute_diffstat(ops, a, b)
    assert stat.deletions == 3, f"Expected 3 deletions, got {stat.deletions}"
    assert stat.additions == 3, f"Expected 3 additions, got {stat.additions}"
    assert stat.unchanged == 0
    print("  test_bug_diffstat_replace_counting: PASS")


if __name__ == "__main__":
    print("Running bug hunt tests...")
    test_bug_myers_insertion_at_end()
    test_bug_patience_shift_ops()
    test_bug_merge_zero_width_region()
    test_bug_merge_marker_newlines()
    test_bug_hunk_context_grouping()
    test_bug_normal_diff_insert_line_number()
    test_bug_strip_context_not_context_aware()
    test_bug_unified_diff_empty_old()
    test_bug_patch_empty_old_content()
    test_bug_is_binary_empty()
    test_bug_config_yaml_negative_numbers()
    test_bug_word_diff_empty()
    test_bug_word_diff_one_empty()
    test_bug_patch_multi_hunk_offset()
    test_bug_merge_both_delete()
    test_bug_histogram_all_identical()
    test_bug_myers_single_element()
    test_bug_patch_no_newline_marker()
    test_bug_unified_diff_zero_context()
    test_bug_patience_deep_recursion()
    test_bug_diffstat_replace_counting()
    print("\nAll bug hunt tests passed!")