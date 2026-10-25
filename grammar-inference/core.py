"""Learn a compact probabilistic binary grammar from token sequences."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import random


@dataclass(frozen=True)
class Rule:
    """One production, represented by token strings or nonterminal spans."""
    left: str
    right: tuple[str, ...]
    count: int


class Grammar:
    """Weighted grammar whose nonterminals are observed token spans."""

    def __init__(self, rules: dict[str, Counter[tuple[str, ...]]], roots: Counter[str]):
        self.rules = rules
        self.roots = roots

    @property
    def rule_count(self) -> int:
        return sum(map(len, self.rules.values()))

    def _expand(self, symbol: str, rng: random.Random, depth: int, max_tokens: int) -> list[str]:
        if depth <= 0 or symbol not in self.rules:
            return symbol.split("\x1f")
        alternatives = list(self.rules[symbol].items())
        rhs = _weighted(alternatives, rng)
        result: list[str] = []
        for child in rhs:
            result.extend(self._expand(child, rng, depth - 1, max_tokens - len(result)))
            if len(result) > max_tokens:
                return result[:max_tokens]
        return result

    def sample(self, seed: int | None = None, max_tokens: int = 40, max_depth: int = 20) -> str:
        if max_tokens < 1 or max_depth < 1:
            raise ValueError("max_tokens and max_depth must be positive")
        root = _weighted(list(self.roots.items()), random.Random(seed))
        return " ".join(self._expand(root, random.Random(seed), max_depth, max_tokens)[:max_tokens])


def _weighted(items, rng):
    total = sum(weight for _, weight in items)
    pick = rng.randrange(total)
    for value, weight in items:
        if pick < weight:
            return value
        pick -= weight
    raise AssertionError("weighted choice invariant")


def learn(sentences: list[str]) -> Grammar:
    """Induce rules from non-empty whitespace-tokenized sentences."""
    if not sentences:
        raise ValueError("provide at least one training sentence")
    if len(sentences) > 10000:
        raise ValueError("at most 10000 training sentences are supported")
    roots: Counter[str] = Counter()
    rules: dict[str, Counter[tuple[str, ...]]] = defaultdict(Counter)
    for sentence in sentences:
        tokens = sentence.split()
        if not tokens:
            continue
        if len(tokens) > 200:
            raise ValueError("sentences may contain at most 200 tokens")
        spans: dict[tuple[int, int], str] = {}
        for width in range(1, len(tokens) + 1):
            for start in range(len(tokens) - width + 1):
                end = start + width
                key = "\x1f".join(tokens[start:end])
                spans[start, end] = key
                if width == 1:
                    rules[key][(tokens[start],)] += 1
                else:
                    splits = [(spans[start, mid], spans[mid, end]) for mid in range(start + 1, end)]
                    for rhs in splits:
                        rules[key][rhs] += 1
        roots[spans[0, len(tokens)]] += 1
    if not roots:
        raise ValueError("training sentences must contain at least one token")
    return Grammar(dict(rules), roots)
