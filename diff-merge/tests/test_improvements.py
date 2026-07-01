"""Tests for the comprehensive improvement features (v3.0).

Covers: side-by-side diff, HTML output, directory diff, diff optimizer,
and logging.
"""

import os
import tempfile
import textwrap
import unittest

from diff_merge.sidebyside import side_by_side
from diff_merge.htmlout import html_diff, html_diff_document
from diff_merge.dirdiff import diff_directories, ChangeType
from diff_merge.optimizer import optimize_diff, optimize_common_edges
from diff_merge.logging_config import setup_logging, get_logger
from diff_merge import myers_diff
from diff_merge.myers import DiffOp, Operation


# ---------------------------------------------------------------------------
# Side-by-side
# ---------------------------------------------------------------------------

class TestSideBySide(unittest.TestCase):

    def test_identical(self):
        a = ["line1", "line2", "line3"]
        b = ["line1", "line2", "line3"]
        result = side_by_side(a, b, width=60)
        self.assertEqual(len(result), 3)
        for line in result:
            self.assertIn("│", line)

    def test_addition(self):
        a = ["line1", "line3"]
        b = ["line1", "line2", "line3"]
        result = side_by_side(a, b, width=60)
        # Should have 3 rows (one for each entry: equal, insert, equal)
        self.assertEqual(len(result), 3)

    def test_deletion(self):
        a = ["line1", "line2", "line3"]
        b = ["line1", "line3"]
        result = side_by_side(a, b, width=60)
        self.assertEqual(len(result), 3)

    def test_replacement(self):
        a = ["hello world", "foo"]
        b = ["hello earth", "foo"]
        result = side_by_side(a, b, width=80)
        self.assertTrue(len(result) >= 2)

    def test_empty_inputs(self):
        result = side_by_side([], [], width=60)
        self.assertEqual(result, [])

    def test_color_mode(self):
        a = ["old"]
        b = ["new"]
        result = side_by_side(a, b, width=60, color=True)
        # Should contain ANSI codes
        self.assertTrue(any("\033[" in line for line in result))

    def test_no_line_numbers(self):
        a = ["line1", "line2"]
        b = ["line1", "line2"]
        result = side_by_side(a, b, width=60, show_line_numbers=False)
        for line in result:
            # Without line numbers, there should be no │ in the number area
            self.assertIn("│", line)

    def test_narrow_width(self):
        """Very narrow width should not crash."""
        a = ["a very long line that exceeds width"]
        b = ["a very long line that is different"]
        result = side_by_side(a, b, width=20)
        self.assertTrue(len(result) >= 1)

    def test_algorithm_choice(self):
        a = ["line1", "line2", "line3"]
        b = ["line1", "changed", "line3"]
        for algo in ["myers", "patience", "histogram", "lcs"]:
            result = side_by_side(a, b, width=60, algorithm=algo)
            self.assertTrue(len(result) >= 1, f"Algorithm {algo} failed")


# ---------------------------------------------------------------------------
# HTML output
# ---------------------------------------------------------------------------

class TestHTMLDiff(unittest.TestCase):

    def test_basic_html(self):
        a = ["hello world"]
        b = ["hello earth"]
        lines = html_diff(a, b, fromfile="a.txt", tofile="b.txt")
        html = "\n".join(lines)
        self.assertIn("<table", html)
        self.assertIn("hello", html)
        self.assertIn("world", html)
        self.assertIn("earth", html)

    def test_full_document(self):
        a = ["line1", "line2"]
        b = ["line1", "changed"]
        doc = html_diff_document(a, b, fromfile="old", tofile="new")
        self.assertIn("<!DOCTYPE html>", doc)
        self.assertIn("</html>", doc)
        self.assertIn("<style>", doc)

    def test_html_escaping(self):
        a = ["<script>alert(1)</script>"]
        b = ["<b>safe</b>"]
        doc = html_diff_document(a, b)
        # The raw <script> tag should not appear unescaped in the content
        self.assertNotIn("<script>alert", doc)
        self.assertIn("&lt;", doc)

    def test_addition_only(self):
        a = ["line1"]
        b = ["line1", "line2"]
        lines = html_diff(a, b)
        html = "\n".join(lines)
        self.assertIn("diff-add", html)

    def test_deletion_only(self):
        a = ["line1", "line2"]
        b = ["line1"]
        lines = html_diff(a, b)
        html = "\n".join(lines)
        self.assertIn("diff-del", html)

    def test_empty_inputs(self):
        lines = html_diff([], [])
        self.assertTrue(len(lines) >= 2)  # container + table

    def test_inline_diff(self):
        a = ["hello world foo"]
        b = ["hello earth foo"]
        lines = html_diff(a, b, inline=True)
        html = "\n".join(lines)
        self.assertIn("<del>", html)
        self.assertIn("<ins>", html)


# ---------------------------------------------------------------------------
# Directory diff
# ---------------------------------------------------------------------------

class TestDirDiff(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.dir_a = os.path.join(self.tmp, "a")
        self.dir_b = os.path.join(self.tmp, "b")
        os.makedirs(self.dir_a)
        os.makedirs(self.dir_b)

    def _write(self, dirpath, relpath, content):
        full = os.path.join(dirpath, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(content)

    def test_added_file(self):
        self._write(self.dir_a, "f1.txt", "content\n")
        self._write(self.dir_b, "f1.txt", "content\n")
        self._write(self.dir_b, "f2.txt", "new\n")
        result = diff_directories(self.dir_a, self.dir_b)
        self.assertEqual(result.total_added, 1)
        added = [c for c in result.changes if c.change_type == ChangeType.ADDED]
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0].path, "f2.txt")

    def test_removed_file(self):
        self._write(self.dir_a, "f1.txt", "content\n")
        self._write(self.dir_a, "f2.txt", "old\n")
        self._write(self.dir_b, "f1.txt", "content\n")
        result = diff_directories(self.dir_a, self.dir_b)
        self.assertEqual(result.total_removed, 1)

    def test_modified_file(self):
        self._write(self.dir_a, "f.txt", "line1\nline2\n")
        self._write(self.dir_b, "f.txt", "line1\nchanged\n")
        result = diff_directories(self.dir_a, self.dir_b)
        self.assertEqual(result.total_modified, 1)
        modified = [c for c in result.changes if c.change_type == ChangeType.MODIFIED]
        self.assertEqual(len(modified), 1)
        self.assertIsNotNone(modified[0].diffstat)
        assert modified[0].diffstat is not None
        self.assertEqual(modified[0].diffstat.additions, 1)
        self.assertEqual(modified[0].diffstat.deletions, 1)

    def test_unchanged_file(self):
        self._write(self.dir_a, "f.txt", "same\n")
        self._write(self.dir_b, "f.txt", "same\n")
        result = diff_directories(self.dir_a, self.dir_b)
        self.assertEqual(result.total_unchanged, 1)
        self.assertEqual(result.total_modified, 0)

    def test_nested_paths(self):
        self._write(self.dir_a, "src/mod/file.py", "x = 1\n")
        self._write(self.dir_b, "src/mod/file.py", "x = 2\n")
        result = diff_directories(self.dir_a, self.dir_b)
        self.assertEqual(result.total_modified, 1)

    def test_summary(self):
        self._write(self.dir_a, "f1.txt", "a\n")
        self._write(self.dir_b, "f1.txt", "a\n")
        self._write(self.dir_b, "f2.txt", "b\n")
        result = diff_directories(self.dir_a, self.dir_b)
        s = result.summary()
        self.assertIn("1 added", s)
        self.assertIn("1 unchanged", s)

    def test_has_changes(self):
        self._write(self.dir_a, "f.txt", "a\n")
        self._write(self.dir_b, "f.txt", "a\n")
        result = diff_directories(self.dir_a, self.dir_b)
        self.assertFalse(result.has_changes)

    def test_empty_dirs(self):
        result = diff_directories(self.dir_a, self.dir_b)
        self.assertEqual(result.total_added, 0)
        self.assertEqual(result.total_removed, 0)
        self.assertEqual(result.total_modified, 0)


# ---------------------------------------------------------------------------
# Diff optimizer
# ---------------------------------------------------------------------------

class TestOptimizer(unittest.TestCase):

    def test_optimize_common_edges_no_common(self):
        a = ["x", "y", "z"]
        b = ["x", "Y", "z"]
        ops = myers_diff(a, b)
        result = optimize_common_edges(ops, a, b)
        # The REPLACE for 'y'->'Y' should remain, no common prefix/suffix in it
        tags = [op.tag.value for op in result]
        self.assertIn("replace", tags)

    def test_optimize_common_edges_with_prefix(self):
        # The REPLACE covers lines with a common prefix line
        a = ["common", "old", "trail"]
        b = ["common", "new", "trail"]
        ops = myers_diff(a, b)
        # Myers should already produce EQUAL, REPLACE, EQUAL
        # but let's force a REPLACE that includes the common line
        fake_ops = [DiffOp(Operation.REPLACE, 0, 3, 0, 3)]
        result = optimize_common_edges(fake_ops, a, b)
        # Should extract "common" as EQUAL at start and "trail" at end
        tags = [op.tag.value for op in result]
        self.assertIn("equal", tags)

    def test_optimize_diff_runs(self):
        a = ["a", "b", "c"]
        b = ["a", "B", "c"]
        ops = myers_diff(a, b)
        result = optimize_diff(ops, a, b)
        self.assertTrue(len(result) >= 1)

    def test_optimize_whitespace(self):
        a = ["  hello  "]
        b = ["hello"]
        ops = myers_diff(a, b)
        result = optimize_diff(ops, a, b, whitespace=True)
        # The whitespace-only change should become EQUAL
        tags = [op.tag.value for op in result]
        self.assertTrue(all(t == "equal" for t in tags))

    def test_optimize_idempotent(self):
        a = ["a", "b", "c", "d"]
        b = ["a", "x", "c", "d"]
        ops = myers_diff(a, b)
        r1 = optimize_diff(ops, a, b)
        r2 = optimize_diff(r1, a, b)
        self.assertEqual(r1, r2)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

class TestLogging(unittest.TestCase):

    def test_get_logger(self):
        logger = get_logger("test")
        self.assertIsNotNone(logger)
        # Logger name should start with "diff_merge"
        self.assertTrue(logger.name.startswith("diff_merge"))

    def test_setup_logging(self):
        logger = setup_logging("DEBUG")
        self.assertEqual(logger.level, 10)  # DEBUG = 10

    def test_logger_no_crash(self):
        logger = get_logger()
        logger.debug("debug message")
        logger.info("info message")
        logger.warning("warning message")


if __name__ == "__main__":
    unittest.main()