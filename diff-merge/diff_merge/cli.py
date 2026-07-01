"""
Command-line interface for the diff_merge toolkit.

Subcommands:
    diff       — Compute diff between two files
    patch      — Apply a patch to a file
    merge      — Three-way merge
    lcs        — Print longest common subsequence
    stat       — Show diff statistics (diffstat)
    reverse    — Reverse a diff (generate undo patch)
    inline     — Show word-level inline diff
    sidebyside — Show side-by-side visual diff
    html       — Generate HTML diff output
    dirdiff    — Compare two directories
    config     — Show/save/load configuration
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

from .myers import myers_diff, Operation
from .patience import patience_diff
from .histogram import histogram_diff
from .lcs import lcs_diff, longest_common_subsequence
from .format import unified_diff, context_diff, normal_diff
from .patch import parse_unified_diff, apply_patch, PatchError
from .merge import three_way_merge
from .inline import highlight_inline
from .stat import compute_diffstat
from .config import Config, load_config, save_config
from .utils import preprocess_lines, reverse_ops, is_binary
from .sidebyside import side_by_side
from .htmlout import html_diff_document
from .dirdiff import diff_directories
from .optimizer import optimize_diff
from .logging_config import get_logger, setup_logging


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_lines(filepath: str) -> List[str]:
    """Read a file and return its lines (preserving newlines)."""
    path = Path(filepath)
    if not path.exists():
        print(f"Error: file not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if not content:
        return []
    return content.splitlines(keepends=True)


def _read_bytes(filepath: str) -> bytes:
    """Read a file as bytes (for binary detection)."""
    path = Path(filepath)
    if not path.exists():
        print(f"Error: file not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    with open(path, "rb") as f:
        return f.read()


def _strip_lines(lines: List[str]) -> List[str]:
    """Strip trailing newlines from lines."""
    return [line.rstrip("\n\r") for line in lines]


def _get_diff_fn(algorithm: str):
    """Get the diff function for the given algorithm name."""
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


def _check_binary(filepath1: str, filepath2: str = "") -> bool:
    """Check if either file is binary.  Returns True if binary detected."""
    data1 = _read_bytes(filepath1)
    if is_binary(data1):
        print(f"Binary files differ: {filepath1}", file=sys.stderr)
        return True
    if filepath2:
        data2 = _read_bytes(filepath2)
        if is_binary(data2):
            print(f"Binary files differ: {filepath2}", file=sys.stderr)
            return True
    return False


def _apply_config_to_args(args: argparse.Namespace, config: Config) -> None:
    """Override args with config values where args don't explicitly override."""
    # Only override if not explicitly set on command line
    # We use a simple approach: config provides defaults
    if not getattr(args, "_explicit_algorithm", False):
        args.algorithm = config.algorithm
    if not getattr(args, "_explicit_format", False):
        args.format = config.format
    if not getattr(args, "_explicit_context", False):
        args.context = config.context
    if not getattr(args, "_explicit_fuzz", False):
        args.fuzz = config.fuzz
    if not getattr(args, "_explicit_max_offset", False):
        args.max_offset = config.max_offset
    args.ignore_whitespace = config.ignore_whitespace
    args.ignore_blank_lines = config.ignore_blank_lines
    args.color = config.color


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_diff(args: argparse.Namespace) -> None:
    """Compute and print a diff between two files."""
    # Load config if provided
    config = Config()
    if args.config:
        config = load_config(args.config)

    # Apply config defaults
    _apply_config_to_args(args, config)

    # Binary file detection
    if _check_binary(args.oldfile, args.newfile):
        sys.exit(1)

    a = _read_lines(args.oldfile)
    b = _read_lines(args.newfile)
    a_s = _strip_lines(a)
    b_s = _strip_lines(b)

    # Apply whitespace/blank-line preprocessing
    if args.ignore_whitespace or args.ignore_blank_lines:
        a_processed, a_map = preprocess_lines(a_s, config)
        b_processed, b_map = preprocess_lines(b_s, config)
        # Diff the processed lines
        diff_fn = _get_diff_fn(args.algorithm)
        ops = diff_fn(a_processed, b_processed)
        # For formatting, we use the processed lines
        a_use, b_use = a_processed, b_processed
    else:
        a_use, b_use = a_s, b_s

    if args.format == "unified":
        result = unified_diff(
            a_use, b_use,
            fromfile=args.oldfile,
            tofile=args.newfile,
            context=args.context,
            algorithm=args.algorithm,
        )
    elif args.format == "context":
        result = context_diff(
            a_use, b_use,
            fromfile=args.oldfile,
            tofile=args.newfile,
            context=args.context,
            algorithm=args.algorithm,
        )
    elif args.format == "normal":
        result = normal_diff(
            a_use, b_use,
            algorithm=args.algorithm,
        )
    else:
        print(f"Unknown format: {args.format}", file=sys.stderr)
        sys.exit(1)

    if args.color:
        for line in result:
            if line.startswith("+") and not line.startswith("+++"):
                print(f"\033[32m{line}\033[0m")
            elif line.startswith("-") and not line.startswith("---"):
                print(f"\033[31m{line}\033[0m")
            elif line.startswith("@@"):
                print(f"\033[36m{line}\033[0m")
            else:
                print(line)
    else:
        for line in result:
            print(line)


def cmd_patch(args: argparse.Namespace) -> None:
    """Apply a patch to a file."""
    source = _read_lines(args.source)
    source_s = _strip_lines(source)

    if args.patchfile:
        patch_lines = _read_lines(args.patchfile)
    else:
        patch_text = sys.stdin.read()
        patch_lines = patch_text.splitlines(keepends=True)
    patch_s = _strip_lines(patch_lines)

    hunks = parse_unified_diff(patch_s)
    if not hunks:
        print("No hunks found in patch.", file=sys.stderr)
        sys.exit(1)

    if args.reverse:
        # Reverse each hunk's lines: swap + and -
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
            # Swap old/new headers
            hunk.old_start, hunk.new_start = hunk.new_start, hunk.old_start
            hunk.old_count, hunk.new_count = hunk.new_count, hunk.old_count

    result = apply_patch(
        source_s, hunks,
        fuzz=args.fuzz,
        max_offset=args.max_offset,
    )

    for line in result.patched:
        print(line)

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

    if result.rejected_hunks > 0:
        sys.exit(1)


def cmd_merge(args: argparse.Namespace) -> None:
    """Perform a three-way merge."""
    base = _read_lines(args.base)
    ours = _read_lines(args.ours)
    theirs = _read_lines(args.theirs)

    base_s = _strip_lines(base)
    ours_s = _strip_lines(ours)
    theirs_s = _strip_lines(theirs)

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

    a_s = _strip_lines(a)
    b_s = _strip_lines(b)

    lcs = longest_common_subsequence(a_s, b_s)
    for line in lcs:
        print(line)


def cmd_stat(args: argparse.Namespace) -> None:
    """Show diff statistics."""
    if _check_binary(args.oldfile, args.newfile):
        sys.exit(1)

    a = _read_lines(args.oldfile)
    b = _read_lines(args.newfile)
    a_s = _strip_lines(a)
    b_s = _strip_lines(b)

    diff_fn = _get_diff_fn(args.algorithm)
    ops = diff_fn(a_s, b_s)
    stat = compute_diffstat(ops, a_s, b_s)

    print(f" {args.oldfile} | {args.newfile}")
    print(f" {stat.summary()}")
    print(f" {stat.histogram()}")
    print(f" Net change: {stat.net_change:+d} lines")
    print(f" Change ratio: {stat.change_ratio:.1%}")


def cmd_reverse(args: argparse.Namespace) -> None:
    """Generate a reverse diff (undo patch)."""
    a = _read_lines(args.oldfile)
    b = _read_lines(args.newfile)
    a_s = _strip_lines(a)
    b_s = _strip_lines(b)

    # Generate forward diff, then reverse it
    diff_fn = _get_diff_fn(args.algorithm)
    ops = diff_fn(a_s, b_s)
    reversed_ops = reverse_ops(ops)

    # Generate unified diff from reversed ops
    # We need to generate the patch with b as "old" and a as "new"
    result = unified_diff(
        b_s, a_s,
        fromfile=args.newfile,
        tofile=args.oldfile,
        context=args.context,
        algorithm=args.algorithm,
    )
    for line in result:
        print(line)


def cmd_inline(args: argparse.Namespace) -> None:
    """Show word-level inline diff."""
    a = _read_lines(args.file1)
    b = _read_lines(args.file2)
    a_s = _strip_lines(a)
    b_s = _strip_lines(b)

    diff_fn = _get_diff_fn(args.algorithm)
    ops = diff_fn(a_s, b_s)

    use_color = args.color
    for op in ops:
        if op.tag == Operation.EQUAL:
            for i, j in zip(range(op.i1, op.i2), range(op.j1, op.j2)):
                print(f"  {a_s[i]}")
        elif op.tag == Operation.DELETE:
            for i in range(op.i1, op.i2):
                print(f"- {a_s[i]}")
        elif op.tag == Operation.INSERT:
            for j in range(op.j1, op.j2):
                print(f"+ {b_s[j]}")
        elif op.tag == Operation.REPLACE:
            for i, j in zip(range(op.i1, op.i2), range(op.j1, op.j2)):
                ha, hb = highlight_inline(a_s[i], b_s[j], use_color=use_color)
                print(f"- {ha}")
                print(f"+ {hb}")


def cmd_sidebyside(args: argparse.Namespace) -> None:
    """Show a side-by-side visual diff."""
    a = _read_lines(args.file1)
    b = _read_lines(args.file2)
    a_s = _strip_lines(a)
    b_s = _strip_lines(b)

    lines = side_by_side(
        a_s, b_s,
        width=args.width,
        algorithm=args.algorithm,
        color=args.color,
    )
    for line in lines:
        print(line)


def cmd_html(args: argparse.Namespace) -> None:
    """Generate an HTML diff document."""
    a = _read_lines(args.file1)
    b = _read_lines(args.file2)
    a_s = _strip_lines(a)
    b_s = _strip_lines(b)

    doc = html_diff_document(
        a_s, b_s,
        fromfile=args.file1,
        tofile=args.file2,
        algorithm=args.algorithm,
        inline=not args.no_inline,
        title=f"Diff: {args.file1} → {args.file2}",
    )

    if args.output:
        Path(args.output).write_text(doc, encoding="utf-8")
        print(f"HTML diff written to {args.output}", file=sys.stderr)
    else:
        print(doc)


def cmd_dirdiff(args: argparse.Namespace) -> None:
    """Compare two directories."""
    result = diff_directories(args.dir_a, args.dir_b, compute_stats=True)

    for change in result.changes:
        if change.change_type.value == "added":
            print(f"  + {change.path}")
        elif change.change_type.value == "removed":
            print(f"  - {change.path}")
        elif change.change_type.value == "modified":
            ds = change.diffstat
            if ds:
                print(f"  ~ {change.path}  ({ds.summary()})")
            else:
                print(f"  ~ {change.path}")

    print(f"\n{result.summary()}", file=sys.stderr)

    if not result.has_changes:
        print("No changes found.", file=sys.stderr)


def cmd_config(args: argparse.Namespace) -> None:
    """Show, save, or load configuration."""
    if args.action == "show":
        config = Config()
        if args.config_file:
            config = load_config(args.config_file)
        print("Current configuration:")
        for key, value in config.to_dict().items():
            print(f"  {key}: {value}")
    elif args.action == "save":
        config = Config()
        if args.config_file:
            config = load_config(args.config_file)
        save_config(config, args.output)
        print(f"Configuration saved to {args.output}")
    elif args.action == "set":
        # Load existing or create new
        config = Config()
        if args.config_file:
            config = load_config(args.config_file)
        # Parse key=value pairs
        for kv in args.settings:
            if "=" not in kv:
                print(f"Invalid setting: {kv} (expected key=value)", file=sys.stderr)
                sys.exit(1)
            key, _, value = kv.partition("=")
            # Parse value type
            if value.lower() in ("true", "false"):
                setattr(config, key, value.lower() == "true")
            elif value.isdigit():
                setattr(config, key, int(value))
            else:
                setattr(config, key, value)
        if args.output:
            save_config(config, args.output)
            print(f"Configuration saved to {args.output}")
        else:
            for key, value in config.to_dict().items():
                print(f"  {key}: {value}")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="diff_merge",
        description="Text diff, patch, and merge toolkit",
    )
    parser.add_argument("--verbose", action="store_true",
                        help="Enable debug logging")
    parser.add_argument("--log-level", default=None,
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Set logging level")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- diff ---
    diff_parser = subparsers.add_parser("diff", help="Compute diff between two files")
    diff_parser.add_argument("oldfile", help="Original file")
    diff_parser.add_argument("newfile", help="Modified file")
    diff_parser.add_argument("--format", choices=["unified", "context", "normal"],
                             default="unified", help="Output format")
    diff_parser.add_argument("--algorithm", choices=["myers", "patience", "histogram", "lcs"],
                             default="myers", help="Diff algorithm")
    diff_parser.add_argument("--context", type=int, default=3, help="Lines of context")
    diff_parser.add_argument("--config", default=None, help="Config file path")
    diff_parser.add_argument("--color", action="store_true", help="Colorized output")
    diff_parser.add_argument("--ignore-whitespace", action="store_true",
                             help="Ignore whitespace changes")
    diff_parser.add_argument("--ignore-blank-lines", action="store_true",
                             help="Ignore blank line changes")
    diff_parser.set_defaults(func=cmd_diff)

    # --- patch ---
    patch_parser = subparsers.add_parser("patch", help="Apply a patch to a file")
    patch_parser.add_argument("source", help="Source file to patch")
    patch_parser.add_argument("--patchfile", default=None, help="Patch file (default: stdin)")
    patch_parser.add_argument("--fuzz", type=int, default=0, help="Allowed fuzz lines")
    patch_parser.add_argument("--max-offset", type=int, default=100, help="Max line offset")
    patch_parser.add_argument("--reject", action="store_true", help="Write rejected hunks to .rej")
    patch_parser.add_argument("--reverse", action="store_true", help="Reverse the patch (undo)")
    patch_parser.set_defaults(func=cmd_patch)

    # --- merge ---
    merge_parser = subparsers.add_parser("merge", help="Three-way merge")
    merge_parser.add_argument("base", help="Common ancestor file")
    merge_parser.add_argument("ours", help="Our version")
    merge_parser.add_argument("theirs", help="Their version")
    merge_parser.add_argument("--marker-size", type=int, default=7, help="Conflict marker size")
    merge_parser.set_defaults(func=cmd_merge)

    # --- lcs ---
    lcs_parser = subparsers.add_parser("lcs", help="Print longest common subsequence")
    lcs_parser.add_argument("file1", help="First file")
    lcs_parser.add_argument("file2", help="Second file")
    lcs_parser.set_defaults(func=cmd_lcs)

    # --- stat ---
    stat_parser = subparsers.add_parser("stat", help="Show diff statistics")
    stat_parser.add_argument("oldfile", help="Original file")
    stat_parser.add_argument("newfile", help="Modified file")
    stat_parser.add_argument("--algorithm", choices=["myers", "patience", "histogram", "lcs"],
                             default="myers", help="Diff algorithm")
    stat_parser.set_defaults(func=cmd_stat)

    # --- reverse ---
    rev_parser = subparsers.add_parser("reverse", help="Generate reverse (undo) diff")
    rev_parser.add_argument("oldfile", help="Original file")
    rev_parser.add_argument("newfile", help="Modified file")
    rev_parser.add_argument("--algorithm", choices=["myers", "patience", "histogram", "lcs"],
                            default="myers", help="Diff algorithm")
    rev_parser.add_argument("--context", type=int, default=3, help="Lines of context")
    rev_parser.set_defaults(func=cmd_reverse)

    # --- inline ---
    inline_parser = subparsers.add_parser("inline", help="Word-level inline diff")
    inline_parser.add_argument("file1", help="First file")
    inline_parser.add_argument("file2", help="Second file")
    inline_parser.add_argument("--algorithm", choices=["myers", "patience", "histogram", "lcs"],
                               default="myers", help="Diff algorithm")
    inline_parser.add_argument("--color", action="store_true", help="Colorized output")
    inline_parser.set_defaults(func=cmd_inline)

    # --- sidebyside ---
    sbs_parser = subparsers.add_parser("sidebyside",
                                       help="Side-by-side visual diff")
    sbs_parser.add_argument("file1", help="First file")
    sbs_parser.add_argument("file2", help="Second file")
    sbs_parser.add_argument("--algorithm", choices=["myers", "patience", "histogram", "lcs"],
                            default="myers", help="Diff algorithm")
    sbs_parser.add_argument("--width", type=int, default=80, help="Total output width")
    sbs_parser.add_argument("--color", action="store_true", help="Colorized output")
    sbs_parser.set_defaults(func=cmd_sidebyside)

    # --- html ---
    html_parser = subparsers.add_parser("html",
                                         help="Generate HTML diff output")
    html_parser.add_argument("file1", help="First file")
    html_parser.add_argument("file2", help="Second file")
    html_parser.add_argument("--algorithm", choices=["myers", "patience", "histogram", "lcs"],
                             default="myers", help="Diff algorithm")
    html_parser.add_argument("--output", default=None, help="Output HTML file (default: stdout)")
    html_parser.add_argument("--no-inline", action="store_true",
                              help="Disable word-level inline diff")
    html_parser.set_defaults(func=cmd_html)

    # --- dirdiff ---
    dirdiff_parser = subparsers.add_parser("dirdiff",
                                           help="Compare two directories")
    dirdiff_parser.add_argument("dir_a", help="First directory")
    dirdiff_parser.add_argument("dir_b", help="Second directory")
    dirdiff_parser.set_defaults(func=cmd_dirdiff)

    # --- config ---
    config_parser = subparsers.add_parser("config", help="Show/save/load configuration")
    config_parser.add_argument("action", choices=["show", "save", "set"],
                               help="Action to perform")
    config_parser.add_argument("--config-file", default=None, help="Input config file")
    config_parser.add_argument("--output", default=None, help="Output config file")
    config_parser.add_argument("settings", nargs="*", help="key=value pairs (for 'set')")
    config_parser.set_defaults(func=cmd_config)

    args = parser.parse_args()

    # Set up logging if requested
    if getattr(args, "verbose", False):
        setup_logging("DEBUG")
    elif getattr(args, "log_level", None):
        setup_logging(args.log_level)

    logger = get_logger()
    logger.debug("CLI invoked: %s", " ".join(sys.argv[1:]))

    args.func(args)


if __name__ == "__main__":
    main()