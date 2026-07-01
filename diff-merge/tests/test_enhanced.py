"""
Enhanced tests for the diff_merge toolkit (Phase 2 features).
Run with: python3 -m pytest tests/ -v
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from diff_merge import (
    myers_diff,
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
    word_diff,
    highlight_inline,
    compute_diffstat,
    Config,
    load_config,
    save_config,
    preprocess_lines,
    reverse_ops,
    is_binary,
)
from diff_merge.myers import Operation, DiffOp


# ---------------------------------------------------------------------------
# Inline / word-level diff tests
# ---------------------------------------------------------------------------

def test_word_diff_basic():
    parts = word_diff("hello world", "hello earth")
    tags = [t for t, _, _ in parts]
    assert "equal" in tags or "replace" in tags
    print("  test_word_diff_basic: PASS")


def test_highlight_inline_no_color():
    a, b = highlight_inline("hello world", "hello earth", use_color=False)
    assert "hello" in a  # unchanged part preserved
    assert "hello" in b
    print("  test_highlight_inline_no_color: PASS")


def test_highlight_inline_color():
    a, b = highlight_inline("hello world", "hello earth", use_color=True)
    assert "\033[" in a or "\033[" in b  # has ANSI codes
    print("  test_highlight_inline_color: PASS")


def test_highlight_inline_identical():
    a, b = highlight_inline("same text", "same text", use_color=False)
    assert a == "same text"
    assert b == "same text"
    print("  test_highlight_inline_identical: PASS")


# ---------------------------------------------------------------------------
# Diffstat tests
# ---------------------------------------------------------------------------

def test_diffstat_basic():
    a = ["line1", "line2", "line3"]
    b = ["line1", "line2 modified", "line3", "line4"]
    ops = myers_diff(a, b)
    stat = compute_diffstat(ops, a, b)
    assert stat.additions > 0
    assert stat.deletions > 0
    assert stat.unchanged > 0
    print("  test_diffstat_basic: PASS")


def test_diffstat_no_changes():
    a = ["line1", "line2"]
    b = ["line1", "line2"]
    ops = myers_diff(a, b)
    stat = compute_diffstat(ops, a, b)
    assert stat.additions == 0
    assert stat.deletions == 0
    assert stat.unchanged == 2
    assert stat.total_changed == 0
    assert stat.change_ratio == 0.0
    print("  test_diffstat_no_changes: PASS")


def test_diffstat_histogram():
    a = ["l1"] * 10
    b = ["l1"] * 5 + ["l2"] * 5
    ops = myers_diff(a, b)
    stat = compute_diffstat(ops, a, b)
    h = stat.histogram()
    assert isinstance(h, str)
    assert "5+" in h  # 5 additions
    print("  test_diffstat_histogram: PASS")


def test_diffstat_summary():
    a = ["line1", "line2", "line3"]
    b = ["line1", "line2 new", "line3"]
    ops = myers_diff(a, b)
    stat = compute_diffstat(ops, a, b)
    s = stat.summary()
    assert "insertion" in s
    assert "deletion" in s
    print("  test_diffstat_summary: PASS")


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------

def test_config_defaults():
    config = Config()
    assert config.algorithm == "myers"
    assert config.format == "unified"
    assert config.context == 3
    assert config.fuzz == 0
    assert config.color is False
    print("  test_config_defaults: PASS")


def test_config_from_dict():
    config = Config.from_dict({
        "algorithm": "patience",
        "context": 5,
        "color": True,
        "unknown_key": "ignored",
    })
    assert config.algorithm == "patience"
    assert config.context == 5
    assert config.color is True
    print("  test_config_from_dict: PASS")


def test_config_to_dict():
    config = Config(algorithm="histogram", context=10)
    d = config.to_dict()
    assert d["algorithm"] == "histogram"
    assert d["context"] == 10
    print("  test_config_to_dict: PASS")


def test_config_json_roundtrip(tmp_path=None):
    import tempfile, json
    config = Config(algorithm="patience", context=7, color=True)
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        path = f.name
    try:
        save_config(config, path)
        loaded = load_config(path)
        assert loaded.algorithm == "patience"
        assert loaded.context == 7
        assert loaded.color is True
    finally:
        os.unlink(path)
    print("  test_config_json_roundtrip: PASS")


def test_config_toml_roundtrip():
    import tempfile
    config = Config(algorithm="histogram", context=5)
    with tempfile.NamedTemporaryFile(suffix=".toml", mode="w", delete=False) as f:
        path = f.name
    try:
        save_config(config, path)
        loaded = load_config(path)
        assert loaded.algorithm == "histogram"
        assert loaded.context == 5
    finally:
        os.unlink(path)
    print("  test_config_toml_roundtrip: PASS")


# ---------------------------------------------------------------------------
# Utils tests
# ---------------------------------------------------------------------------

def test_reverse_ops():
    a = ["line1", "line2", "line3"]
    b = ["line1", "line2 modified", "line3"]
    ops = myers_diff(a, b)
    reversed_ops = reverse_ops(ops)
    # Reversing should swap INSERT<->DELETE and swap i/j indices
    for orig, rev in zip(ops, reversed_ops):
        if orig.tag == Operation.DELETE:
            assert rev.tag == Operation.INSERT
        elif orig.tag == Operation.INSERT:
            assert rev.tag == Operation.DELETE
        assert rev.i1 == orig.j1
        assert rev.i2 == orig.j2
        assert rev.j1 == orig.i1
        assert rev.j2 == orig.i2
    print("  test_reverse_ops: PASS")


def test_is_binary_text():
    assert is_binary(b"hello world\n") is False
    assert is_binary(b"") is False
    print("  test_is_binary_text: PASS")


def test_is_binary_null():
    assert is_binary(b"hello\x00world") is True
    print("  test_is_binary_null: PASS")


def test_is_binary_high_nontext():
    # Lots of non-text bytes
    data = bytes(range(128, 256)) * 10
    assert is_binary(data) is True
    print("  test_is_binary_high_nontext: PASS")


def test_preprocess_lines_basic():
    config = Config()
    lines = ["hello", "world"]
    processed, indices = preprocess_lines(lines, config)
    assert processed == ["hello", "world"]
    assert indices == [0, 1]
    print("  test_preprocess_lines_basic: PASS")


def test_preprocess_ignore_whitespace():
    config = Config(ignore_whitespace=True)
    lines = ["  hello world  ", "\tfoo\tbar"]
    processed, indices = preprocess_lines(lines, config)
    assert processed == ["hello world", "foo bar"]
    print("  test_preprocess_ignore_whitespace: PASS")


def test_preprocess_ignore_blank():
    config = Config(ignore_blank_lines=True)
    lines = ["hello", "", "world", "   "]
    processed, indices = preprocess_lines(lines, config)
    assert processed == ["hello", "world"]
    assert indices == [0, 2]
    print("  test_preprocess_ignore_blank: PASS")


# ---------------------------------------------------------------------------
# Enhanced patch tests
# ---------------------------------------------------------------------------

def test_patch_reverse():
    a = ["line1", "line2", "line3", "line4"]
    b = ["line1", "line2 modified", "line3", "line5"]
    patch_text = unified_diff(a, b, fromfile="old", tofile="new")
    hunks = parse_unified_diff(patch_text)

    # Reverse the hunks
    for hunk in hunks:
        new_lines = []
        for sign, text in hunk.lines:
            if sign == "+":
                new_lines.append(("-", text))
            elif sign == "-":
                new_lines.append(("+", text))
            else:
                new_lines.append((sign, text))
        hunk.lines = new_lines
        hunk.old_start, hunk.new_start = hunk.new_start, hunk.old_start
        hunk.old_count, hunk.new_count = hunk.new_count, hunk.old_count

    result = apply_patch(b, hunks)
    assert result.patched == a, f"reverse patch failed: {result.patched} != {a}"
    print("  test_patch_reverse: PASS")


def test_patch_with_fuzz():
    a = ["ctx1", "ctx2", "line1", "line2", "ctx3", "ctx4"]
    b = ["ctx1", "ctx2", "line1 modified", "line2", "ctx3", "ctx4"]
    patch_text = unified_diff(a, b, fromfile="old", tofile="new")
    hunks = parse_unified_diff(patch_text)

    # Apply to slightly modified context
    shifted = ["ctx1 modified", "ctx2", "line1", "line2", "ctx3", "ctx4"]
    result = apply_patch(shifted, hunks, fuzz=1, max_offset=10)
    assert result.applied_hunks > 0, "should apply with fuzz"
    print("  test_patch_with_fuzz: PASS")


def test_patch_empty_source():
    a = []
    b = ["line1", "line2"]
    patch_text = unified_diff(a, b, fromfile="old", tofile="new")
    hunks = parse_unified_diff(patch_text)
    result = apply_patch(a, hunks)
    assert result.patched == b, f"empty source patch failed: {result.patched}"
    print("  test_patch_empty_source: PASS")


# ---------------------------------------------------------------------------
# Enhanced merge tests
# ---------------------------------------------------------------------------

def test_merge_both_delete():
    base = ["line1", "line2", "line3"]
    ours = ["line1", "line3"]
    theirs = ["line1", "line3"]
    result = three_way_merge(base, ours, theirs)
    assert result.clean
    assert result.lines == ["line1", "line3"]
    print("  test_merge_both_delete: PASS")


def test_merge_same_change():
    base = ["line1", "line2", "line3"]
    ours = ["line1", "line2 modified", "line3"]
    theirs = ["line1", "line2 modified", "line3"]
    result = three_way_merge(base, ours, theirs)
    assert result.clean
    assert result.lines == ["line1", "line2 modified", "line3"]
    print("  test_merge_same_change: PASS")


def test_merge_insertions():
    base = ["line1", "line3"]
    ours = ["line1", "line2 ours", "line3"]
    theirs = ["line1", "line2 theirs", "line3"]
    result = three_way_merge(base, ours, theirs)
    # Both inserted different content at the same position → conflict
    assert not result.clean, "should have conflict"
    print("  test_merge_insertions: PASS")


def test_merge_no_changes():
    base = ["line1", "line2", "line3"]
    result = three_way_merge(base, base, base)
    assert result.clean
    assert result.lines == ["line1", "line2", "line3"]
    print("  test_merge_no_changes: PASS")


def test_merge_empty_base():
    base = []
    ours = ["line1", "line2"]
    theirs = ["line1", "line3"]
    result = three_way_merge(base, ours, theirs)
    # Both inserted different content → conflict
    assert not result.clean, "should have conflict for empty base"
    print("  test_merge_empty_base: PASS")


# ---------------------------------------------------------------------------
# Format edge cases
# ---------------------------------------------------------------------------

def test_unified_diff_empty():
    result = unified_diff(["a"], ["a"])
    assert result == []
    print("  test_unified_diff_empty: PASS")


def test_context_diff_empty():
    result = context_diff(["a"], ["a"])
    assert result == []
    print("  test_context_diff_empty: PASS")


def test_normal_diff_empty():
    result = normal_diff(["a"], ["a"])
    assert result == []
    print("  test_normal_diff_empty: PASS")


def test_unified_diff_all_changed():
    a = ["line1", "line2"]
    b = ["lineA", "lineB"]
    result = unified_diff(a, b, fromfile="a", tofile="b")
    assert len(result) > 0
    assert result[0] == "--- a"
    assert result[1] == "+++ b"
    print("  test_unified_diff_all_changed: PASS")


# ---------------------------------------------------------------------------
# Large-scale stress tests
# ---------------------------------------------------------------------------

def test_all_algorithms_stress():
    """Stress test all algorithms with large random inputs."""
    import random
    random.seed(12345)
    a = [str(random.randint(0, 20)) for _ in range(500)]
    b = a.copy()
    for _ in range(100):
        if random.random() < 0.4:
            idx = random.randint(0, len(b) - 1)
            b[idx] = str(random.randint(0, 20))
        elif random.random() < 0.4:
            idx = random.randint(0, len(b))
            b.insert(idx, str(random.randint(0, 20)))
        else:
            if len(b) > 1:
                idx = random.randint(0, len(b) - 1)
                b.pop(idx)

    for name, fn in [("myers", myers_diff), ("lcs", lcs_diff),
                     ("patience", patience_diff), ("histogram", histogram_diff)]:
        ops = fn(a, b)
        # Reconstruct a
        ra = []
        for op in ops:
            if op.tag in (Operation.EQUAL, Operation.DELETE, Operation.REPLACE):
                ra.extend(a[op.i1:op.i2])
        assert ra == a, f"{name}: reconstruct a failed"
        # Reconstruct b
        rb = []
        for op in ops:
            if op.tag == Operation.EQUAL:
                rb.extend(a[op.i1:op.i2])
            elif op.tag == Operation.INSERT:
                rb.extend(b[op.j1:op.j2])
            elif op.tag == Operation.REPLACE:
                rb.extend(b[op.j1:op.j2])
        assert rb == b, f"{name}: reconstruct b failed"
    print("  test_all_algorithms_stress: PASS")


if __name__ == "__main__":
    print("Running enhanced tests...")
    test_word_diff_basic()
    test_highlight_inline_no_color()
    test_highlight_inline_color()
    test_highlight_inline_identical()
    test_diffstat_basic()
    test_diffstat_no_changes()
    test_diffstat_histogram()
    test_diffstat_summary()
    test_config_defaults()
    test_config_from_dict()
    test_config_to_dict()
    test_config_json_roundtrip()
    test_config_toml_roundtrip()
    test_reverse_ops()
    test_is_binary_text()
    test_is_binary_null()
    test_is_binary_high_nontext()
    test_preprocess_lines_basic()
    test_preprocess_ignore_whitespace()
    test_preprocess_ignore_blank()
    test_patch_reverse()
    test_patch_with_fuzz()
    test_patch_empty_source()
    test_merge_both_delete()
    test_merge_same_change()
    test_merge_insertions()
    test_merge_no_changes()
    test_merge_empty_base()
    test_unified_diff_empty()
    test_context_diff_empty()
    test_normal_diff_empty()
    test_unified_diff_all_changed()
    test_all_algorithms_stress()
    print("\nAll enhanced tests passed!")