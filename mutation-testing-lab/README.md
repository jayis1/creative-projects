# Mutation Testing Lab

A dependency-free Python mutation-testing runner for small Python modules. It creates temporary source variants (comparison-operator and boolean-literal mutations), executes a supplied unittest suite against each variant in an isolated temporary copy, and reports killed/surviving mutants. Useful for finding tests that execute code but fail to detect meaningful behavioral changes.

## How it works

The tokenizer identifies eligible operators outside comments and strings. Each mutation is applied to a temporary copy of the target module; unittest runs with that temporary directory first on `PYTHONPATH`. A nonzero suite exit kills a mutant; a passing suite means it survived. The original file is never modified.

## Usage

`python3 mutation_lab.py path/to/module.py --tests path/to/tests -v`

Run the included test suite: `python3 -m unittest discover -s tests -v`

Initial scope is deliberately conservative: `<`, `<=`, `>`, `>=`, `==`, `!=`, `and`, `or`, `True`, and `False`. Tests must be importable by unittest discovery.
