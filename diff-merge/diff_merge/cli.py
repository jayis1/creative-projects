"""
Command-line interface for the diff_merge toolkit.

Usage examples:
    python3 -m diff_merge.cli diff old.txt new.txt
    python3 -m diff_merge.cli diff old.txt new.txt --format unified --algorithm patience
    python3 -m diff_merge.cli patch source.txt < patch.diff
    python3 -m diff_merge.cli merge base.txt ours.txt theirs.txt
    python3 -m diff_merge.cli diff old.txt new.txt --format context --context 5
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

from .myers import myers_diff
from .patience import patience_diff
from .histogram import histogram_diff
from .lcs import lcs_diff, longest_common_subsequence
from .format import unified_diff, context_diff, normal_diff
from .patch import parse_unified_diff, apply_patch, PatchError
from .merge import three_way_merge


def _read_lines(filepath: str) -> List[str]:
    """Read a file and return its lines (preserving newlines)."""
    path = Path(filepath)
    if not path.exists():
        print(f"Error: file not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    # Use splitlines(keepends=True) but handle empty files
    if not content:
        return []
    return content.splitlines(keepends=True)


def _ensure_newlines(lines: List[str]) -> List[str]:
    """Ensure each line ends with a newline for diff formatting."""
    result = []
    for line in lines:
        if line and not line.endswith("\n"):
            line = line + "\n"
        result.append(line)
    return result


def _get_diff_fn(algorithm: str):
    if algorithm == "myers":
        return myers_diff
    elif algorithm == "patience":
        return patience_diff
    elif algorithm == "histogram":
        return histogram_diff
    elif algorithm == "lcs":
        return lcs_diff
    else:
        print(f"Error: unknown algorithm '{algorithm}'", file=sys.stderr)
        sys.exit(1)


def cmd_diff(args: argparse.Namespace) -> None:
    """Compute and print a diff between two files."""
    a = _read_lines(args.oldfile)
    b = _read_lines(args.newfile)

    # Normalize: strip newlines for diffing, then add them back
    a_stripped = [line.rstrip("\n\r") for line in a]
    b_stripped = [line.rstrip("\n\r") for line in b]

    if args.format == "unified":
        result = unified_diff(
            a_stripped, b_stripped,
            fromfile=args.oldfile,
            tofile=args.newfile,
            context=args.context,
            algorithm=args.algorithm,
        )
    elif args.format == "context":
        result = context_diff(
            a_stripped, b_stripped,
            fromfile=args.oldfile,
            tofile=args.newfile,
            context=args.context,
            algorithm=args.algorithm,
        )
    elif args.format == "normal":
        result = normal_diff(
            a_stripped, b_stripped,
            algorithm=args.algorithm,
        )
    else:
        print(f"Unknown format: {args.format}", file=sys.stderr)
        sys.exit(1)

    for line in result:
        print(line)


def cmd_patch(args: argparse.Namespace) -> None:
    """Apply a patch to a file."""
    source = _read_lines(args.source)
    source_stripped = [line.rstrip("\n\r") for line in source]

    # Read patch from stdin or file
    if args.patchfile:
        patch_lines = _read_lines(args.patchfile)
    else:
        patch_text = sys.stdin.read()
        patch_lines = patch_text.splitlines(keepends=True)
    patch_stripped = [line.rstrip("\n\r") for line in patch_lines]

    hunks = parse_unified_diff(patch_stripped)
    if not hunks:
        print("No hunks found in patch.", file=sys.stderr)
        sys.exit(1)

    result = apply_patch(
        source_stripped, hunks,
        fuzz=args.fuzz,
        max_offset=args.max_offset,
    )

    # Output patched content
    for line in result.patched:
        print(line)

    # Report to stderr
    print(
        f"Applied {result.applied_hunks} hunks, "
        f"{result.rejected_hunks} rejected, "
        f"fuzz={result.fuzz_used}",
        file=sys.stderr,
    )

    if result.rejected_hunks > 0 and args.reject:
        rej_path = args.source + ".rej"
        with open(rej_path, "w") as f:
            for hunk in result.rejected:
                f.write(
                    f"@@ -{hunk.old_start},{hunk.old_count} "
                    f"+{hunk.new_start},{hunk.new_count} @@\n"
                )
                for sign, text in hunk.lines:
                    f.write(f"{sign}{text}\n")
        print(f"Rejected hunks written to {rej_path}", file=sys.stderr)


def cmd_merge(args: argparse.Namespace) -> None:
    """Perform a three-way merge."""
    base = _read_lines(args.base)
    ours = _read_lines(args.ours)
    theirs = _read_lines(args.theirs)

    # Strip newlines for merging
    base_s = [line.rstrip("\n\r") for line in base]
    ours_s = [line.rstrip("\n\r") for line in ours]
    theirs_s = [line.rstrip("\n\r") for line in theirs]

    result = three_way_merge(
        base_s, ours_s, theirs_s,
        conflict_marker_size=args.marker_size,
    )

    for line in result.lines:
        print(line)

    if result.clean:
        print("Merge completed cleanly (no conflicts).", file=sys.stderr)
    else:
        print(
            f"Merge completed with {len(result.conflicts)} conflict(s).",
            file=sys.stderr,
        )
        sys.exit(1)


def cmd_lcs(args: argparse.Namespace) -> None:
    """Print the longest common subsequence of two files."""
    a = _read_lines(args.file1)
    b = _read_lines(args.file2)

    a_s = [line.rstrip("\n\r") for line in a]
    b_s = [line.rstrip("\n\r") for line in b]

    lcs = longest_common_subsequence(a_s, b_s)
    for line in lcs:
        print(line)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="diff_merge",
        description="Text diff, patch, and merge toolkit",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # diff subcommand
    diff_parser = subparsers.add_parser("diff", help="Compute diff between two files")
    diff_parser.add_argument("oldfile", help="Original file")
    diff_parser.add_argument("newfile", help="Modified file")
    diff_parser.add_argument(
        "--format", choices=["unified", "context", "normal"],
        default="unified", help="Output format (default: unified)",
    )
    diff_parser.add_argument(
        "--algorithm", choices=["myers", "patience", "histogram", "lcs"],
        default="myers", help="Diff algorithm (default: myers)",
    )
    diff_parser.add_argument(
        "--context", type=int, default=3,
        help="Lines of context (default: 3)",
    )
    diff_parser.set_defaults(func=cmd_diff)

    # patch subcommand
    patch_parser = subparsers.add_parser("patch", help="Apply a patch to a file")
    patch_parser.add_argument("source", help="Source file to patch")
    patch_parser.add_argument(
        "--patchfile", default=None,
        help="Patch file (default: read from stdin)",
    )
    patch_parser.add_argument(
        "--fuzz", type=int, default=0,
        help="Allowed fuzz lines (default: 0)",
    )
    patch_parser.add_argument(
        "--max-offset", type=int, default=100,
        help="Max line offset for matching (default: 100)",
    )
    patch_parser.add_argument(
        "--reject", action="store_true",
        help="Write rejected hunks to .rej file",
    )
    patch_parser.set_defaults(func=cmd_patch)

    # merge subcommand
    merge_parser = subparsers.add_parser("merge", help="Three-way merge")
    merge_parser.add_argument("base", help="Common ancestor file")
    merge_parser.add_argument("ours", help="Our version")
    merge_parser.add_argument("theirs", help="Their version")
    merge_parser.add_argument(
        "--marker-size", type=int, default=7,
        help="Conflict marker size (default: 7)",
    )
    merge_parser.set_defaults(func=cmd_merge)

    # lcs subcommand
    lcs_parser = subparsers.add_parser("lcs", help="Print longest common subsequence")
    lcs_parser.add_argument("file1", help="First file")
    lcs_parser.add_argument("file2", help="Second file")
    lcs_parser.set_defaults(func=cmd_lcs)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()