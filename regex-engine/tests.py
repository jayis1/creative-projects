#!/usr/bin/env python3
"""
Comprehensive tests for the regex engine — covering all features and edge cases.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from regex_engine.parser import Parser, ParseError
from regex_engine.compiler import Compiler
from regex_engine.nfa import State
from regex_engine.matcher import Matcher, Match
from regex_engine.pattern import Pattern
import regex_engine as re


total = 0
passed = 0

def check(name, condition, msg=""):
    global total, passed
    total += 1
    if condition:
        passed += 1
        print(f"  ✓ {name}")
    else:
        print(f"  ✗ {name}: {msg}")


# ============================================================
# Basic literal and concatenation
# ============================================================
check("literal match", Pattern("a").match("a").group(0) == "a")
check("literal no match", Pattern("a").match("b") is None)
check("concat match", Pattern("ab").match("ab").group(0) == "ab")
check("concat no match", Pattern("ab").match("ac") is None)
check("longer concat", Pattern("hello").match("hello world").group(0) == "hello")

# ============================================================
# Alternation
# ============================================================
check("alt first", Pattern("a|b").match("a").group(0) == "a")
check("alt second", Pattern("a|b").match("b").group(0) == "b")
check("alt no match", Pattern("a|b").match("c") is None)
check("alt three", Pattern("a|b|c").match("b").group(0) == "b")
check("alt longer", Pattern("cat|dog").match("dog").group(0) == "dog")
check("alt three words", Pattern("cat|dog|bird").match("bird").group(0) == "bird")

# ============================================================
# Quantifiers
# ============================================================
check("star zero", Pattern("a*").match("").group(0) == "")
check("star one", Pattern("a*").match("a").group(0) == "a")
check("star many", Pattern("a*").match("aaa").group(0) == "aaa")
check("plus zero", Pattern("a+").match("") is None)
check("plus one", Pattern("a+").match("a").group(0) == "a")
check("plus many", Pattern("a+").match("aaa").group(0) == "aaa")
check("question zero", Pattern("a?").match("").group(0) == "")
check("question one", Pattern("a?").match("a").group(0) == "a")

# ============================================================
# Dot
# ============================================================
check("dot match", Pattern(".").match("a").group(0) == "a")
check("dot no newline", Pattern(".").match("\n") is None)
check("dot no empty", Pattern(".").match("") is None)
check("dot star", Pattern(".*").match("hello world").group(0) == "hello world")

# ============================================================
# Character classes
# ============================================================
check("charclass match", Pattern("[abc]").match("b").group(0) == "b")
check("charclass no match", Pattern("[abc]").match("d") is None)
check("charclass range", Pattern("[a-z]").match("m").group(0) == "m")
check("charclass range no match", Pattern("[a-z]").match("M") is None)
check("charclass negated", Pattern("[^0-9]").match("a") is not None)
check("charclass negated no match", Pattern("[^0-9]").match("5") is None)
check("charclass multiple ranges", Pattern("[a-zA-Z]").match("Z") is not None)
check("charclass dash", Pattern("[-a]").match("-") is not None)

# ============================================================
# Shorthand classes
# ============================================================
check("\\d match", Pattern("\\d").match("5").group(0) == "5")
check("\\d no match", Pattern("\\d").match("a") is None)
check("\\w match", Pattern("\\w").match("a") is not None)
check("\\w underscore", Pattern("\\w").match("_") is not None)
check("\\s match", Pattern("\\s").match(" ") is not None)
check("\\D match", Pattern("\\D").match("a") is not None)
check("\\W match", Pattern("\\W").match("!") is not None)
check("\\S match", Pattern("\\S").match("a") is not None)

# ============================================================
# Groups
# ============================================================
check("group match", Pattern("(ab)").match("ab").group(0) == "ab")
check("group with alt", Pattern("(a|b)*c").match("ababc").group(0) == "ababc")
check("group star", Pattern("(ab)+").match("ababab").group(0) == "ababab")
check("nested groups", Pattern("((a)(b))").match("ab").group(0) == "ab")

# ============================================================
# Brace quantifiers
# ============================================================
check("brace exact", Pattern("a{3}").match("aaa").group(0) == "aaa")
check("brace exact no match", Pattern("a{3}").match("aa") is None)
check("brace range", Pattern("a{2,4}").match("aaa").group(0) == "aaa")
check("brace unbounded", Pattern("a{2,}").match("aaaaa").group(0) == "aaaaa")
check("brace exact 1", Pattern("a{1}").match("a").group(0) == "a")

# ============================================================
# Anchors
# ============================================================
check("^ at start", Pattern("^hello").match("hello world").group(0) == "hello")
check("^ not at start", Pattern("^hello").match("say hello") is None)
check("$ at end", Pattern("hello$").search("hello").group(0) == "hello")
check("$ not at end", Pattern("hello$").match("hello world") is None)
check("^$ together", Pattern("^hello$").match("hello") is not None)
check("^$ empty", Pattern("^$").match("") is not None)

# ============================================================
# Search
# ============================================================
check("search middle", Pattern("bc").search("abcd").group(0) == "bc")
check("search start", Pattern("ab").search("abcd").group(0) == "ab")
check("search not found", Pattern("xyz").search("abcd") is None)
check("search pattern", Pattern("\\d+").search("abc123def").group(0) == "123")

# ============================================================
# Findall
# ============================================================
check("findall words", Pattern("[a-z]+").findall("hello world foo") == ["hello", "world", "foo"])
check("findall digits", Pattern("\\d+").findall("a1b23c456") == ["1", "23", "456"])
check("findall single chars", Pattern("[aeiou]").findall("hello") == ["e", "o"])

# ============================================================
# Sub
# ============================================================
check("sub basic", Pattern("\\d+").sub("NUM", "a1b23c456") == "aNUMbNUMcNUM")
check("sub count", Pattern("\\d+").sub("NUM", "a1b23c456", count=2) == "aNUMbNUMc456")
check("sub spaces", Pattern("\\s+").sub("_", "hello   world") == "hello_world")
check("subn", Pattern("\\d+").subn("X", "a1b2c3") == ("aXbXcX", 3))

# ============================================================
# Split
# ============================================================
check("split basic", Pattern(",").split("a,b,c") == ["a", "b", "c"])
check("split regex", Pattern("\\s+").split("hello   world  foo") == ["hello", "world", "foo"])
check("split maxsplit", Pattern(",").split("a,b,c,d", maxsplit=2) == ["a", "b", "c,d"])

# ============================================================
# Fullmatch
# ============================================================
check("fullmatch yes", Pattern("abc").fullmatch("abc") is not None)
check("fullmatch no", Pattern("abc").fullmatch("abcd") is None)
check("fullmatch partial", Pattern("abc").fullmatch("ab") is None)

# ============================================================
# Finditer
# ============================================================
matches = Pattern("[a-z]+").finditer("hello world foo")
check("finditer count", len(matches) == 3)
check("finditer values", [m.group(0) for m in matches] == ["hello", "world", "foo"])

# ============================================================
# Edge cases
# ============================================================
check("empty pattern", Pattern("").match("") is not None)
check("empty pattern in string", Pattern("").match("abc") is not None)
check("escaped dot", Pattern("\\.").match(".").group(0) == ".")
check("escaped dot no match", Pattern("\\.").match("a") is None)
check("escaped star", Pattern("\\*").match("*") is not None)
check("complex regex 1", Pattern("(\\d+)-(\\d+)").search("123-456") is not None)
check("complex regex 2", Pattern("[a-z]+@[a-z]+\\.[a-z]+").match("user@example.com") is not None)
check("repeated quantifier", Pattern("a{2}b{3}").match("aabbb") is not None)

# ============================================================
# Bug fixes: previously found and fixed bugs
# ============================================================

# Bug: Pattern("a").match("abc") was returning end=3 instead of end=1
check("literal match truncation", Pattern("a").match("abc").group(0) == "a")
check("literal match end pos", Pattern("a").match("abc").end == 1)

# Bug: alternation a|b|c matched 'c' with empty string
check("alt three all branches", Pattern("a|b|c").match("c").group(0) == "c")

# Bug: shorthand classes \d, \w, \s didn't work (predicate was broken)
check("\\d predicate fixed", Pattern("\\d+").match("123").group(0) == "123")
check("\\w predicate fixed", Pattern("\\w+").match("hello_123").group(0) == "hello_123")
check("\\s predicate fixed", Pattern("\\s+").match("  \t").group(0) == "  \t")

# Bug: sub with count didn't append remaining text
check("sub count appends rest", Pattern("\\d+").sub("X", "a1b2c3d", count=2) == "aXbXc3d")

# Bug: $ anchor in match mode
check("$ match at end of string", Pattern("hello$").search("hello") is not None)
check("$ search at end", Pattern("end$").search("the end") is not None)

# Bug: split with zero-length matches
check("split empty pattern", Pattern("").split("abc") == ["", "a", "b", "c", ""])

# Bug: alternation with empty branch
check("alt empty branch", Pattern("a|").match("") is not None)

# Bug: nested quantifiers (a*)* — Thompson NFA handles this correctly
check("nested star quantifier", Pattern("(a*)*").match("aaa") is not None)

# Bug: escaped backslash
check("escaped backslash", Pattern("\\\\").match("\\") is not None)

# Bug: ] at start of char class
check("] in charclass", Pattern("[]abc]").match("]") is not None)

# ============================================================
# Module-level API
# ============================================================
check("re.match", re.match("hello", "hello world").group(0) == "hello")
check("re.search", re.search("world", "hello world").group(0) == "world")
check("re.findall", re.findall("\\d+", "a1b23c") == ["1", "23"])
check("re.sub", re.sub("\\d+", "X", "a1b23c") == "aXbXc")
check("re.split", re.split(",", "a,b,c") == ["a", "b", "c"])

# ============================================================
# Error handling
# ============================================================
try:
    Parser("(abc").parse()
    check("unterminated group error", False, "should have raised ParseError")
except ParseError:
    check("unterminated group error", True)

try:
    Parser("[abc").parse()
    check("unterminated charclass error", False, "should have raised ParseError")
except ParseError:
    check("unterminated charclass error", True)

try:
    Parser("a{2,1}").parse()
    check("invalid quantifier error", False, "should have raised ParseError")
except ParseError:
    check("invalid quantifier error", True)

try:
    Pattern("^+")
    check("quantifier on anchor error", False, "should have raised ParseError")
except ParseError:
    check("quantifier on anchor error", True)

try:
    Pattern("*")
    check("bare star error", False, "should have raised ParseError")
except ParseError:
    check("bare star error", True)

try:
    Pattern("+")
    check("bare plus error", False, "should have raised ParseError")
except ParseError:
    check("bare plus error", True)


print(f"\n{'='*50}")
print(f"Results: {passed}/{total} passed, {total - passed} failed")
if total - passed > 0:
    print("Some tests failed!")
    sys.exit(1)
else:
    print("All tests passed!")
    sys.exit(0)