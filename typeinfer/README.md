# typeinfer — Hindley-Milner Type Inference Engine

A from-scratch implementation of the Hindley-Milner (HM) type inference
algorithm (also known as Algorithm W) for a small purely-functional lambda
calculus.  The engine infers principal types for expressions containing
lambdas, let-bindings, conditionals, integer/boolean literals, primitives,
and let-polymorphism — all without any external dependencies.

## Language

The mini-language supports:

| Construct | Syntax | Example |
|-----------|--------|---------|
| Integer literal | `42` | `42` |
| Boolean literal | `true` / `false` | `true` |
| Variable | `x` | `x` |
| Lambda | `λx. body` or `\x. body` | `\x. x` |
| Application | `f x` | `(\x. x) 42` |
| Let | `let x = e1 in e2` | `let id = \x. x in id 5` |
| If | `if c then a else b` | `if true then 1 else 2` |
| Let-rec | `let rec f = \x. ... in ...` | `let rec fac = \n. if n then 1 else n * fac (n - 1) in ...` |

## How it works

1. **Lexing** — a small tokenizer splits input into tokens (keywords,
   identifiers, integers, operators).
2. **Parsing** — a recursive-descent parser builds an AST of
   `Expr` nodes.
3. **Unification** — a Robinson-style unification algorithm over type
   variables, with the occurs-check to prevent infinite types.
4. **Generalisation** — let-bound variables are generalised to
   polymorphic types (∀-quantification) at `let` sites.
5. **Instantiation** — polymorphic types are instantiated with fresh
   type variables at use sites.
6. **Inference** — Algorithm W walks the AST, produces type equations,
   and solves them via unification, yielding the principal (most general)
   type of the expression.

## Usage

```python
from typeinfer import infer, parse, type_to_string

# Identity function
t = infer("\\x. x")
print(type_to_string(t))  # a -> a

# Let-polymorphism
t = infer("let id = \\x. x in (id 1, id true) ... ")
```

### CLI

```bash
python -m typeinfer "\x. x"
python -m typeinfer "let id = \x. x in id 42"
```