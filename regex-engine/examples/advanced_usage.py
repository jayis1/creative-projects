#!/usr/bin/env python3
"""
Advanced usage examples for the regex_engine module.

Demonstrates advanced features: capture groups, anchors, quantifiers,
character classes, backreferences in sub(), and performance.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from regex_engine import Pattern, compile


def main():
    print("=" * 60)
    print("regex_engine — Advanced Usage Examples")
    print("=" * 60)

    # Capture groups
    print("\n--- Capture Groups ---")
    p = compile(r"(\w+)@(\w+)\.(\w+)")
    m = p.search("Contact user@example.com for info")
    print(f"  Pattern: r'(\\w+)@(\\w+)\\.(\\w+)'")
    print(f"  Text: 'Contact user@example.com for info'")
    print(f"  Full match: '{m.group(0)}'")
    print(f"  Groups: {m.groups()}")

    # Anchors
    print("\n--- Anchors ---")
    p = compile(r"^hello")
    m = p.match("hello world")
    print(f"  ^hello on 'hello world' → '{m.group(0)}'")

    p = compile(r"world$")
    m = p.search("hello world")
    print(f"  world$ on 'hello world' → '{m.group(0)}'")

    p = compile(r"^world$")
    m = p.fullmatch("world")
    print(f"  ^world$ on 'world' (fullmatch) → matched={m is not None}")

    # Complex quantifiers
    print("\n--- Quantifiers ---")
    # {n} exact
    p = compile(r"a{3}")
    print(f"  r'a{{3}}' matches 'aaa': {p.match('aaa') is not None}")
    print(f"  r'a{{3}}' matches 'aa': {p.match('aa') is None}")

    # {n,m} range
    p = compile(r"a{2,4}")
    m = p.match("aaaa")
    print(f"  r'a{{2,4}}' on 'aaaa': '{m.group(0)}'")

    # {n,} unbounded
    p = compile(r"a{2,}")
    m = p.match("aaaaa")
    print(f"  r'a{{2,}}' on 'aaaaa': '{m.group(0)}'")

    # Character classes
    print("\n--- Character Classes ---")
    p = compile(r"[aeiou]+")
    m = p.search("hello")
    print(f"  [aeiou]+ in 'hello': '{m.group(0)}'")

    p = compile(r"[A-Z][a-z]+")
    m = p.search("Hello World")
    print(f"  [A-Z][a-z]+ in 'Hello World': '{m.group(0)}'")

    p = compile(r"[^0-9]+")
    m = p.search("abc123def")
    print(f"  [^0-9]+ in 'abc123def': '{m.group(0)}'")

    # Shorthand classes
    print("\n--- Shorthand Classes ---")
    p = compile(r"\d+")
    m = p.search("abc123def")
    print(f"  \\d+ in 'abc123def': '{m.group(0)}'")

    p = compile(r"\w+")
    m = p.search("hello_world!")
    print(f"  \\w+ in 'hello_world!': '{m.group(0)}'")

    p = compile(r"\s+")
    m = p.search("hello   world")
    print(f"  \\s+ in 'hello   world': matched={m is not None}")

    # Substitution
    print("\n--- Substitution ---")
    p = compile(r"\d+")
    result = p.sub("NUM", "a1b23c456")
    print(f"  sub(r'\\d+', 'NUM', 'a1b23c456') → '{result}'")

    # With count limit
    result = p.sub("X", "a1b2c3d", count=2)
    print(f"  sub(r'\\d+', 'X', 'a1b2c3d', count=2) → '{result}'")

    # subn
    result, count = p.subn("X", "a1b2c3")
    print(f"  subn(r'\\d+', 'X', 'a1b2c3') → ('{result}', {count})")

    # Split with regex
    print("\n--- Split ---")
    p = compile(r"\s+")
    parts = p.split("hello   world  foo")
    print(f"  split(r'\\s+', 'hello   world  foo') → {parts}")

    p = compile(r",")
    parts = p.split("a,b,c,d", maxsplit=2)
    print(f"  split(',', 'a,b,c,d', maxsplit=2) → {parts}")

    # Fullmatch
    print("\n--- Fullmatch ---")
    p = compile(r"\d{3}-\d{4}")
    print(f"  fullmatch(r'\\d{{3}}-\\d{{4}}', '555-1234'): {p.fullmatch('555-1234') is not None}")
    print(f"  fullmatch(r'\\d{{3}}-\\d{{4}}', '555-12345'): {p.fullmatch('555-12345') is None}")

    # Email-like pattern
    print("\n--- Email Pattern ---")
    p = compile(r"[a-zA-Z0-9.]+@[a-zA-Z0-9.]+\.[a-zA-Z]{2,}")
    m = p.search("Send email to user.name@example.co.uk please")
    print(f"  Email found: '{m.group(0)}'")

    # Performance: pathological pattern
    print("\n--- Performance ---")
    import time
    p = compile(r"(a*)*b")  # Pathological for backtracking engines
    start = time.time()
    result = p.match("a" * 25)
    elapsed = time.time() - start
    print(f"  (a*)*b on 'aaa...a' (25 chars): {elapsed:.4f}s (linear time guaranteed)")

    p = compile(r"a*")
    start = time.time()
    m = p.match("a" * 10000)
    elapsed = time.time() - start
    print(f"  a* on 'aaa...a' (10000 chars): {elapsed:.4f}s")


if __name__ == "__main__":
    main()