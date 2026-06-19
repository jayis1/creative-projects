# MiniLang Architecture

This document explains the internal architecture of the MiniLang compiler
and virtual machine.

## Pipeline Overview

```
Source code (string)
    │
    ▼
┌──────────┐
│  Lexer   │  Tokenizes source → list of Token(kind, lexeme, line, col)
│          │  Handles: comments, strings, numbers, identifiers, operators
└────┬─────┘
     │ list[Token]
     ▼
┌──────────┐
│  Parser  │  Recursive-descent / Pratt parser → AST (Program)
│          │  Grammar: declarations, statements, expressions with precedence
└────┬─────┘
     │ Program (tuple of Stmt)
     ▼
┌──────────────┐
│ Type Checker │  Bidirectional inference → TypeChecker (expr_types, functions)
│              │  Checks: types, scopes, const-ness, loop context, returns
└────┬─────────┘
     │ TypeChecker metadata (function signatures, local slot allocation)
     ▼
┌──────────────┐
│  Optimizer   │  (Optional) AST-level: constant folding, dead-code elimination
│              │  Bytecode-level: jump threading
└────┬─────────┘
     │ Optimized Program AST
     ▼
┌──────────┐
│ Compiler │  AST → bytecode (Chunk per function + main)
│          │  Jump-and-patch for forward jumps, scope-based local slots
└────┬─────┘
     │ CompiledProgram (main chunk, function chunks, string pool)
     ▼
┌──────────┐
│   VM     │  Stack-based interpreter with mark-and-sweep GC
│          │  Call frames, step limit, call depth limit
└──────────┘
```

## Lexer

The lexer is a hand-written scanner (`lexer.py`) that produces a list of
`Token` objects. Each token carries its `kind` (a `TokenKind` enum), the
`lexeme` string, and `line`/`col` for error reporting.

Key design decisions:
- **Multi-char operators**: Tried longest-first (`==` before `=`).
- **Keywords**: A static `KEYWORDS` dict maps lexemes to `TokenKind`.
- **String escapes**: A lookup table handles `\n`, `\t`, `\r`, `\\`, `\"`, `\0`.

## Parser

The parser (`parser.py`) is a recursive-descent / Pratt-parser hybrid:
- **Declarations** (functions, variables) are parsed top-down.
- **Expressions** use Pratt precedence climbing (assignment → logic_or →
  logic_and → equality → comparison → addition → multiplication → unary →
  postfix → primary).

The grammar is defined in the module docstring. Notable features:
- `elif` keyword support (desugared to nested `if` in `else` branch).
- `else if` chains (same desugaring).
- Array literals and indexing.
- Function calls with arguments.

## AST

All AST nodes (`ast.py`) are **frozen dataclasses** with `slots=True`:
- Frozen = immutable, hashable (the optimizer compares subtrees for equality).
- Slots = memory-efficient, fast attribute access.

Node types:
- **Expressions**: `IntLit`, `StringLit`, `BoolLit`, `NilLit`, `ArrayLit`,
  `Ident`, `BinOp`, `UnaryOp`, `IndexExpr`, `CallExpr`, `Assign`, `IndexAssign`
- **Statements**: `VarDecl`, `ExprStmt`, `Block`, `IfStmt`, `WhileStmt`,
  `ForStmt`, `ReturnStmt`, `BreakStmt`, `ContinueStmt`, `FuncDecl`
- **Types**: `IntType`, `StringType`, `BoolType`, `UnitType`, `ArrayType`,
  `FuncType`

## Type Checker

The type checker (`types.py`) performs bidirectional type inference:
- Every expression is assigned a type stored in `expr_types: dict[int, TypeNode]`.
- Scopes track variable → (slot, type) mappings for local slot allocation.
- Functions are registered in a first pass (allows forward references).
- Break/continue are checked to be inside loops.
- Return types are checked against function declarations.
- Non-unit functions must return on all paths.

## Optimizer

The optimizer (`optimizer.py`) runs two AST-level passes to a fixed point:
1. **Constant folding**: Evaluates literal expressions at compile time
   (e.g., `2 + 3` → `5`, `"a" + "b"` → `"ab"`).
2. **Dead-code elimination**: Removes statements after unconditional
   `return`/`break`/`continue` in the same block.

Plus one bytecode-level pass:
3. **Jump threading**: Collapses `JUMP → JUMP` chains.

Integer division in the optimizer uses truncate-toward-zero semantics to
match the VM.

## Compiler

The compiler (`compiler.py`) walks the type-checked AST and emits bytecode:
- **One chunk per function** plus a `main` chunk for top-level code.
- **Jump-and-patch**: Forward jumps emit a placeholder operand, patched
  once the target PC is known.
- **Scope frames**: Variable names → local slots, with a shared counter
  across nested scopes in a function.
- **Loop break/continue**: A stack of `(break_targets, continue_targets)`
  ensures nested loops correctly target the right loop level.
- **String pool**: Each chunk has a string pool; merged into a global pool
  after compilation with index remapping.

## Bytecode

The instruction set (`bytecode.py`) has 34+ opcodes:

| Category      | Opcodes                                                    |
|---------------|------------------------------------------------------------|
| Literals      | `PUSH_INT`, `PUSH_STR`, `PUSH_BOOL`, `PUSH_NIL`          |
| Variables     | `LOAD_LOCAL`, `STORE_LOCAL`, `POP`                         |
| Arrays        | `NEW_ARRAY`, `INDEX_GET`, `INDEX_SET`                      |
| Arithmetic    | `ADD`, `SUB`, `MUL`, `DIV`, `MOD`, `NEG`                   |
| Comparison    | `EQ`, `NEQ`, `LT`, `LE`, `GT`, `GE`                       |
| Logic         | `NOT`, `AND`, `OR` (compiled as short-circuit jumps)      |
| Control flow  | `JUMP`, `JUMP_IF_FALSE`, `JUMP_IF_TRUE`, `CALL`, `RETURN`  |
| Builtins/Other| `PRINT`, `HALT`, `TRACE`                                  |

The `Disassembler` pretty-prints bytecode with annotations for string
literals, jump targets, and local slots.

## VM

The VM (`vm.py`) is a stack-based interpreter:
- **Call frames**: Each function call creates a `Frame` with its own operand
  stack, locals array, and PC. The `caller` chain forms the call stack.
- **Dispatch**: A single `while True` loop with `if/elif` chains on opcode.
- **GC**: Mark-and-sweep garbage collector. Marks from all live frames'
  roots (locals + stacks), sweeps unreachable heap objects. Runs when
  heap size exceeds `_next_gc` (grows exponentially).
- **Step limit**: Prevents infinite loops (default 10M steps).
- **Call depth limit**: Prevents Python stack overflow from deep recursion
  (default 512).
- **Integer division**: Truncates toward zero (C/Java/Rust semantics, not
  Python's floor division).

## Value Representation

Runtime values (`value.py`) use a tagged-union pattern:
- `Value(tag: ValueTag, payload: object)` — the tag is a small int enum,
  the payload is the actual data.
- Tags: `INT`, `BOOL`, `STRING`, `NIL`, `ARRAY`, `CLOSURE`, `BOUND`.
- Heap-allocated values (arrays, closures) inherit from `Object` for GC
  tracking.
- `Value.display()` provides human-readable string conversion.