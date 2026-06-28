# typeinfer — Hindley-Milner Type Inference Engine

A from-scratch implementation of the Hindley-Milner (HM) type inference
algorithm (Algorithm W) for a small purely-functional lambda calculus.  The
engine infers principal types for expressions containing lambdas,
let-bindings (with let-polymorphism), conditionals, integer/boolean
literals, primitive operators, tuples, algebraic data type constructors,
and recursive definitions — all without any external dependencies.

## Language

The mini-language supports:

| Construct | Syntax | Example |
|-----------|--------|---------|
| Integer literal | `42` | `42` |
| Boolean literal | `true` / `false` | `true` |
| Variable | `x` | `x` |
| Lambda | `λx. body` or `\x. body` | `\x. x` |
| Multi-arg lambda | `\x y z. body` (sugar) | `\x y. x` |
| Application | `f x` | `(\x. x) 42` |
| Let | `let x = e1 in e2` | `let id = \x. x in id 5` |
| Let-rec | `let rec f = \x. ... in ...` | `let rec f = \n. if n then 1 else f n in f` |
| If | `if c then a else b` | `if true then 1 else 2` |
| Tuple | `(a, b, ...)` | `(1, true)` |
| Unit | `()` | `()` |
| Operators | `+ - * / < > <= >= == != && \|\|` | `1 + 2 * 3` |

### Operator precedence (highest binds tightest)

| Level | Operators | Associativity |
|-------|-----------|---------------|
| 1 | `&&` `\|\|` | right |
| 2 | `==` `!=` `<` `>` `<=` `>=` | left |
| 3 | `+` `-` | left |
| 4 | `*` `/` | left |
| 5 | application | left |

Infix operators desugar to applications of a variable named by the operator
symbol, e.g. `a + b` ⟶ `((+) a) b`.

## How it works

1. **Lexing** — a small tokenizer splits input into tokens (keywords,
   identifiers, integers, operators, punctuation).  Multi-character
   operators (`==`, `<=`, `&&`, …) are matched longest-first.
2. **Parsing** — a recursive-descent parser with operator-precedence
   climbing builds an AST of `Expr` nodes.  Multi-argument lambdas and
   tuples are desugared into the core forms.
3. **Unification** — a Robinson-style unification algorithm over type
   variables, with the **occurs-check** to prevent infinite types such as
   `a = a -> a`.
4. **Generalisation** — let-bound variables are generalised to
   polymorphic types (∀-quantification) at `let` sites.  Only variables
   not free in the surrounding environment are generalised.
5. **Instantiation** — polymorphic types are instantiated with fresh
   type variables at use sites, enabling let-polymorphism.
6. **Inference** — Algorithm W walks the AST, produces type equations,
   and solves them via unification, yielding the principal (most general)
   type of the expression.

## Usage

### Python API

```python
from typeinfer import infer, type_to_string

# Identity function — most general type
print(type_to_string(infer(r"\x. x")))            # a -> a

# Let-polymorphism: id can be used at Int and Bool in the same scope
print(type_to_string(infer(r"let id = \x. x in (id 1, id true)")))
# Tuple<Int, Bool>

# With built-in primitives
print(type_to_string(infer(r"\x. x + 1", use_builtins=True)))   # Int -> Int
print(type_to_string(infer(r"1 + 2 * 3", use_builtins=True)))   # Int
print(type_to_string(infer(r"\x. x == x", use_builtins=True)))  # a -> Bool

# Algebraic data types (List / Maybe)
print(type_to_string(infer(r"Cons 1 Nil", use_builtins=True)))  # List<Int>
print(type_to_string(infer(r"Just 5", use_builtins=True)))      # Maybe<Int>

# Inference trace
from typeinfer import infer_with_trace
t, steps = infer_with_trace(r"let id = \x. x in id 42")
for s in steps:
    print(s)
print("=>", type_to_string(t))
```

### CLI

```bash
# Basic inference
python -m typeinfer "\x. x"                     # a -> a
python -m typeinfer "let id = \x. x in id 42"   # Int

# With built-in primitives (+, -, *, /, <, >, ==, ..., List, Maybe)
python -m typeinfer --builtins "\x. x + 1"      # Int -> Int
python -m typeinfer -b "1 + 2 * 3"              # Int
python -m typeinfer -b "Cons 1 Nil"             # List<Int>

# Step-by-step inference trace
python -m typeinfer --explain "let id = \x. x in id 42"

# Show the parsed AST
python -m typeinfer --ast "\x. x + 1"

# Interactive REPL
python -m typeinfer --repl

# Version
python -m typeinfer --version
```

### REPL

The REPL supports a few commands:

| Command | Action |
|---------|--------|
| `:t <expr>` | infer and print the type |
| `:e <expr>` | infer and print the trace + type |
| `:b` | toggle built-in primitives on/off |
| `:q` | quit |

## Built-in environment

When `--builtins` is passed (or `use_builtins=True` in Python), the
following identifiers are available:

| Category | Names | Type |
|----------|-------|------|
| Arithmetic | `+ - * /` | `Int -> Int -> Int` |
| Comparison | `< > <= >=` | `Int -> Int -> Bool` |
| Equality | `== !=` | `∀a. a -> a -> Bool` |
| Boolean | `&& \|\| not` | `Bool -> Bool -> Bool` / `Bool -> Bool` |
| Negation | `neg` | `Int -> Int` |
| List ADT | `Nil` / `Cons` | `∀a. List<a>` / `∀a. a -> List<a> -> List<a>` |
| Maybe ADT | `Nothing` / `Just` | `∀a. Maybe<a>` / `∀a. a -> Maybe<a>` |

## Project layout

```
typeinfer/
├── typeinfer/
│   ├── __init__.py      # public API re-exports
│   ├── __main__.py      # CLI + REPL
│   ├── types.py         # Type representations (TVar, TCon, TFun, Scheme)
│   ├── lexer.py         # tokenizer
│   ├── parser.py        # recursive-descent parser + AST nodes
│   ├── unify.py         # Robinson unification + substitutions
│   ├── inference.py     # Algorithm W
│   └── primitives.py    # built-in typing environments
├── tests/
│   └── test_*.py
├── pyproject.toml
└── README.md
```

## Error reporting

The engine detects and reports:

- **Lexical errors** — invalid characters.
- **Syntax errors** — unexpected / trailing tokens, missing keywords.
- **Unbound variables** — use of an identifier not in scope.
- **Type mismatches** — failure to unify two types (e.g. `1 + true`).
- **Occurs-check failures** — infinite types such as `\x. x x`.
- **Branch mismatches** — `if c then a else b` where `a` and `b` have
  different types, or `c` is not `Bool`.

## License

MIT.