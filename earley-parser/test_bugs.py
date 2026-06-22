"""Bug hunt tests for the earley-parser project."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from earley import (
    Grammar, EarleyParser, ParseError, ParseNode,
    Tokenizer, TokenSpec, GrammarLoader,
)


# Bug 1: Memoization caches truncated results, potentially missing valid
# parse trees when max_trees is small.
def test_memo_truncation():
    """S -> A A; A -> a | B; B -> a. Input [a, a] has 4 trees.
    With max_trees=50 we should get 4. With max_trees=3, we should get 3
    (truncation is OK), but the memo should not cache the truncated result
    and prevent a later call with max_trees=50 from getting all 4."""
    g = Grammar.from_rules("S", [
        ("S", ("A", "A")),
        ("A", ("a",)),
        ("A", ("B",)),
        ("B", ("a",)),
    ])
    p = EarleyParser(g)
    # First call with small max_trees
    trees_small = p.trees_v2(["a", "a"], max_trees=3)
    assert len(trees_small) == 3, f"Expected 3, got {len(trees_small)}"
    # Second call with large max_trees should get all 4
    trees_full = p.trees_v2(["a", "a"], max_trees=50)
    assert len(trees_full) == 4, f"Expected 4 trees, got {len(trees_full)} (memo truncated!)"


# Bug 2: Tokenizer infinite loop on zero-length regex matches
def test_tokenizer_zero_length():
    """A regex like [0-9]* can match zero characters, causing an infinite loop.
    The tokenizer should detect zero-length matches and advance past them."""
    tok = Tokenizer([
        TokenSpec("NUM", r"[0-9]*"),  # can match empty string!
        TokenSpec("PLUS", r"\+"),
    ])
    # Should not hang — should raise ValueError on unmatched 'a'
    try:
        tokens = tok.tokenize("a+")
        # If it doesn't raise, it should at least not hang
        # (zero-length match at 'a' should advance position)
    except ValueError:
        pass  # Also acceptable: raises error on unmatched input
    # NUM should still work for actual numbers
    tok2 = Tokenizer([
        TokenSpec("NUM", r"[0-9]+"),
        TokenSpec("PLUS", r"\+"),
    ])
    assert tok2.tokenize("12+34") == ["NUM", "PLUS", "NUM"]


# Bug 3: _furthest_position takes unused parameter
def test_furthest_position_unused_param():
    """_furthest_position takes a `tokens` parameter it never uses.
    This is a code quality issue, not a correctness bug, but the method
    should work regardless of what's passed."""
    g = Grammar.from_rules("E", [
        ("E", ("E", "+", "E")),
        ("E", ("id",)),
    ])
    p = EarleyParser(g)
    p.parse(["id", "+"])  # builds charts
    # Should return 2 (furthest chart with items)
    pos = p._furthest_position([])
    assert pos == 2, f"Expected 2, got {pos}"


# Bug 4: Empty grammar (no rules) causes IndexError in GrammarLoader
def test_empty_grammar_loader():
    """Loading an empty grammar file should raise a clear error, not IndexError."""
    try:
        g = GrammarLoader.load("")
        assert False, "Should have raised ValueError"
    except (ValueError, IndexError) as e:
        # IndexError is the bug; ValueError is the fix
        if isinstance(e, IndexError):
            assert False, f"IndexError instead of ValueError: {e}"


# Bug 5: Memo causes tree sharing — modifying one tree affects another
def test_tree_sharing():
    """If the memo caches ParseNode objects and returns the same instances,
    modifying one tree would corrupt another."""
    g = Grammar.from_rules("S", [
        ("S", ("A", "A")),
        ("A", ("a",)),
        ("A", ("B",)),
        ("B", ("a",)),
    ])
    p = EarleyParser(g)
    trees = p.trees_v2(["a", "a"], max_trees=50)
    assert len(trees) == 4
    # Check that no two top-level trees share the same ParseNode object
    # for their children (they should be independent)
    for i in range(len(trees)):
        for j in range(i + 1, len(trees)):
            # The root nodes should be different objects
            assert trees[i] is not trees[j], "Root nodes shared!"
            # Check children are not shared
            for ci in trees[i].children:
                for cj in trees[j].children:
                    if ci is cj:
                        assert False, f"Child node shared between tree {i} and {j}"


# Bug 6: ParseError for empty input when start is not nullable
def test_empty_input_non_nullable():
    g = Grammar.from_rules("E", [
        ("E", ("E", "+", "E")),
        ("E", ("id",)),
    ])
    p = EarleyParser(g)
    result = p.parse_or_error([])
    assert isinstance(result, ParseError)
    assert result.position == 0


if __name__ == "__main__":
    failures = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as e:
                print(f"FAIL {name}: {e}")
                failures += 1
    if failures:
        print(f"\n{failures} test(s) failed")
        sys.exit(1)
    else:
        print(f"\nAll tests passed")