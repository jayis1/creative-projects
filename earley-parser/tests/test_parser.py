"""Tests for the EarleyParser, Chart, Item, ParseNode, and ParseForest."""
import pytest
from earley_parser import (
    Grammar, EarleyParser, ParseError, ParseNode, ParseForest,
    GrammarLoader, EMPTY,
)


# -- Fixtures ---------------------------------------------------------------- #

@pytest.fixture
def expr_grammar():
    return Grammar.from_rules("E", [
        ("E", ("E", "+", "E")),
        ("E", ("E", "*", "E")),
        ("E", ("(", "E", ")")),
        ("E", ("id",)),
    ])


@pytest.fixture
def balance_grammar():
    return Grammar.from_rules("S", [
        ("S", ("(", "S", ")")),
        ("S", ("S", "S")),
        ("S", ()),
    ])


@pytest.fixture
def unambiguous_expr():
    return Grammar.from_rules("E", [
        ("E", ("E", "+", "T")),
        ("E", ("T",)),
        ("T", ("T", "*", "F")),
        ("T", ("F",)),
        ("F", ("(", "E", ")")),
        ("F", ("id",)),
    ])


# -- Recognition ------------------------------------------------------------- #

class TestRecognition:
    def test_basic_accept(self, expr_grammar):
        p = EarleyParser(expr_grammar)
        assert p.parse(["id"])
        assert p.parse(["id", "+", "id"])
        assert p.parse(["id", "+", "id", "*", "id"])
        assert p.parse(["(", "id", "+", "id", ")", "*", "id"])

    def test_basic_reject(self, expr_grammar):
        p = EarleyParser(expr_grammar)
        assert not p.parse(["id", "+"])
        assert not p.parse(["+", "id"])
        assert not p.parse([])
        assert not p.parse(["id", "id"])

    def test_epsilon(self, balance_grammar):
        p = EarleyParser(balance_grammar)
        assert p.parse([])
        assert p.parse(["(", ")"])
        assert p.parse(["(", "(", ")", ")"])
        assert not p.parse(["(", ")", ")"])

    def test_nullable_midrule(self):
        g = Grammar.from_rules("A", [
            ("A", ("B", "C")),
            ("B", ("x",)),
            ("B", ()),
            ("C", ("c",)),
        ])
        p = EarleyParser(g)
        assert p.parse(["x", "c"])
        assert p.parse(["c"])
        assert not p.parse(["x"])


# -- Tree Extraction --------------------------------------------------------- #

class TestTreeExtraction:
    def test_single_tree(self, expr_grammar):
        p = EarleyParser(expr_grammar)
        trees = p.trees(["id"])
        assert len(trees) == 1
        assert trees[0].symbol == "E"
        assert trees[0].start == 0
        assert trees[0].end == 1

    def test_ambiguous_multiple_trees(self, expr_grammar):
        p = EarleyParser(expr_grammar)
        trees = p.trees(["id", "+", "id", "*", "id"], max_trees=10)
        assert len(trees) >= 2

    def test_unambiguous_one_tree(self, unambiguous_expr):
        p = EarleyParser(unambiguous_expr)
        trees = p.trees(["id", "+", "id", "*", "id"], max_trees=10)
        assert len(trees) == 1

    def test_tree_spans(self, expr_grammar):
        p = EarleyParser(expr_grammar)
        trees = p.trees(["id", "+", "id"])
        assert len(trees) == 1
        t = trees[0]
        assert t.start == 0 and t.end == 3
        assert len(t.children) == 3
        assert t.children[0].start == 0 and t.children[0].end == 1
        assert t.children[1].symbol == "+"

    def test_trees_v2_alias(self, expr_grammar):
        """Backward compatibility: trees_v2 should work."""
        p = EarleyParser(expr_grammar)
        trees = p.trees_v2(["id"])
        assert len(trees) == 1

    def test_max_trees_limit(self, expr_grammar):
        p = EarleyParser(expr_grammar)
        trees = p.trees(["id", "+", "id", "*", "id"], max_trees=1)
        assert len(trees) <= 1

    def test_tree_node_independence(self):
        """Parse trees should not share ParseNode objects."""
        g = Grammar.from_rules("S", [
            ("S", ("A", "A")),
            ("A", ("a",)),
            ("A", ("B",)),
            ("B", ("a",)),
        ])
        p = EarleyParser(g)
        trees = p.trees(["a", "a"], max_trees=50)
        assert len(trees) == 4
        for i in range(len(trees)):
            for j in range(i + 1, len(trees)):
                assert trees[i] is not trees[j]
                for ci in trees[i].children:
                    for cj in trees[j].children:
                        assert ci is not cj, "Shared child node!"


# -- Parse Forest ------------------------------------------------------------ #

class TestParseForest:
    def test_forest_basic(self, expr_grammar):
        p = EarleyParser(expr_grammar)
        forest = p.forest(["id", "+", "id", "*", "id"], max_trees=10)
        assert len(forest) >= 2
        assert forest.is_ambiguous
        assert forest.ambiguity_count >= 2

    def test_forest_unambiguous(self, unambiguous_expr):
        p = EarleyParser(unambiguous_expr)
        forest = p.forest(["id", "+", "id"])
        assert not forest.is_ambiguous
        assert len(forest) == 1

    def test_forest_stats(self, expr_grammar):
        p = EarleyParser(expr_grammar)
        forest = p.forest(["id", "+", "id", "*", "id"])
        stats = forest.stats()
        assert stats["tree_count"] >= 2
        assert stats["is_ambiguous"] is True
        assert stats["max_depth"] > 0
        assert stats["total_nodes"] > 0

    def test_forest_pretty(self, expr_grammar):
        p = EarleyParser(expr_grammar)
        forest = p.forest(["id"])
        s = forest.pretty()
        assert "Tree 1" in s
        assert "E" in s

    def test_forest_to_json(self, expr_grammar):
        p = EarleyParser(expr_grammar)
        forest = p.forest(["id"])
        j = forest.to_json()
        assert '"symbol"' in j
        assert '"span"' in j

    def test_forest_to_dot(self, expr_grammar):
        p = EarleyParser(expr_grammar)
        forest = p.forest(["id"])
        dot = forest.to_dot()
        assert "digraph" in dot
        assert "ParseTree" in dot

    def test_forest_to_lisp(self, expr_grammar):
        p = EarleyParser(expr_grammar)
        forest = p.forest(["id"])
        lisp = forest.to_lisp()
        assert lisp.startswith("(E")

    def test_forest_iteration(self, expr_grammar):
        p = EarleyParser(expr_grammar)
        forest = p.forest(["id", "+", "id", "*", "id"], max_trees=10)
        count = sum(1 for _ in forest)
        assert count == len(forest)

    def test_forest_indexing(self, expr_grammar):
        p = EarleyParser(expr_grammar)
        forest = p.forest(["id"])
        assert forest[0].symbol == "E"


# -- ParseNode --------------------------------------------------------------- #

class TestParseNode:
    def test_is_leaf(self):
        node = ParseNode("id", 0, 1, [])
        assert node.is_leaf()

    def test_not_leaf(self):
        node = ParseNode("E", 0, 1, [ParseNode("id", 0, 1, [])])
        assert not node.is_leaf()

    def test_to_dict(self):
        node = ParseNode("E", 0, 3, [ParseNode("id", 0, 1, [])])
        d = node.to_dict()
        assert d["symbol"] == "E"
        assert d["span"] == [0, 3]
        assert len(d["children"]) == 1

    def test_to_json(self):
        node = ParseNode("E", 0, 1, [ParseNode("id", 0, 1, [])])
        j = node.to_json()
        assert '"symbol": "E"' in j

    def test_pretty(self):
        node = ParseNode("E", 0, 1, [ParseNode("id", 0, 1, [])])
        s = node.pretty()
        assert "E" in s
        assert "id" in s

    def test_yield_terminals(self):
        node = ParseNode("E", 0, 3, [
            ParseNode("E", 0, 1, [ParseNode("id", 0, 1, [])]),
            ParseNode("+", 1, 2, []),
            ParseNode("E", 2, 3, [ParseNode("id", 2, 3, [])]),
        ])
        terminals = node.yield_terminals()
        assert terminals == ["id", "+", "id"]

    def test_depth(self):
        node = ParseNode("E", 0, 3, [
            ParseNode("E", 0, 1, [ParseNode("id", 0, 1, [])]),
            ParseNode("+", 1, 2, []),
        ])
        assert node.depth() == 3

    def test_count_nodes(self):
        node = ParseNode("E", 0, 3, [
            ParseNode("E", 0, 1, [ParseNode("id", 0, 1, [])]),
            ParseNode("+", 1, 2, []),
        ])
        assert node.count_nodes() == 4

    def test_walk(self):
        node = ParseNode("E", 0, 3, [
            ParseNode("id", 0, 1, []),
            ParseNode("+", 1, 2, []),
        ])
        nodes = list(node.walk())
        assert len(nodes) == 3
        assert nodes[0].symbol == "E"

    def test_is_ambiguous(self):
        node = ParseNode("E", 0, 3, alternatives=[
            [ParseNode("id", 0, 1, [])],
            [ParseNode("(", 0, 1, [])],
        ])
        assert node.is_ambiguous()


# -- Error Reporting --------------------------------------------------------- #

class TestErrorReporting:
    def test_parse_error_position(self, expr_grammar):
        p = EarleyParser(expr_grammar)
        result = p.parse_or_error(["id", "+"])
        assert isinstance(result, ParseError)
        assert result.position == 2

    def test_parse_error_expected_set(self, expr_grammar):
        p = EarleyParser(expr_grammar)
        result = p.parse_or_error(["id", "+"])
        assert isinstance(result, ParseError)
        assert "id" in result.expected or "(" in result.expected

    def test_parse_error_empty_input(self):
        g = Grammar.from_rules("E", [
            ("E", ("E", "+", "E")),
            ("E", ("id",)),
        ])
        p = EarleyParser(g)
        result = p.parse_or_error([])
        assert isinstance(result, ParseError)
        assert result.position == 0

    def test_parse_error_to_dict(self, expr_grammar):
        p = EarleyParser(expr_grammar)
        result = p.parse_or_error(["id", "+"])
        d = result.to_dict()
        assert d["position"] == 2
        assert isinstance(d["expected"], list)

    def test_trees_raises_parse_error(self, expr_grammar):
        p = EarleyParser(expr_grammar)
        with pytest.raises(ParseError):
            p.trees(["id", "+"])

    def test_parse_error_message(self, expr_grammar):
        p = EarleyParser(expr_grammar)
        result = p.parse_or_error(["id", "+"])
        msg = str(result)
        assert "position 2" in msg
        assert "expected" in msg


# -- Diagnostics ------------------------------------------------------------- #

class TestDiagnostics:
    def test_chart_stats(self, expr_grammar):
        p = EarleyParser(expr_grammar)
        p.parse(["id", "+", "id"])
        stats = p.chart_stats()
        assert len(stats) == 4  # n+1 charts
        assert all(s > 0 for s in stats)

    def test_chart_dump(self, expr_grammar):
        p = EarleyParser(expr_grammar)
        p.parse(["id"])
        dump = p.chart_dump()
        assert "Chart[0]" in dump
        assert "items" in dump

    def test_ambiguity_count(self, expr_grammar):
        p = EarleyParser(expr_grammar)
        assert p.ambiguity_count(["id", "+", "id", "*", "id"]) >= 2

    def test_is_ambiguous(self, expr_grammar):
        p = EarleyParser(expr_grammar)
        assert p.is_ambiguous(["id", "+", "id", "*", "id"])
        assert not p.is_ambiguous(["id"])

    def test_ambiguity_count_on_parse_error(self, expr_grammar):
        p = EarleyParser(expr_grammar)
        assert p.ambiguity_count(["id", "+"]) == 0


# -- Item -------------------------------------------------------------------- #

class TestItem:
    def test_next_symbol(self):
        from earley_parser import Item
        item = Item("E", ("E", "+", "E"), 0, 0)
        assert item.next_symbol() == "E"

    def test_next_symbol_complete(self):
        from earley_parser import Item
        item = Item("E", ("E", "+", "E"), 3, 0)
        assert item.next_symbol() is None

    def test_is_complete(self):
        from earley_parser import Item
        assert Item("E", ("id",), 1, 0).is_complete()
        assert not Item("E", ("id",), 0, 0).is_complete()

    def test_advanced(self):
        from earley_parser import Item
        item = Item("E", ("E", "+", "E"), 0, 0)
        advanced = item.advanced()
        assert advanced.dot == 1
        assert advanced.origin == 0

    def test_repr(self):
        from earley_parser import Item
        item = Item("E", ("E", "+", "E"), 1, 0)
        s = repr(item)
        assert "E" in s
        assert "•" in s

    def test_frozen(self):
        """Items are frozen (hashable) and can be used in sets."""
        from earley_parser import Item
        item = Item("E", ("id",), 0, 0)
        s = {item}
        assert item in s