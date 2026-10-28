#!/usr/bin/env python3
"""Small, safe mutation-testing runner for Python modules."""
import argparse
import ast
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tokenize

MUTATIONS = {"<": "<=", "<=": "<", ">": ">=", ">=": ">", "==": "!=", "!=": "==", "and": "or", "or": "and", "True": "False", "False": "True"}


def candidates(source):
    """Return (start,end,replacement,label) edits, excluding comments and strings."""
    result = []
    lines = source.splitlines(keepends=True)
    offsets = []
    n = 0
    for line in lines:
        offsets.append(n)
        n += len(line)
    try:
        tokens = tokenize.generate_tokens(iter(source.splitlines(keepends=True)).__next__)
        for token in tokens:
            replacement = MUTATIONS.get(token.string)
            if replacement is None or token.type not in (tokenize.OP, tokenize.NAME):
                continue
            start = offsets[token.start[0]-1] + token.start[1]
            end = offsets[token.end[0]-1] + token.end[1]
            result.append((start, end, replacement, token.string))
    except (tokenize.TokenError, IndentationError) as exc:
        raise ValueError(f"cannot tokenize module: {exc}") from exc
    return result


def run(target, tests, verbose=False):
    target, tests = target.resolve(), tests.resolve()
    if not target.is_file() or target.suffix != ".py":
        raise ValueError("target must be an existing .py file")
    if not tests.is_dir():
        raise ValueError("tests must be an existing directory")
    source = target.read_text(encoding="utf-8")
    ast.parse(source, filename=str(target))
    edits = candidates(source)
    if not edits:
        raise ValueError("no supported mutation operators found")
    killed = survived = 0
    for index, (start, end, replacement, original) in enumerate(edits, 1):
        mutated = source[:start] + replacement + source[end:]
        try:
            ast.parse(mutated, filename=str(target))
        except SyntaxError:
            continue
        with tempfile.TemporaryDirectory(prefix="mutation-lab-") as tmp:
            root = Path(tmp)
            relative = target.name
            (root / relative).write_text(mutated, encoding="utf-8")
            # Copy test tree so test discovery runs in an isolated directory.
            shutil.copytree(tests, root / "tests")
            env = os.environ.copy()
            env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
            proc = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=20)
        dead = proc.returncode != 0
        killed += int(dead)
        survived += int(not dead)
        if verbose:
            print(f"{index}: {original}->{replacement}: {'KILLED' if dead else 'SURVIVED'}")
    total = killed + survived
    print(f"Mutation score: {killed}/{total} killed ({killed / total:.1%})" if total else "No syntactically valid mutants")
    return 0 if total else 2


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    parser.add_argument("--tests", type=Path, required=True)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run(args.target, args.tests, args.verbose)
    except (OSError, ValueError, SyntaxError, subprocess.TimeoutExpired) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
