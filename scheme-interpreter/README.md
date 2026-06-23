# Scheme Interpreter

A from-scratch Scheme interpreter in pure Python (no dependencies) implementing a substantial subset of R5RS Scheme, including tail-call optimization, first-class continuations, and a complete macro system.

## Features

- **Lexer**: Handles numbers (int/float/rational), strings, symbols, booleans, characters, comments
- **Parser**: Recursive-descent parser producing AST as nested Python data structures
- **Special Forms**: `lambda`, `define`, `if`, `cond`, `let`, `let*`, `letrec`, `begin`, `quote`, `quasiquote`, `set!`, `and`, `or`, `when`, `unless`, `case`, `do`, `delay`/`force`, `multiple-values`/`call-with-values`
- **Tail-Call Optimization**: Trampoline-based TCO prevents stack overflow on deep recursion
- **First-Class Continuations**: Full `call/cc` support via continuation-passing style
- **Macros**: `define-syntax` with `syntax-rules` pattern matching and hygienic renaming
- **Closures & Lexical Scoping**: Proper lexical scoping with environment chains
- **Garbage Collection**: Relies on Python's GC; supports weak references via `make-weak-vector`
- **Standard Library**: 100+ built-in procedures (arithmetic, list ops, string ops, I/O, predicates)
- **REPL & CLI**: Interactive REPL + script execution with argparse CLI
- **Error Handling**: Rich error messages with source location tracking

## Installation

```bash
cd scheme-interpreter
pip install -e .
```

## Usage

### REPL
```bash
python3 -m scheme_interpreter.repl
```

### Run a script
```bash
python3 -m scheme_interpreter.cli script.scm
```

### Examples

```scheme
;; Basic arithmetic
> (+ 1 2 3)
6

;; Define functions
> (define (factorial n)
    (if (= n 0) 1 (* n (factorial (- n 1)))))
> (factorial 10)
3628800

;; Tail-recursive (no stack overflow)
> (define (loop n acc)
    (if (= n 0) acc (loop (- n 1) (+ acc 1))))
> (loop 100000 0)
100000

;; Closures
> (define (make-counter)
    (let ((count 0))
      (lambda () (set! count (+ count 1)) count)))
> (define c (make-counter))
> (c) (c) (c)
1
2
3

;; call/cc
> (+ 1 (call/cc (lambda (k) (+ 2 (k 10)))))
11

;; Macros
> (define-syntax swap!
    (syntax-rules ()
      ((swap! a b)
       (let ((tmp a)) (set! a b) (set! b tmp)))))
```