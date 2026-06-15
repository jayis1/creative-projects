#!/usr/bin/env python3
"""
Basic usage examples for the regex_engine module.

Demonstrates the core API: compile, match, search, findall, sub, split.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from regex_engine import compile, match, search, findall, sub, split


def main():
    print("=" * 60)
    print("regex_engine — Basic Usage Examples")
    print("=" * 60)

    # Compile a pattern
    print("\n--- Compile & Match ---")
    p = compile(r"\d+")
    m = p.match("123abc")
    print(f"  Pattern: {p!r}")
    print(f"  match('123abc') → {m!r}")
    print(f"  group(0) = '{m.group(0)}'")
    print(f"  span() = {m.span()}")

    # Module-level convenience functions
    print("\n--- Module-Level Functions ---")
    print(f"  match('hello', 'hello world') → {match('hello', 'hello world')!r}")
    print(f"  search('world', 'hello world') → {search('world', 'hello world')!r}")
    result_findall = findall(r"\d+", "a1b23c456")
    result_sub = sub(r"\d+", "X", "a1b23c456")
    print(f"  findall(r'\\d+', 'a1b23c456') → {result_findall}")
    print(f"  sub(r'\\d+', 'X', 'a1b23c456') → '{result_sub}'")
    print(f"  split(',', 'a,b,c') → {split(',', 'a,b,c')}")

    # Search
    print("\n--- Search ---")
    m = search(r"\d+", "abc123def456")
    print(f"  search(r'\\d+', 'abc123def456')")
    print(f"  → Match: '{m.group(0)}' at position {m.start}")

    # Findall
    print("\n--- Findall ---")
    words = findall(r"[a-z]+", "hello world foo bar")
    print(f"  findall(r'[a-z]+', 'hello world foo bar')")
    print(f"  → {words}")

    # Substitution
    print("\n--- Substitution ---")
    result = sub(r"\s+", "_", "hello   world  foo")
    print(f"  sub(r'\\s+', '_', 'hello   world  foo')")
    print(f"  → '{result}'")

    # Split
    print("\n--- Split ---")
    parts = split(r"\s+", "hello   world  foo")
    print(f"  split(r'\\s+', 'hello   world  foo')")
    print(f"  → {parts}")

    # Fullmatch
    print("\n--- Fullmatch ---")
    p = compile(r"\d{3}-\d{4}")
    m = p.fullmatch("555-1234")
    print(f"  fullmatch(r'\\d{{3}}-\\d{{4}}', '555-1234') → {m!r}")
    m = p.fullmatch("555-12345")
    print(f"  fullmatch(r'\\d{{3}}-\\d{{4}}', '555-12345') → {m!r}")

    # Finditer
    print("\n--- Finditer ---")
    p = compile(r"\d+")
    matches = p.finditer("a1b23c456")
    print(f"  finditer(r'\\d+', 'a1b23c456'):")
    for m in matches:
        print(f"    {m!r}")


if __name__ == "__main__":
    main()