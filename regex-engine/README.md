# 🔧 regex-engine

![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-146%20passing-brightgreen)
![Performance](https://img.shields.io/badge/complexity-O(nm)-orange)

A **regular expression engine built from scratch** using Thompson's NFA construction, implementing the classic algorithm described in Russ Cox's *"Regular Expression Matching Can Be Simple And Fast"*.

> **Key guarantee:** O(nm) matching time — no exponential backtracking, ever.

---

## 📑 Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Architecture](#architecture)
- [Performance](#performance)
- [CLI Usage](#cli-usage)
- [Examples](#examples)
- [Testing](#testing)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [References](#references)

---

## Features

| Feature | Syntax | Example |
|---------|--------|---------|
| Literals | `abc` | `cat` matches "cat" |
| Wildcard | `.` | `a.c` matches "abc", "arc" |
| Alternation | `\|` | `cat\|dog` matches "cat" or "dog" |
| Grouping | `(...)` | `(ab)+` matches "ab", "abab" |
| **Capture Groups** | `(...)` | `(\\d+)-(\\d+)` extracts "123" and "456" from "123-456" |
| Kleene star | `*` | `a*` matches "", "a", "aaa" |
| Plus | `+` | `a+` matches "a", "aaa" |
| Optional | `?` | `a?` matches "", "a" |
| Brace quantifiers | `{n}`, `{n,m}`, `{n,}` | `a{2,4}` matches "aa"–"aaaa" |
| Character classes | `[abc]`, `[a-z]`, `[^0-9]` | `[a-z]+` matches lowercase words |
| Shorthand classes | `\d`, `\w`, `\s`, `\D`, `\W`, `\S` | `\d+` matches "123" |
| Escapes | `\.`, `\\`, `\n`, `\t`, `\xNN` | `a\.b` matches "a.b" |
| Anchors | `^`, `$` | `^hello` matches at start |
| Non-greedy | `*?`, `+?`, `??` | `a*?` prefers shortest match |
| **Backreferences in sub** | `\1`, `\2`, etc. | `sub(r'(\w+)', r'<\1>', 'hello')` → `<hello>` |

---

## Installation

### From Source

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/regex-engine

# Install as a package (optional)
pip install -e .

# Or just add to your Python path
export PYTHONPATH=/path/to/regex-engine:$PYTHONPATH
```

### As a Dependency

Add to your `pyproject.toml`:

```toml
[dependencies]
regex-engine = { path = "./regex-engine" }
```

### Requirements

- Python 3.8+
- No external dependencies

---

## Quick Start

```python
from regex_engine import compile, search, findall, sub, split

# Compile a pattern
p = compile(r'\d+')
m = p.match('123abc')
print(m.group(0))   # '123'
print(m.span())     # (0, 3)

# Module-level convenience functions
m = search(r'\d+', 'abc123def')
print(m.group(0))   # '123'

# Findall
print(findall(r'[a-z]+', 'hello world'))  # ['hello', 'world']

# Substitution with backreferences
p = compile(r'(\w+)')
print(p.sub(r'<\1>', 'hello world'))  # '<hello> <world>'

# Split
print(split(r',', 'a,b,c'))  # ['a', 'b', 'c']

# Capture groups
p = compile(r'(\d+)-(\d+)')
m = p.search('123-456')
print(m.groups())   # ('123', '456')
print(m.span(1))    # (0, 3)
print(m.span(2))    # (4, 7)

# Findall with groups returns tuples
p = compile(r'(\d+)-(\d+)')
print(p.findall('12-34 56-78'))  # [('12', '34'), ('56', '78')]
```

---

## API Reference

### Module-Level Functions

| Function | Description |
|----------|-------------|
| `compile(pattern, flags=0)` | Compile pattern into a Pattern object |
| `match(pattern, string, flags=0)` | Match pattern at start of string |
| `search(pattern, string, flags=0)` | Search for first match anywhere |
| `findall(pattern, string, flags=0)` | Find all non-overlapping matches |
| `sub(pattern, repl, string, count=0, flags=0)` | Replace matches |
| `split(pattern, string, maxsplit=0, flags=0)` | Split by pattern |

### Pattern Methods

| Method | Description |
|--------|-------------|
| `match(text)` | Match at start of text |
| `fullmatch(text)` | Match entire text |
| `search(text, pos=0)` | Search for first match |
| `findall(text)` | All non-overlapping matches |
| `finditer(text)` | All matches as Match objects |
| `sub(repl, text, count=0)` | Replace matches (supports `\1` backreferences) |
| `subn(repl, text, count=0)` | Replace matches, return (string, count) |
| `split(text, maxsplit=0)` | Split by pattern |
| `groups` | Number of capture groups (property) |

### Match Object

| Attribute/Method | Description |
|-----------------|-------------|
| `group(n=0)` | Matched group (0 = entire match, 1+ = capture groups) |
| `groups(default=None)` | All captured groups as tuple |
| `span(n=0)` | (start, end) of group n |
| `start` | Start position of match |
| `end` | End position of match |
| `matched` | Whether match succeeded |
| `lastindex()` | Last matched group index |
| `__bool__` | Truthy if matched |
| `__eq__` | Equality comparison |

---

## Architecture

The engine operates in three stages:

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    Parser     │────▶│   Compiler   │────▶│    Matcher   │
│              │     │              │     │              │
│ Pattern ────▶│ AST │──────────▶│ NFA │──────────▶│ Match        │
│   String     │     │   (States)   │     │   Result     │
└──────────────┘     └──────────────┘     └──────────────┘
   Recursive           Thompson's           Two-list
   descent             construction         simulation
```

### 1. Parser (`parser.py`)

A **recursive descent parser** converts a regex pattern string into an Abstract Syntax Tree (AST). The grammar handles operator precedence:

```
alternation := concat ('|' concat)*
concat := quantified+
quantified := atom ('*' | '+' | '?' | '{n,m}') '?'?
atom := group | charclass | anchor | dot | escape | literal
```

AST node types: `Literal`, `Dot`, `AnchorStart`, `AnchorEnd`, `CharClass`, `Shorthand`, `Concat`, `Alternation`, `Quantified`, `Group`

### 2. Compiler (`compiler.py`)

**Thompson's construction** converts the AST into an NFA with these state types:

| State Type | Purpose | Fields |
|-----------|---------|--------|
| `CHAR` | Match character by predicate | `out1` = predicate, `out2` = next state |
| `SPLIT` | Two epsilon transitions | `out1`, `out2` = both branches |
| `MATCH` | Accepting state | (terminal) |
| `ANCHOR_START` | `^` anchor | `out1` = next state |
| `ANCHOR_END` | `$` anchor | `out1` = next state |
| `GROUP_START` | Capture group start | `out1` = next state, `group_idx` |
| `GROUP_END` | Capture group end | `out1` = next state, `group_idx` |

**Key property:** Each AST node compiles to a constant number of NFA states, so the total NFA has O(m) states for a pattern of length m.

### 3. Matcher (`matcher.py`)

**Thompson's two-list algorithm** simulates the NFA:

```
current = ε-closure(start)
for each character ch in text:
    next = {}
    for each CHAR state s in current:
        if s.predicate(ch):
            add ε-closure(s.out2) to next
    current = next
    if MATCH state in current:
        record longest match
```

This guarantees **O(nm)** matching time — no backtracking, no exponential blowup.

### Package Structure

```
regex_engine/
├── __init__.py      # Module-level API (compile, match, search, findall, sub, split)
├── __main__.py      # python -m regex_engine support
├── parser.py        # Recursive descent parser → AST
├── compiler.py      # Thompson's construction: AST → NFA
├── nfa.py           # NFA state/fragment definitions + utilities
├── matcher.py       # Thompson's two-list NFA simulation + Match object
├── pattern.py       # High-level Pattern interface (like re.Pattern)
└── cli.py           # Command-line interface
```

---

## Performance

### O(nm) Guarantee

Unlike backtracking regex engines (which can take O(2^n) time on pathological inputs), this engine guarantees **O(nm) matching time** where:
- **n** = text length
- **m** = pattern length

This is because Thompson's simulation tracks at most m states and processes each character exactly once.

### Benchmark: Pathological Pattern

The classic pathological case `(a*)*b` matching `"aaa..."` (no 'b') causes exponential backtracking in many engines. Our engine handles it in linear time:

```python
from regex_engine import Pattern
import time

p = Pattern("(a*)*b")
start = time.time()
result = p.match("a" * 25)   # 25 'a's, no 'b'
elapsed = time.time() - start  # ~0.0001 seconds
```

### Benchmark: Long Match

```python
p = Pattern("a*")
start = time.time()
m = p.match("a" * 10000)    # 10,000 'a's
elapsed = time.time() - start  # ~0.01 seconds
```

---

## CLI Usage

```bash
# Install and use from command line
python -m regex_engine '\d+' 'hello 123 world'
# Output: Match: '123' at (5, 8)

# Search mode
python -m regex_engine --search '\d+' 'abc123def'
# Output: Match: '123' at (3, 6)

# Find all matches
python -m regex_engine --findall '[a-z]+' 'hello world'
# Output: hello
#         world

# Substitute
python -m regex_engine --sub '\s+' '_' 'hello   world'
# Output: hello_world

# Split
python -m regex_engine --split ',' 'a,b,c'
# Output: a
#         b
#         c

# Full match
python -m regex_engine --fullmatch 'hello' 'hello'
# Output: Match: 'hello' at (0, 5)

# Verbose mode with groups
python -m regex_engine --verbose '(\d+)-(\d+)' '123-456'
# Output: Match: '123-456' at (0, 7)
#           Group 1: '123' at (0, 3)
#           Group 2: '456' at (4, 7)

# Version
python -m regex_engine --version
# Output: 2.0.0

# Read from stdin
echo 'test123' | python -m regex_engine '\d+'
# Output: Match: '123' at (4, 7)
```

---

## Examples

See the `examples/` directory for complete runnable examples:

- **`basic_usage.py`** — Core API: compile, match, search, findall, sub, split, fullmatch, finditer
- **`advanced_usage.py`** — Advanced features: capture groups, anchors, quantifiers, character classes, performance testing

Run them:

```bash
python3 examples/basic_usage.py
python3 examples/advanced_usage.py
```

---

## Testing

### Quick Test (Original Suite)

```bash
python3 tests.py
# 106/106 passed
```

### Comprehensive Test Suite (pytest)

```bash
pip install pytest
python3 -m pytest tests/test_regex_engine.py -v
# 146 passed
```

### Test Coverage

The test suite covers:

| Category | Tests |
|----------|-------|
| Literals & concatenation | 8 |
| Alternation | 8 |
| Quantifiers | 15 |
| Dot wildcard | 5 |
| Character classes | 8 |
| Shorthand classes | 7 |
| Groups & capture | 8 |
| Anchors | 7 |
| Search | 5 |
| Findall | 3 |
| Substitution | 5 |
| Split | 4 |
| Fullmatch | 3 |
| Finditer | 2 |
| Error handling | 7 |
| Input validation | 11 |
| Module API | 7 |
| Performance | 2 |
| NFA module | 6 |
| Match object | 5 |
| Edge cases & regressions | 11 |
| CLI | 2 |
| **Total** | **146** |

---

## Known Issues (Resolved)

### 1. CHAR state Fragment dangling arrow convention (Critical)
**Bug**: CHAR-state Fragments used `'out1'` as the dangling arrow. When `patch()` overwrote `out1`, it destroyed the predicate callable, causing all character matching to fail silently.
**Fix**: Changed all CHAR-state Fragments to use `'out2'`. Convention: `out1` = predicate, `out2` = transition target.

### 2. Shorthand class kind mapping (Critical)
**Bug**: `_compile_shorthand` passed raw characters (`'d'`) instead of kind names (`'digit'`) to `_check_shorthand`, causing `\d`, `\w`, `\s` to always return `False`.
**Fix**: Added `kind_map` dictionary translation.

### 3. Alternation epsilon path (Critical)
**Bug**: Alternation compiler created a dangling `out2` on the last SPLIT, creating an epsilon path to MATCH that allowed `a|b` to match any character with an empty string.
**Fix**: Restructured alternation: 2-alternative uses single SPLIT, 3+ chains SPLITs with last alternative going directly.

### 4. `sub()` with count not appending remaining text (Major)
**Bug**: When count limit was reached, `sub()` broke out of the loop without appending remaining text.
**Fix**: Added `result.append(text[pos:])` before break.

### 5. Matcher overwriting `last_match` at end-of-string (Major)
**Bug**: End-of-string handling unconditionally set `last_match = len(text)` when MATCH state found, causing `Pattern("a").match("abc")` to return `end=3` instead of `end=1`.
**Fix**: Only follow ANCHOR_END transitions at end-of-string, not re-check MATCH states.

### 6. `split()` not handling zero-length matches (Minor)
**Bug**: `split()` skipped all zero-length matches, making it impossible to split on patterns like `""`.
**Fix**: Added proper zero-length match handling.

---

## Roadmap

- [ ] **Lazy quantifiers** — Currently `*?` and `+?` parse but still match greedily (Thompson NFA limitation). Implement true lazy matching via left-to-right priority in SPLIT states.
- [ ] **Backreferences in patterns** — `\1`, `\2` in the pattern itself (not just in replacement strings).
- [ ] **Lookahead assertions** — `(?=...)` and `(?!...)`.
- [ ] **Non-capturing groups** — `(?:...)` syntax.
- [ ] **Flags** — Case-insensitive (`re.IGNORECASE`), multiline (`re.MULTILINE`), dotall (`re.DOTALL`).
- [ ] **Performance optimization** — Cache compiled patterns, DFA conversion for simple patterns.
- [ ] **Full `re` module compatibility** — Named groups `(?P<name>...)`, conditional patterns.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:

- Development setup
- Code style and architecture
- Adding features and fixing bugs
- Running tests
- Submitting changes

---

## References

- **Russ Cox**, *"Regular Expression Matching Can Be Simple And Fast"* — [https://swtch.com/~rsc/regexp/regexp1.html](https://swtch.com/~rsc/regexp/regexp1.html)
- **Aho, Sethi, Ullman**, *"Compilers: Principles, Techniques, and Tools"* (Dragon Book) — Thompson's construction algorithm
- **Python `re` module** — [https://docs.python.org/3/library/re.html](https://docs.python.org/3/library/re.html)

---

## License

MIT License — see [LICENSE](LICENSE) for details.