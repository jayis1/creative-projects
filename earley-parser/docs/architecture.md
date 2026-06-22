# Architecture

## Overview

The earley-parser package is organized as a modular Python package with
clean separation of concerns:

```
earley_parser/
├── __init__.py      # Public API exports
├── errors.py        # Exception hierarchy
├── grammar.py       # Grammar, GrammarLoader, GrammarStats
├── tokenizer.py     # Tokenizer, TokenSpec, Token
├── parser.py        # EarleyParser, Chart, Item, ParseNode, ParseForest
├── cyk.py           # CNFGrammar, CYKParser (alternative algorithm)
├── analysis.py      # LL1Table, ambiguity detection, grammar comparison
├── config.py        # ParserConfig, load_config, save_config
└── cli.py           # Command-line interface (10 subcommands)
```

## Core Components

### Grammar (`grammar.py`)

The `Grammar` class represents a context-free grammar. It provides:

- **Construction**: `from_rules()` builds from `(lhs, rhs)` pairs.
  `GrammarLoader.load()` parses BNF text files.
- **Nullable computation**: Fixed-point iteration to find all nullable
  non-terminals (those that can derive ε).
- **FIRST sets**: Computed via iterative closure. `first_of_sequence()`
  computes FIRST for an RHS sequence.
- **FOLLOW sets**: Computed via iterative closure using FIRST sets.
  FOLLOW(A) contains all terminals that can appear after A.
- **Productivity**: Non-terminals that can derive a terminal string.
- **Reachability**: Non-terminals reachable from the start symbol.
- **Validation**: Detects missing start symbols, unproductive rules,
  unreachable rules, terminal/non-terminal conflicts.
- **Serialization**: `to_dict()` / `from_dict()` for JSON interchange.

### Earley Parser (`parser.py`)

The `EarleyParser` implements the classic Earley algorithm:

1. **Predict**: When the dot is before a non-terminal N, add all
   productions of N to the current chart.
2. **Scan**: When the dot is before a terminal matching the current
   input token, advance the dot and add to the next chart.
3. **Complete**: When an item is complete, advance any earlier item
   that was waiting for this non-terminal.

Key data structures:
- **Item**: A frozen (hashable) dotted rule `(lhs → α • β, origin)`.
- **Chart**: Per-position item set with O(1) deduplication and an
  index of complete items by LHS for fast complete()-operation lookups.
- **ParseNode**: Tree node with symbol, span, children, and optional
  alternatives for ambiguous parses.
- **ParseForest**: Container for multiple trees with export to JSON,
  DOT, and Lisp S-expressions.

Tree extraction uses left-to-right split-point enumeration with:
- Cycle detection via an ancestor path set
- Memoization for sub-tree reuse (with truncation-aware caching)
- Deep-copying of shared sub-trees to ensure tree independence

### CYK Parser (`cyk.py`)

An alternative O(n³) parser for CNF grammars. Uses bottom-up dynamic
programming: `table[i][length]` = set of non-terminals deriving
`tokens[i:i+length]`. Supports recognition and tree extraction.

### Tokenizer (`tokenizer.py`)

Regex-based tokenizer with:
- Ordered token specs (first match wins)
- Skip support (whitespace, comments)
- Zero-length match protection
- Full token objects with positions (`tokenize_full()`)
- Whitespace fallback for unmatched input

### Analysis (`analysis.py`)

- **LL1Table**: Builds an LL(1) predictive parsing table from FIRST
  and FOLLOW sets. Detects conflicts (multiple entries in one cell).
- **detect_ambiguity**: Empirically tests all strings up to length N.
- **GrammarComparator**: Approximate language equivalence via sampling.
- **compute_bracket_depth**: Maximum nesting depth of non-terminal
  references.

### Config (`config.py`)

Supports JSON, YAML, and TOML configuration files. Handles:
- Grammar file paths (relative to config directory)
- Tokenizer specifications
- Parser options (max_trees, algorithm)
- Logging configuration

### CLI (`cli.py`)

10 subcommands: `recognize`, `tree`, `forest`, `check`, `analyze`,
`ll1`, `chart`, `cyk`, `demo`, `config`.

## Algorithm Complexity

| Algorithm | Time (general) | Time (unambiguous) | Space |
|-----------|----------------|---------------------|-------|
| Earley    | O(n³)          | O(n²)               | O(n²) |
| CYK       | O(n³)          | O(n³)               | O(n²) |

Where n = input length.

## Data Flow

```
BNF text → GrammarLoader → Grammar → EarleyParser → charts → trees → ParseForest
                                                                      ↓
                                                              JSON / DOT / Lisp
```

```
Raw text → Tokenizer → token list → EarleyParser → recognition / trees
```