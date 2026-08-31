# suffix-automaton

A suffix automaton toolkit for substring analytics, lexicographic substring queries, absence detection, and common-substring analysis.

## What it does

The project now includes:

- linear-time suffix automaton construction
- substring membership checks
- exact occurrence counting
- distinct substring counting
- repeated-substring analysis
- substring location lookup
- k-th lexicographic distinct substring queries
- shortest absent substring search over a chosen alphabet
- top repeated substring reports
- generalized longest common substring search across multiple strings
- pairwise LCS reporting
- JSON serialization and restoration
- Graphviz DOT export
- a CLI for analysis, membership, counting, locating, export, visualization, and report generation

## How it works

A suffix automaton is a DFA-like compressed representation of all substrings of a text. Each state stores:

- `length`: the maximum substring length represented by the state
- `link`: the suffix link to the next smaller end-position class
- `next`: outgoing transitions
- `first_pos`: one end position for reconstruction
- `occ_count`: propagated end-position count for repetition analysis

Construction uses the standard online extension algorithm with state cloning when a transition split is needed.

### Query strategies

- membership and occurrence queries walk the automaton in `O(m)` for query length `m`
- distinct substring counting uses the standard `len(state) - len(link(state))` contribution formula
- k-th lexicographic substring queries use cached path counts over the DAG of states
- shortest absent substring search performs a BFS over the chosen alphabet and uses the automaton to reject present candidates quickly
- generalized LCS builds the automaton on the shortest string and scans the rest to track the best per-state match length
- location lookup uses the automaton for validation, then Python's substring search for exact spans, including overlapping matches

## Usage

### Install for local development

```bash
cd suffix-automaton
python3 -m venv .venv
. .venv/bin/activate
pip install -e . pytest
```

### Run the test suite

```bash
pytest
```

### Analyze a string

```bash
python3 -m suffix_automaton analyze --text banana
```

Example output:

```text
length: 6
states: 10
distinct_substrings: 15
longest_repeated_substring: 'ana'
longest_repeated_count: 2
alphabet: abn
```

### Query substrings

```bash
python3 -m suffix_automaton contains --text banana ana
python3 -m suffix_automaton count --text banana ana
python3 -m suffix_automaton locate --text banana ana
python3 -m suffix_automaton kth --text banana 3
python3 -m suffix_automaton absent --text banana --alphabet abn
python3 -m suffix_automaton repeats --text banana --limit 5 --json
```

### Export JSON or Graphviz

```bash
python3 -m suffix_automaton export --text banana --output banana.sam.json
python3 -m suffix_automaton dot --text banana --output banana.sam.dot
```

### Longest common substring analysis

```bash
python3 -m suffix_automaton lcs abracadabra cadabrac dabracad
python3 -m suffix_automaton lcs --pairwise banana bandana anagram
```

Example pairwise JSON output:

```json
{
  "longest_common_substring": "ana",
  "pairwise": {
    "0-1": "ana",
    "0-2": "ana",
    "1-2": "ana"
  }
}
```

## Examples

- `banana`: repeated substring `ana`, shortest absent substring over `abn` is `aa`
- `mississippi`: useful for repeated-substring rankings and overlap-heavy location queries
- `abracadabra`, `cadabrac`, `dabracad`: generalized LCS result is `abrac`
