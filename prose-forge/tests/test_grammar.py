"""Tests for the grammar engine."""

from prose_forge.grammar import Grammar, BUILTIN_GRAMMAR


class TestGrammarBasics:
    def test_simple_expansion(self):
        g = Grammar({"start": ["hello world"]})
        assert g.generate() == "hello world"

    def test_recursive_expansion(self):
        g = Grammar({
            "start": ["<greeting> <name>"],
            "greeting": ["hello", "hi"],
            "name": ["world", "there"],
        }, seed=42)
        result = g.generate()
        words = result.split()
        assert len(words) == 2
        assert words[0] in ("hello", "hi")
        assert words[1] in ("world", "there")

    def test_unresolved_symbol_stays_visible(self):
        g = Grammar({"start": ["hello <missing>"]})
        result = g.generate()
        assert "<missing>" in result

    def test_whitespace_cleanup(self):
        g = Grammar({"start": ["  hello   world  ."]})
        result = g.generate()
        assert "  " not in result
        assert " ." not in result
        assert result.endswith(".")

    def test_reproducible_with_seed(self):
        g1 = Grammar(BUILTIN_GRAMMAR, seed=123)
        g2 = Grammar(BUILTIN_GRAMMAR, seed=123)
        assert g1.generate() == g2.generate()

    def test_different_seeds_differ(self):
        g1 = Grammar(BUILTIN_GRAMMAR, seed=1)
        g2 = Grammar(BUILTIN_GRAMMAR, seed=999)
        # Not guaranteed to differ, but extremely likely with this grammar
        assert g1.generate() != g2.generate()


class TestGrammarWeighted:
    def test_weighted_rules(self):
        g = Grammar({
            "start": [(10, "common"), (1, "rare")],
        }, seed=42)
        counts = {"common": 0, "rare": 0}
        for _ in range(100):
            counts[g.generate()] += 1
        assert counts["common"] > counts["rare"]

    def test_add_rule_string(self):
        g = Grammar()
        g.add_rule("start", "hello")
        assert g.generate() == "hello"

    def test_add_rule_tuple(self):
        g = Grammar()
        g.add_rule("start", (2, "weighted"))
        assert g.generate() == "weighted"


class TestGrammarVariables:
    def test_variable_substitution(self):
        g = Grammar({"start": ["Hello, {name}!"]})
        g.set_var("name", "World")
        assert g.generate() == "Hello, World!"

    def test_conditional_rules(self):
        g = Grammar({
            "start": [
                (1, "small", "size == 'small'"),
                (1, "large", "size == 'large'"),
            ],
        })
        g.set_var("size", "small")
        assert g.generate() == "small"
        g.set_var("size", "large")
        assert g.generate() == "large"


class TestBuiltinGrammar:
    def test_generates_nonempty(self):
        g = Grammar(BUILTIN_GRAMMAR, seed=42)
        result = g.generate()
        assert len(result) > 50

    def test_no_unresolved_symbols(self):
        g = Grammar(BUILTIN_GRAMMAR, seed=42)
        result = g.generate()
        assert "<" not in result
        assert "{" not in result