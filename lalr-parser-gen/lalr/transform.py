"""Grammar transformation utilities.

Provides algorithms for transforming grammars to make them suitable for
LL/LR parsing:

    - **Left recursion removal**: Convert left-recursive rules to
      right-recursive equivalents using the standard A → Aα | β
      transformation.
    - **Left factoring**: Factor common prefixes from alternatives to
      reduce conflicts.
    - **Epsilon removal**: Attempt to eliminate epsilon productions
      where possible.
    - **Reachability pruning**: Remove unreachable non-terminals.
    - **Useless symbol elimination**: Remove symbols that never derive
      terminal strings.

These transformations can help resolve conflicts in grammars that are
not naturally LALR(1).
"""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


def remove_left_recursion(
    productions: List[Tuple[str, List[str]]],
    start: Optional[str] = None,
) -> Tuple[List[Tuple[str, List[str]]], str]:
    """Remove immediate left recursion from a grammar.

    For a rule A → Aα₁ | Aα₂ | ... | β₁ | β₂ | ...,
    transforms to:
        A  → β₁ A' | β₂ A' | ...
        A' → α₁ A' | α₂ A' | ε

    Args:
        productions: List of (head, body) tuples.
        start: Start symbol (defaults to first production's head).

    Returns:
        (transformed_productions, start_symbol)
    """
    if not productions:
        return [], start or ""

    if start is None:
        start = productions[0][0]

    # Group productions by head
    by_head: Dict[str, List[List[str]]] = {}
    for head, body in productions:
        by_head.setdefault(head, []).append(list(body))

    result: List[Tuple[str, List[str]]] = []

    for head in list(by_head.keys()):
        alts = by_head[head]
        recursive: List[List[str]] = []
        non_recursive: List[List[str]] = []

        for alt in alts:
            if alt and alt[0] == head:
                recursive.append(alt[1:])  # α (without leading A)
            else:
                non_recursive.append(alt)

        if not recursive:
            # No left recursion — keep as-is
            for alt in alts:
                result.append((head, alt))
            continue

        # Introduce A' for left recursion
        prime = head + "'"
        while prime in by_head or any(p[0] == prime for p in result):
            prime += "'"

        logger.debug("Removing left recursion from %s, introducing %s", head, prime)

        # A → β₁ A' | β₂ A' | ...
        for beta in non_recursive:
            result.append((head, beta + [prime]))

        # A' → α₁ A' | α₂ A' | ε
        for alpha in recursive:
            result.append((prime, alpha + [prime]))
        result.append((prime, []))  # epsilon

    # Ensure start symbol is first
    result.sort(key=lambda p: 0 if p[0] == start else 1)

    return result, start


def left_factor(
    productions: List[Tuple[str, List[str]]],
) -> List[Tuple[str, List[str]]]:
    """Left-factor common prefixes from alternatives.

    For A → αβ₁ | αβ₂ | γ, produces:
        A  → α A_factored | γ
        A_factored → β₁ | β₂

    Args:
        productions: List of (head, body) tuples.

    Returns:
        Transformed productions list.
    """
    if not productions:
        return []

    # Group by head
    by_head: Dict[str, List[List[str]]] = {}
    for head, body in productions:
        by_head.setdefault(head, []).append(list(body))

    result: List[Tuple[str, List[str]]] = []
    used_names: Set[str] = set(by_head.keys())

    def _fresh_name(base: str) -> str:
        name = base + "_factored"
        while name in used_names:
            name += "_"
        used_names.add(name)
        return name

    for head, alts in by_head.items():
        if len(alts) <= 1:
            for alt in alts:
                result.append((head, alt))
            continue

        # Group alternatives by their first symbol
        # Only factor groups with 2+ alternatives sharing a prefix
        first_groups: Dict[str, List[List[str]]] = {}
        no_prefix: List[List[str]] = []
        for alt in alts:
            if alt:
                first_groups.setdefault(alt[0], []).append(alt)
            else:
                no_prefix.append(alt)

        factored_any = False
        for first_sym, group in first_groups.items():
            if len(group) < 2:
                # Only one alternative starts with this symbol — no factoring needed
                for alt in group:
                    result.append((head, alt))
                continue

            # Find common prefix length among this group
            prefix_len = 0
            min_len = min(len(a) for a in group)
            for i in range(min_len):
                sym = group[0][i]
                if all(a[i] == sym for a in group):
                    prefix_len = i + 1
                else:
                    break

            if prefix_len == 0:
                for alt in group:
                    result.append((head, alt))
                continue

            # Factor out the common prefix
            prefix = group[0][:prefix_len]
            factored_name = _fresh_name(head)

            # A -> prefix A_factored
            result.append((head, prefix + [factored_name]))

            # A_factored -> beta_1 | beta_2 | ...
            for alt in group:
                suffix = alt[prefix_len:]
                result.append((factored_name, suffix if suffix else []))

            logger.debug("Left-factored %s (prefix=%s), introduced %s",
                         head, prefix, factored_name)
            factored_any = True

        # Add alternatives with no prefix (epsilon)
        for alt in no_prefix:
            result.append((head, alt))

        if not factored_any and len(first_groups) <= 1:
            # No factoring was possible — keep originals
            # (Already added above, so nothing more to do)
            pass

    return result


def remove_unreachable(
    productions: List[Tuple[str, List[str]]],
    start: str,
) -> List[Tuple[str, List[str]]]:
    """Remove productions that are unreachable from the start symbol.

    Args:
        productions: List of (head, body) tuples.
        start: Start symbol.

    Returns:
        Filtered productions list with only reachable rules.
    """
    # Collect all non-terminals
    nonterminals: Set[str] = set()
    for head, _ in productions:
        nonterminals.add(head)

    # BFS from start
    reachable: Set[str] = set()
    queue: List[str] = [start]
    while queue:
        nt = queue.pop()
        if nt in reachable:
            continue
        reachable.add(nt)
        for head, body in productions:
            if head == nt:
                for sym in body:
                    if sym in nonterminals and sym not in reachable:
                        queue.append(sym)

    # Filter productions
    result = [
        (head, body) for head, body in productions
        if head in reachable
    ]

    removed = len(productions) - len(result)
    if removed:
        logger.info("Removed %d unreachable productions", removed)

    return result


def eliminate_useless_symbols(
    productions: List[Tuple[str, List[str]]],
    start: str,
) -> List[Tuple[str, List[str]]]:
    """Eliminate non-terminals that never derive a terminal-only string.

    A non-terminal is "useful" if it can derive a string of terminals.
    This iteratively removes non-terminals that only derive non-terminals
    that are themselves useless.

    Args:
        productions: List of (head, body) tuples.
        start: Start symbol.

    Returns:
        Filtered productions list.
    """
    # Determine which non-terminals can derive terminal strings
    nonterminals: Set[str] = set(head for head, _ in productions)
    terminals: Set[str] = set()
    for _, body in productions:
        for sym in body:
            if sym not in nonterminals:
                terminals.add(sym)

    # Iteratively find "productive" non-terminals
    productive: Set[str] = set()
    changed = True
    while changed:
        changed = False
        for head, body in productions:
            if head in productive:
                continue
            # A non-terminal is productive if all symbols in some body
            # are either terminals or productive non-terminals
            if all(
                sym in terminals or sym in productive
                for sym in body
            ):
                productive.add(head)
                changed = True

    # Filter to productive productions
    result = [
        (head, body) for head, body in productions
        if head in productive
        and all(s in terminals or s in productive for s in body)
    ]

    # Then remove unreachable from start
    result = remove_unreachable(result, start)

    return result


def grammar_summary(
    productions: List[Tuple[str, List[str]]],
    start: Optional[str] = None,
) -> str:
    """Return a human-readable summary of a grammar."""
    if not productions:
        return "Empty grammar"

    if start is None:
        start = productions[0][0]

    nonterminals: Set[str] = set(head for head, _ in productions)
    terminals: Set[str] = set()
    for _, body in productions:
        for sym in body:
            if sym not in nonterminals:
                terminals.add(sym)

    lines = [
        f"Grammar summary:",
        f"  Start symbol: {start}",
        f"  Productions: {len(productions)}",
        f"  Non-terminals: {len(nonterminals)} — {sorted(nonterminals)}",
        f"  Terminals: {len(terminals)} — {sorted(terminals)}",
        "",
        "Productions:",
    ]
    for i, (head, body) in enumerate(productions):
        rhs = " ".join(body) if body else "ε"
        lines.append(f"  {i}: {head} → {rhs}")

    return "\n".join(lines)