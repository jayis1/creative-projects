"""
Comprehensive tests for the regex engine.
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


class TestParser:
    """Test the regex parser."""

    def test_literal(self):
        ast = Parser("a").parse()
        assert ast is not None

    def test_concat(self):
        ast = Parser("ab").parse()
        assert ast is not None

    def test_alternation(self):
        ast = Parser("a|b").parse()
        assert ast is not None

    def test_group(self):
        ast = Parser("(ab)").parse()
        assert ast is not None

    def test_star(self):
        ast = Parser("a*").parse()
        assert ast is not None

    def test_plus(self):
        ast = Parser("a+").parse()
        assert ast is not None

    def test_question(self):
        ast = Parser("a?").parse()
        assert ast is not None

    def test_dot(self):
        ast = Parser(".").parse()
        assert ast is not None

    def test_escape_digit(self):
        ast = Parser("\\d").parse()
        assert ast is not None

    def test_escape_word(self):
        ast = Parser("\\w").parse()
        assert ast is not None

    def test_char_class(self):
        ast = Parser("[abc]").parse()
        assert ast is not None

    def test_char_class_range(self):
        ast = Parser("[a-z]").parse()
        assert ast is not None

    def test_char_class_negated(self):
        ast = Parser("[^0-9]").parse()
        assert ast is not None

    def test_quantifier_braces_exact(self):
        ast = Parser("a{3}").parse()
        assert ast is not None

    def test_quantifier_braces_range(self):
        ast = Parser("a{2,5}").parse()
        assert ast is not None

    def test_quantifier_braces_unbounded(self):
        ast = Parser("a{2,}").parse()
        assert ast is not None

    def test_non_greedy(self):
        ast = Parser("a*?").parse()
        assert ast is not None

    def test_anchor_start(self):
        ast = Parser("^a").parse()
        assert ast is not None

    def test_anchor_end(self):
        ast = Parser("a$").parse()
        assert ast is not None

    def test_unmatched_paren(self):
        try:
            Parser("(abc").parse()
            assert False, "Should have raised ParseError"
        except ParseError:
            pass

    def test_unmatched_bracket(self):
        try:
            Parser("[abc").parse()
            assert False, "Should have raised ParseError"
        except ParseError:
            pass


class TestCompiler:
    """Test the NFA compiler."""

    def test_compile_literal(self):
        ast = Parser("a").parse()
        start = Compiler().compile(ast)
        assert start is not None

    def test_compile_concat(self):
        ast = Parser("ab").parse()
        start = Compiler().compile(ast)
        assert start is not None

    def test_compile_alternation(self):
        ast = Parser("a|b").parse()
        start = Compiler().compile(ast)
        assert start is not None

    def test_compile_star(self):
        ast = Parser("a*").parse()
        start = Compiler().compile(ast)
        assert start is not None

    def test_compile_plus(self):
        ast = Parser("a+").parse()
        start = Compiler().compile(ast)
        assert start is not None

    def test_compile_complex(self):
        ast = Parser("(a|b)*c").parse()
        start = Compiler().compile(ast)
        assert start is not None


class TestMatcher:
    """Test the NFA matcher."""

    def _match(self, pattern, text):
        return Pattern(pattern).match(text)

    def _search(self, pattern, text):
        return Pattern(pattern).search(text)

    # Literal matches
    def test_literal_match(self):
        m = self._match("a", "a")
        assert m is not None and m.group(0) == "a"

    def test_literal_no_match(self):
        m = self._match("a", "b")
        assert m is None

    def test_literal_match_prefix(self):
        m = self._match("a", "ab")
        assert m is not None and m.group(0) == "a"

    # Concatenation
    def test_concat_match(self):
        m = self._match("ab", "ab")
        assert m is not None and m.group(0) == "ab"

    def test_concat_no_match(self):
        m = self._match("ab", "ac")
        assert m is None

    # Alternation
    def test_alt_match_first(self):
        m = self._match("a|b", "a")
        assert m is not None and m.group(0) == "a"

    def test_alt_match_second(self):
        m = self._match("a|b", "b")
        assert m is not None and m.group(0) == "b"

    def test_alt_no_match(self):
        m = self._match("a|b", "c")
        assert m is None

    def test_alt_three(self):
        m = self._match("a|b|c", "b")
        assert m is not None and m.group(0) == "b"

    # Star
    def test_star_zero(self):
        m = self._match("a*", "")
        assert m is not None and m.group(0) == ""

    def test_star_one(self):
        m = self._match("a*", "a")
        assert m is not None and m.group(0) == "a"

    def test_star_many(self):
        m = self._match("a*", "aaa")
        assert m is not None and m.group(0) == "aaa"

    # Plus
    def test_plus_zero(self):
        m = self._match("a+", "")
        assert m is None

    def test_plus_one(self):
        m = self._match("a+", "a")
        assert m is not None and m.group(0) == "a"

    def test_plus_many(self):
        m = self._match("a+", "aaa")
        assert m is not None and m.group(0) == "aaa"

    # Question
    def test_question_zero(self):
        m = self._match("a?", "")
        assert m is not None and m.group(0) == ""

    def test_question_one(self):
        m = self._match("a?", "a")
        assert m is not None and m.group(0) == "a"

    # Dot
    def test_dot_match(self):
        m = self._match(".", "a")
        assert m is not None and m.group(0) == "a"

    def test_dot_no_newline(self):
        m = self._match(".", "\n")
        assert m is None

    def test_dot_no_empty(self):
        m = self._match(".", "")
        assert m is None

    # Character classes
    def test_char_class_match(self):
        m = self._match("[abc]", "b")
        assert m is not None and m.group(0) == "b"

    def test_char_class_no_match(self):
        m = self._match("[abc]", "d")
        assert m is None

    def test_char_class_range(self):
        m = self._match("[a-z]", "m")
        assert m is not None and m.group(0) == "m"

    def test_char_class_range_no_match(self):
        m = self._match("[a-z]", "M")
        assert m is None

    def test_char_class_negated(self):
        m = self._match("[^0-9]", "a")
        assert m is not None

    def test_char_class_negated_no_match(self):
        m = self._match("[^0-9]", "5")
        assert m is None

    # Shorthand classes
    def test_digit_match(self):
        m = self._match("\\d", "5")
        assert m is not None and m.group(0) == "5"

    def test_digit_no_match(self):
        m = self._match("\\d", "a")
        assert m is None

    def test_word_match(self):
        m = self._match("\\w", "a")
        assert m is not None

    def test_word_underscore(self):
        m = self._match("\\w", "_")
        assert m is not None

    def test_space_match(self):
        m = self._match("\\s", " ")
        assert m is not None

    def test_non_digit(self):
        m = self._match("\\D", "a")
        assert m is not None

    def test_non_word(self):
        m = self._match("\\W", "!")
        assert m is not None

    def test_non_space(self):
        m = self._match("\\S", "a")
        assert m is not None

    # Search
    def test_search_found(self):
        m = self._search("bc", "abcd")
        assert m is not None and m.group(0) == "bc" and m.start == 1

    def test_search_not_found(self):
        m = self._search("xyz", "abcd")
        assert m is None

    # Complex patterns
    def test_complex_pattern_1(self):
        m = self._match("(a|b)*c", "ababc")
        assert m is not None and m.group(0) == "ababc"

    def test_complex_pattern_2(self):
        m = self._match("(a|b)*c", "c")
        assert m is not None and m.group(0) == "c"

    def test_email_like(self):
        p = Pattern("[a-z]+@[a-z]+\\.[a-z]+")
        m = p.match("user@example.com")
        assert m is not None and m.group(0) == "user@example.com"

    # Findall
    def test_findall_words(self):
        p = Pattern("[a-z]+")
        result = p.findall("hello world foo")
        assert result == ["hello", "world", "foo"]

    def test_findall_digits(self):
        p = Pattern("\\d+")
        result = p.findall("a1b23c456")
        assert result == ["1", "23", "456"]

    # Sub
    def test_sub(self):
        p = Pattern("\\d+")
        result = p.sub("NUM", "a1b23c456")
        assert result == "aNUMbNUMcNUM"

    def test_sub_count(self):
        p = Pattern("\\d+")
        result = p.sub("NUM", "a1b23c456", count=2)
        assert result == "aNUMbNUMc456"

    # Split
    def test_split(self):
        p = Pattern(",")
        result = p.split("a,b,c")
        assert result == ["a", "b", "c"]

    def test_split_regex(self):
        p = Pattern("\\s+")
        result = p.split("hello   world  foo")
        assert result == ["hello", "world", "foo"]

    # Brace quantifiers
    def test_brace_exact(self):
        m = self._match("a{3}", "aaa")
        assert m is not None and m.group(0) == "aaa"

    def test_brace_exact_no_match(self):
        m = self._match("a{3}", "aa")
        assert m is None

    def test_brace_range(self):
        m = self._match("a{2,4}", "aaa")
        assert m is not None and m.group(0) == "aaa"

    def test_brace_unbounded(self):
        m = self._match("a{2,}", "aaaaa")
        assert m is not None and m.group(0) == "aaaaa"

    # Module-level API
    def test_module_match(self):
        m = re.match("hello", "hello world")
        assert m is not None and m.group(0) == "hello"

    def test_module_search(self):
        m = re.search("world", "hello world")
        assert m is not None and m.group(0) == "world"

    def test_module_findall(self):
        result = re.findall("\\d+", "a1b23c")
        assert result == ["1", "23"]

    def test_module_sub(self):
        result = re.sub("\\d+", "X", "a1b23c")
        assert result == "aXbXc"

    def test_module_split(self):
        result = re.split(",", "a,b,c")
        assert result == ["a", "b", "c"]

    # Edge cases
    def test_empty_pattern(self):
        m = self._match("", "")
        assert m is not None

    def test_empty_pattern_in_string(self):
        m = self._match("", "abc")
        assert m is not None and m.group(0) == ""

    def test_escaped_meta(self):
        m = self._match("\\.", ".")
        assert m is not None and m.group(0) == "."

    def test_escaped_meta_no_match(self):
        m = self._match("\\.", "a")
        assert m is None

    # More complex patterns
    def test_nested_groups(self):
        m = self._match("((a)(b))", "ab")
        assert m is not None and m.group(0) == "ab"

    def test_complex_alternation(self):
        m = self._match("cat|dog|bird", "dog")
        assert m is not None and m.group(0) == "dog"

    def test_repeated_group(self):
        m = self._match("(ab)+", "ababab")
        assert m is not None and m.group(0) == "ababab"

    def test_mixed_quantifiers(self):
        m = self._match("a*b+c?", "aab")
        assert m is not None and m.group(0) == "aab"

    def test_dot_star(self):
        m = self._match(".*", "hello world")
        assert m is not None and m.group(0) == "hello world"

    def test_search_middle(self):
        m = self._search("lo", "hello")
        assert m is not None and m.group(0) == "lo" and m.start == 3


def run_tests():
    """Run all tests and report results."""
    test_classes = [TestParser, TestCompiler, TestMatcher]
    total = 0
    passed = 0
    failed = 0
    errors = []

    for test_class in test_classes:
        instance = test_class()
        methods = [m for m in dir(instance) if m.startswith('test_')]

        for method_name in methods:
            total += 1
            method = getattr(instance, method_name)
            try:
                method()
                passed += 1
                print(f"  ✓ {test_class.__name__}.{method_name}")
            except Exception as e:
                failed += 1
                errors.append((test_class.__name__, method_name, str(e)))
                print(f"  ✗ {test_class.__name__}.{method_name}: {e}")

    print(f"\n{'='*50}")
    print(f"Results: {passed}/{total} passed, {failed} failed")

    if errors:
        print(f"\nFailed tests:")
        for cls, method, error in errors:
            print(f"  {cls}.{method}: {error}")

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)