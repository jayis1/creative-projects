#!/usr/bin/env python3
"""Debug the NFA structure."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from regex_engine.parser import Parser
from regex_engine.compiler import Compiler
from regex_engine.nfa import State

def walk(s, depth=0, visited=None):
    if visited is None:
        visited = set()
    if s is None or id(s) in visited:
        return
    visited.add(id(s))
    kind_str = {State.MATCH: 'MATCH', State.SPLIT: 'SPLIT', State.CHAR: 'CHAR'}
    indent = '  ' * depth
    print(f"{indent}{s} kind={kind_str.get(s.kind, '?')}")
    if s.kind == State.CHAR:
        print(f"{indent}  out1 (predicate): {'callable' if callable(s.out1) else s.out1}")
        print(f"{indent}  out2: {s.out2}")
    elif s.kind == State.SPLIT:
        print(f"{indent}  out1: {s.out1}")
        print(f"{indent}  out2: {s.out2}")
    elif s.kind == State.MATCH:
        print(f"{indent}  (accepting)")
    if s.out1 is not None and s.kind != State.CHAR:
        walk(s.out1, depth+1, visited)
    if s.out2 is not None:
        walk(s.out2, depth+1, visited)

# Test simple literal 'a'
print("=== Pattern: 'a' ===")
ast = Parser('a').parse()
compiler = Compiler()
start = compiler.compile(ast)
walk(start)

# Test 'a*'
print("\n=== Pattern: 'a*' ===")
ast = Parser('a*').parse()
start = compiler.compile(ast)
walk(start)

# Test 'a+'
print("\n=== Pattern: 'a+' ===")
ast = Parser('a+').parse()
start = compiler.compile(ast)
walk(start)

# Test 'ab'
print("\n=== Pattern: 'ab' ===")
ast = Parser('ab').parse()
start = compiler.compile(ast)
walk(start)

# Test 'a|b'
print("\n=== Pattern: 'a|b' ===")
ast = Parser('a|b').parse()
start = compiler.compile(ast)
walk(start)