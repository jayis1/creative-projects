# suffix-automaton

A suffix automaton toolkit for substring analytics on a single text.

## What it does

Phase 1 ships a real suffix automaton implementation with:

- linear-time automaton construction
- substring membership checks
- distinct substring counting
- repeated-substring analysis
- occurrence counting
- substring location lookup
- JSON serialization and restoration
- a CLI for analysis, membership, counting, locating, export, and longest-common-substring queries

## How it works

A suffix automaton is a DFA-like compressed representation of all substrings of a text. Each state stores:

- `length`: the maximum substring length represented by the state
- `link`: the suffix link to the next smaller end-position class
- `next`: outgoing transitions
- `first_pos`: one end position for reconstruction
- `occ_count`: propagated end-position count for repetition analysis

Construction uses the standard online extension algorithm with state cloning when a transition split is needed.

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

### Query substring membership

```bash
python3 -m suffix_automaton contains --text banana ana
python3 -m suffix_automaton count --text banana ana
python3 -m suffix_automaton locate --text banana ana
```

### Export the automaton

```bash
python3 -m suffix_automaton export --text banana --output banana.sam.json
```

### Longest common substring helper

```bash
python3 -m suffix_automaton lcs abracadabra cadabrac dabracad
```
