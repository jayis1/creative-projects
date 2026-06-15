# regex-engine

A regular expression engine built from scratch using **Thompson's NFA construction**, implementing the classic algorithm described in Russ Cox's *"Regular Expression Matching Can Be Simple And Fast"*.

## How It Works

The engine works in three stages:

1. **Parsing** — A recursive descent parser converts a regex pattern string into an Abstract Syntax Tree (AST), handling operator precedence, character classes, escape sequences, and quantifiers.

2. **Compilation** — Thompson's construction converts the AST into an NFA (Nondeterministic Finite Automaton) with five state types:
   - **CHAR**: transitions on a character that satisfies a predicate (`out1` = predicate, `out2` = target state)
   - **SPLIT**: two epsilon transitions (`out1`, `out2`) taken simultaneously
   - **MATCH**: accepting state (pattern matched!)
   - **ANCHOR_START**: epsilon transition that only succeeds at position 0 or after newline (`^`)
   - **ANCHOR_END**: epsilon transition that only succeeds at end of string or before newline (`$`)

   The key property: the NFA has **O(m)** states where m is the pattern length, and each AST node compiles to a constant number of states.

3. **Simulation** — Thompson's two-list algorithm simulates the NFA on input text in **O(nm)** time (n = text length, m = pattern length), with no backtracking. This guarantees linear-time matching even for pathological patterns that cause exponential backtracking in other engines.

## Supported Features

| Feature | Syntax | Example |
|---------|--------|---------|
| Literals | `abc` | `cat` matches "cat" |
| Wildcard | `.` | `a.c` matches "abc", "arc" |
| Alternation | `\|` | `cat\|dog` matches "cat" or "dog" |
| Grouping | `(...)` | `(ab)+` matches "ab", "abab" |
| Kleene star | `*` | `a*` matches "", "a", "aaa" |
| Plus | `+` | `a+` matches "a", "aaa" |
| Optional | `?` | `a?` matches "", "a" |
| Brace quantifiers | `{n}`, `{n,m}`, `{n,}` | `a{2,4}` matches "aa"–"aaaa" |
| Character classes | `[abc]`, `[a-z]`, `[^0-9]` | `[a-z]+` matches lowercase words |
| Shorthand classes | `\d`, `\w`, `\s`, `\D`, `\W`, `\S` | `\d+` matches "123" |
| Escapes | `\.`, `\\`, `\n`, `\t` | `a\.b` matches "a.b" |
| Anchors | `^`, `$` | `^hello` matches at start |
| Non-greedy | `*?`, `+?`, `??` | `a*?` prefers shortest match |

## API

The API mirrors Python's `re` module:

```python
from regex_engine import compile, match, search, findall, sub, split

# Pattern object
p = compile(r'\d+')
m = p.match('123abc')
print(m.group(0))  # '123'

# Module-level convenience functions
m = search(r'\d+', 'abc123def')
print(m.group(0))  # '123'

# Findall
print(findall(r'[a-z]+', 'hello world'))  # ['hello', 'world']

# Substitution
print(sub(r'\d+', 'X', 'a1b23c'))  # 'aXbXc'

# Split
print(split(r',', 'a,b,c'))  # ['a', 'b', 'c']
```

### Pattern Methods

| Method | Description |
|--------|-------------|
| `match(text)` | Match at start of text |
| `fullmatch(text)` | Match entire text |
| `search(text, pos)` | Search for first match |
| `findall(text)` | All non-overlapping matches |
| `finditer(text)` | All matches as Match objects |
| `sub(repl, text, count)` | Replace matches |
| `subn(repl, text, count)` | Replace matches, return (string, count) |
| `split(text, maxsplit)` | Split by pattern |

### Match Object

| Attribute/Method | Description |
|-----------------|-------------|
| `group(n)` | Matched group (0 = entire match) |
| `groups()` | All captured groups as tuple |
| `span(n)` | (start, end) of group n |
| `start`, `end` | Match boundaries |
| `matched` | Whether match succeeded |
| `__bool__` | Truthy if matched |

### Command Line

```bash
# Match
python -m regex_engine '\d+' 'hello 123 world'

# Find all
python -m regex_engine --findall '[a-z]+' 'hello world'

# Substitute
python -m regex_engine --sub '\s+' '_' 'hello   world'

# Split
python -m regex_engine --split ',' 'a,b,c'
```

## Architecture

```
regex_engine/
├── __init__.py    # Module-level API (match, search, findall, sub, split)
├── parser.py      # Recursive descent parser → AST
├── compiler.py    # Thompson's construction: AST → NFA
├── nfa.py         # NFA state and fragment definitions (5 state types)
├── matcher.py     # Thompson's two-list NFA simulation
├── pattern.py     # High-level Pattern interface (like re.Pattern)
└── cli.py         # Command-line interface
```

## Performance Guarantee

Unlike backtracking regex engines (which can take O(2^n) time on pathological inputs), this engine guarantees **O(nm)** matching time** where n is the text length and m is the pattern length. This is because the Thompson simulation tracks a set of states (at most m states) and processes each character exactly once.

## Running Tests

```bash
python3 tests.py
```

## References

- Russ Cox, *"Regular Expression Matching Can Be Simple And Fast"* (https://swtch.com/~rsc/regexp/regexp1.html)
- Aho, Sethi, Ullman, *"Compilers: Principles, Techniques, and Tools"* (Dragon Book)