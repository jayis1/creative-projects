# Mutation Testing Lab

A dependency-free Python mutation-testing runner for measuring whether unit tests detect behavioral changes. It makes safe source variants in temporary copies, executes a test suite against each, and reports killed versus surviving mutants. The original source is never changed.

## Algorithm

Python's tokenizer identifies supported comparison operators, boolean operators, and boolean literals while skipping strings/comments. Each token is replaced in isolation. The variant is syntax-checked and tested with `unittest`; a nonzero test result kills that mutant. Timeouts and malformed input are reported as errors. `--json` emits a machine-readable summary; `--timeout` bounds each test run.

## Usage

`python3 mutation_lab.py path/to/module.py --tests path/to/tests -v`

JSON report: `python3 mutation_lab.py path/to/module.py --tests path/to/tests --json`

Run tests: `python3 -m unittest discover -s mutation-testing-lab/tests -v`

Supported token replacements: `<`, `<=`, `>`, `>=`, `==`, `!=`, `and`, `or`, `True`, and `False`. The target module should be a single self-contained Python file importable by the test suite. Test discovery is run from an isolated temporary directory; no shell is used.

## Limitations

Mutations that are syntactically invalid are skipped. A test failure counts as killed even if caused by an unrelated test/environment failure, so inspect failures in verbose mode when diagnosing results. This is an educational, bounded tool, not a replacement for mature mutation-testing frameworks.

## Known Issues (Resolved)

- The first version's tests could not import the runner from repository-root invocation; the tests now add their project root to `sys.path` and pass under the documented command.

## Bug Hunt Audit

Reviewed all Python source and tests for tokenizer boundary handling, string/comment exclusion, mutation isolation, timeout handling, temporary-directory cleanup, and command construction. No reproducible implementation defects were found in the audited revision. The empty-source edge case is covered by `test_empty_source_has_no_candidates`; all regression and CLI integration tests pass. This audit does not claim exhaustive security verification.
