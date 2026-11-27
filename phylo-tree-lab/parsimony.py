"""Small, dependency-free phylogenetic parsimony toolkit (Fitch algorithm)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Node:
    """A rooted tree node; leaves carry aligned character strings."""
    name: str | None = None
    sequence: str | None = None
    children: tuple["Node", ...] = ()

    def __post_init__(self) -> None:
        if self.children and self.sequence is not None:
            raise ValueError("internal nodes cannot carry sequences")
        if not self.children and self.sequence is None:
            raise ValueError("leaf nodes require a sequence")
        if self.sequence is not None and not self.sequence:
            raise ValueError("sequences must not be empty")
        if self.children:
            lengths = {len(leaf.sequence or "") for leaf in self.leaves()}
            if len(lengths) > 1:
                raise ValueError("all leaf sequences must have equal length")

    def leaves(self) -> tuple["Node", ...]:
        if not self.children:
            return (self,)
        return tuple(leaf for child in self.children for leaf in child.leaves())


def _combine(children: tuple[Node, ...], site: int) -> tuple[frozenset[str], int]:
    """Compute Fitch state set and substitutions for one subtree/site."""
    if not children:
        raise ValueError("internal node must have children")
    states, score = _states(children[0], site)
    for child in children[1:]:
        child_states, child_score = _states(child, site)
        common = states & child_states
        states = common if common else states | child_states
        score += child_score + int(not common)
    return states, score


def _states(node: Node, site: int) -> tuple[frozenset[str], int]:
    if not node.children:
        assert node.sequence is not None
        return frozenset((node.sequence[site],)), 0
    return _combine(node.children, site)


def fitch_score(tree: Node) -> int:
    """Return the minimum unordered-state changes across all sites."""
    leaves = tree.leaves()
    if not tree.children or len(leaves) < 2:
        raise ValueError("tree must contain at least two leaves")
    length = len(leaves[0].sequence or "")
    if not length:
        raise ValueError("leaf sequences must not be empty")
    return sum(_states(tree, site)[1] for site in range(length))


def parse_newick(text: str) -> Node:
    """Parse a simple rooted Newick tree whose leaves are name:SEQUENCE."""
    tokens = text.strip()
    if not tokens.endswith(";"):
        raise ValueError("Newick input must end with ';'")
    pos = 0

    def skip_label() -> None:
        nonlocal pos
        while pos < len(tokens) and tokens[pos] not in ",();":
            pos += 1

    def subtree() -> Node:
        nonlocal pos
        if pos < len(tokens) and tokens[pos] == "(":
            pos += 1
            children = [subtree()]
            while pos < len(tokens) and tokens[pos] == ",":
                pos += 1
                children.append(subtree())
            if pos >= len(tokens) or tokens[pos] != ")":
                raise ValueError("unclosed child list")
            pos += 1
            skip_label()
            return Node(children=tuple(children))
        start = pos
        while pos < len(tokens) and tokens[pos] not in ",();":
            pos += 1
        label = tokens[start:pos].strip()
        if ":" not in label:
            raise ValueError("leaf must be named NAME:SEQUENCE")
        name, sequence = label.split(":", 1)
        if not name or not sequence:
            raise ValueError("leaf name and sequence are required")
        return Node(name=name, sequence=sequence)

    result = subtree()
    if pos != len(tokens) - 1:
        raise ValueError("unexpected trailing Newick content")
    lengths = {len(leaf.sequence or "") for leaf in result.leaves()}
    if len(lengths) != 1:
        raise ValueError("all leaf sequences must have equal length")
    return result
