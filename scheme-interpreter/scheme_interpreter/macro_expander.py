"""Hygienic macro system via syntax-rules.

Implements ``define-syntax`` with ``syntax-rules`` pattern matching:
- Pattern matching with wildcards and literals
- Ellipsis (``...``) patterns capturing zero or more forms
- Hygiene via systematic renaming of introduced identifiers
- Recursive macro expansion
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple
from .types import Symbol, Pair, Nil, Bool, Char, Vector, Unspecified, Macro
from .environment import Environment


class EllipsisBinding:
    """Wrapper for ellipsis-collected bindings.

    Distinguishes ``[v1, v2, v3]`` (a single value that happens to be a
    Python list) from an ellipsis capture of three values ``v1``, ``v2``,
    ``v3``.
    """

    __slots__ = ("values",)

    def __init__(self, values: list):
        self.values = values


def is_macro(name: str, env: Environment) -> bool:
    """Check if *name* is bound to a macro in *env*."""
    try:
        val = env.lookup(name)
        return isinstance(val, Macro)
    except NameError:
        return False


def parse_syntax_rules(form, env: Environment) -> Macro:
    """Parse a ``(syntax-rules (literals...) (pattern template) ...)`` form."""
    # form = (syntax-rules (literals...) rules...)
    if not isinstance(form, Pair) or not isinstance(form.car, Symbol) or form.car.name != "syntax-rules":
        raise SyntaxError("expected syntax-rules form")
    literals_form = form.cdr.car
    literals = []
    node = literals_form
    while isinstance(node, Pair):
        if isinstance(node.car, Symbol):
            literals.append(node.car.name)
        node = node.cdr
    rules = []
    node = form.cdr.cdr
    while isinstance(node, Pair):
        rule = node.car
        pattern = rule.car
        template = rule.cdr.car
        rules.append((pattern, template))
        node = node.cdr
    return Macro(rules, literals)


def define_syntax_rules(interp, expr, env: Environment):
    """Handle ``(define-syntax name (syntax-rules ...))``."""
    name = expr.cdr.car
    if not isinstance(name, Symbol):
        raise SyntaxError("define-syntax: name must be a symbol")
    rules_form = expr.cdr.cdr.car
    macro = parse_syntax_rules(rules_form, env)
    env.define(name.name, macro)
    return Unspecified


def expand_macros(form, env: Environment, interp) -> Any:
    """Recursively expand macros in *form*."""
    if not isinstance(form, Pair):
        return form
    head = form.car
    if isinstance(head, Symbol):
        # Check if it's a macro
        try:
            val = env.lookup(head.name)
        except NameError:
            val = None
        if isinstance(val, Macro):
            expanded = _expand_one(val, form, env, interp)
            return expand_macros(expanded, env, interp)
    # Recurse into sub-forms (but not for quote)
    if isinstance(head, Symbol) and head.name == "quote":
        return form
    if isinstance(head, Symbol) and head.name in ("lambda", "define", "let", "let*", "letrec",
                                                     "let-syntax", "letrec-syntax", "define-syntax"):
        # Don't expand inside these forms' binding lists — only in bodies
        return form  # Special forms handle their own expansion during eval
    # For other forms, recurse into arguments
    new_items = []
    node = form.cdr
    while isinstance(node, Pair):
        new_items.append(expand_macros(node.car, env, interp))
        node = node.cdr
    new_cdr = node  # tail (Nil or improper)
    result = new_cdr
    for item in reversed(new_items):
        result = Pair(item, result)
    return Pair(head, result)


# ---------------------------------------------------------------------------
# pattern matching

def _match_pattern(pattern, form, literals: list, bindings: dict, depth: int = 0) -> bool:
    """Match *pattern* against *form*, collecting bindings.

    Returns True if match succeeds, False otherwise.
    Bindings maps pattern variables to their matched forms.
    Ellipsis patterns produce lists under a special key.
    """
    # Pattern variable: any symbol not in literals and not '...' and not '_'
    if isinstance(pattern, Symbol):
        if pattern.name == "_":
            return True
        if pattern.name == "...":
            return False  # shouldn't reach here directly
        if pattern.name in literals:
            # Literal: must match exactly
            if isinstance(form, Symbol) and form.name == pattern.name:
                return True
            return False
        # Pattern variable
        bindings[pattern.name] = form
        return True

    # Ellipsis check: pattern is (P ... . rest)
    if isinstance(pattern, Pair):
        # Check for ellipsis after first element
        if isinstance(pattern.cdr, Pair) and isinstance(pattern.cdr.car, Symbol) and pattern.cdr.car.name == "...":
            # (P ... . rest) — match P zero or more times, then rest
            sub_pattern = pattern.car
            rest_pattern = pattern.cdr.cdr
            # Collect forms for ellipsis matching
            form_items = []
            node = form
            while isinstance(node, Pair):
                form_items.append(node.car)
                node = node.cdr
            form_tail = node
            # We need to figure out how many elements match rest_pattern
            # Count the fixed-length part of rest_pattern
            rest_len = _pattern_fixed_length(rest_pattern)
            # Elements for ellipsis = len(form_items) - rest_len
            ellipsis_count = len(form_items) - rest_len
            if ellipsis_count < 0:
                return False
            ellipsis_items = form_items[:ellipsis_count]
            rest_items = form_items[ellipsis_count:]
            # Collect sub-bindings for each ellipsis match
            sub_bindings_list = []
            for item in ellipsis_items:
                sub_bindings = {}
                if not _match_pattern(sub_pattern, item, literals, sub_bindings):
                    return False
                sub_bindings_list.append(sub_bindings)
            # Store the ellipsis bindings
            _store_ellipsis_bindings(bindings, sub_pattern, sub_bindings_list)
            # Match rest
            rest_form = list_to_pairs(rest_items, form_tail)
            return _match_pattern(rest_pattern, rest_form, literals, bindings)

        # Regular pair pattern
        if not isinstance(form, Pair):
            return False
        if not _match_pattern(pattern.car, form.car, literals, bindings):
            return False
        return _match_pattern(pattern.cdr, form.cdr, literals, bindings)

    # Vector pattern
    if isinstance(pattern, Vector):
        if not isinstance(form, Vector):
            return False
        # Simple vector matching (no ellipsis in vectors for now)
        if len(pattern) != len(form):
            return False
        for p, f in zip(pattern.items, form.items):
            if not _match_pattern(p, f, literals, bindings):
                return False
        return True

    # Literal constant
    return _scheme_eqv_pattern(pattern, form)


def _scheme_eqv_pattern(a, b) -> bool:
    if a is b:
        return True
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return type(a) == type(b) and a == b
    if isinstance(a, str) and isinstance(b, str):
        return a == b
    if isinstance(a, Bool) and isinstance(b, Bool):
        return a.value == b.value
    if isinstance(a, Char) and isinstance(b, Char):
        return a.value == b.value
    return False


def _pattern_fixed_length(pattern) -> int:
    """Count the fixed (non-ellipsis) length of a pattern tail."""
    n = 0
    node = pattern
    while isinstance(node, Pair):
        # Check for ellipsis
        if isinstance(node.cdr, Pair) and isinstance(node.cdr.car, Symbol) and node.cdr.car.name == "...":
            # Skip the ellipsis element
            node = node.cdr.cdr
            continue
        n += 1
        node = node.cdr
    return n


def _store_ellipsis_bindings(bindings: dict, sub_pattern, sub_bindings_list: list):
    """Store bindings from ellipsis-matched sub-patterns.

    For each pattern variable in *sub_pattern*, we store a list of the
    values matched across all ellipsis repetitions.  We use a sentinel
    wrapper (``EllipsisBinding``) so that the instantiator can distinguish
    ellipsis-collected bindings from regular ones.
    """
    var_names = _collect_pattern_vars(sub_pattern)
    for name in var_names:
        values = [sb.get(name, Nil) for sb in sub_bindings_list]
        # Store as EllipsisBinding so we can distinguish from plain lists
        existing = bindings.get(name)
        if isinstance(existing, EllipsisBinding):
            # Merge: if the variable was already captured by a previous
            # ellipsis at the same level, extend.
            existing.values.extend(values)
        else:
            bindings[name] = EllipsisBinding(values)


def _collect_pattern_vars(pattern) -> set:
    """Collect all pattern variable names in a pattern (excluding literals and '...')."""
    result = set()
    if isinstance(pattern, Symbol):
        if pattern.name not in ("_", "..."):
            result.add(pattern.name)
    elif isinstance(pattern, Pair):
        result |= _collect_pattern_vars(pattern.car)
        result |= _collect_pattern_vars(pattern.cdr)
    elif isinstance(pattern, Vector):
        for item in pattern.items:
            result |= _collect_pattern_vars(item)
    return result


# ---------------------------------------------------------------------------
# template instantiation

def _instantiate_template(template, bindings: dict, interp) -> Any:
    """Instantiate a macro template using collected bindings."""
    if isinstance(template, Symbol):
        if template.name == "...":
            raise SyntaxError("unexpected ellipsis in template")
        if template.name in bindings:
            val = bindings[template.name]
            # EllipsisBinding means it was captured by `...` and must be
            # used with `...` in the template
            if isinstance(val, EllipsisBinding):
                raise SyntaxError(f"pattern variable {template.name} used without ellipsis")
            return val
        return template

    if isinstance(template, Pair):
        return _instantiate_pair_template(template, bindings, interp)

    if isinstance(template, Vector):
        new_items = []
        for item in template.items:
            _instantiate_into_list(item, bindings, new_items, interp)
        return Vector(new_items)

    return template


def _instantiate_pair_template(template: Pair, bindings: dict, interp) -> Pair:
    """Instantiate a pair template, handling ellipsis."""
    # Check for ellipsis after first element
    if isinstance(template.cdr, Pair) and isinstance(template.cdr.car, Symbol) and template.cdr.car.name == "...":
        # (T ... . rest)
        sub_template = template.car
        rest_template = template.cdr.cdr
        # Find the ellipsis count from bindings
        ellipsis_count = _ellipsis_count(sub_template, bindings)
        # Instantiate sub_template ellipsis_count times
        items = []
        for i in range(ellipsis_count):
            # Create sub-bindings by indexing into the ellipsis lists
            sub_bindings = _index_ellipsis_bindings(sub_template, bindings, i)
            item = _instantiate_template(sub_template, sub_bindings, interp)
            items.append(item)
        # Instantiate rest
        rest = _instantiate_template(rest_template, bindings, interp) if rest_template is not Nil else Nil
        # Build pair chain
        result = rest
        for item in reversed(items):
            result = Pair(item, result)
        return result

    # Regular pair
    car = _instantiate_template(template.car, bindings, interp)
    cdr = _instantiate_template(template.cdr, bindings, interp)
    return Pair(car, cdr)


def _instantiate_into_list(template, bindings, out_list: list, interp):
    """Instantiate template and append results to out_list (for vectors)."""
    if isinstance(template, Pair) and isinstance(template.cdr, Pair) and isinstance(template.cdr.car, Symbol) and template.cdr.car.name == "...":
        sub_template = template.car
        rest_template = template.cdr.cdr
        ellipsis_count = _ellipsis_count(sub_template, bindings)
        for i in range(ellipsis_count):
            sub_bindings = _index_ellipsis_bindings(sub_template, bindings, i)
            _instantiate_into_list(sub_template, sub_bindings, out_list, interp)
        if rest_template is not Nil:
            _instantiate_into_list(rest_template, bindings, out_list, interp)
    else:
        out_list.append(_instantiate_template(template, bindings, interp))


def _ellipsis_count(template, bindings: dict) -> int:
    """Determine how many times to repeat an ellipsis sub-template."""
    var_names = _collect_pattern_vars(template)
    counts = []
    for name in var_names:
        if name in bindings and isinstance(bindings[name], EllipsisBinding):
            counts.append(len(bindings[name].values))
    if not counts:
        return 0
    return max(counts)


def _index_ellipsis_bindings(template, bindings: dict, index: int) -> dict:
    """Create a sub-bindings dict by indexing into ellipsis-collected bindings."""
    result = {}
    var_names = _collect_pattern_vars(template)
    for name in var_names:
        if name in bindings:
            if isinstance(bindings[name], EllipsisBinding):
                # Ellipsis-collected: index into the values list
                if index < len(bindings[name].values):
                    result[name] = bindings[name].values[index]
                else:
                    result[name] = Nil
            else:
                result[name] = bindings[name]
    return result


# ---------------------------------------------------------------------------
# main expansion

def _expand_one(macro: Macro, form: Pair, env: Environment, interp) -> Any:
    """Expand a single macro invocation."""
    for pattern, template in macro.rules:
        # The pattern is (macro-name . args), form is (macro-name . args)
        # Match form against pattern (skipping the macro name itself)
        bindings = {}
        # Match the cdr (arguments) against pattern's cdr
        if _match_pattern(pattern.cdr, form.cdr, macro.literals, bindings):
            result = _instantiate_template(template, bindings, interp)
            return result
    # No rule matched
    raise SyntaxError(f"no matching syntax-rules clause for: {form}")


def _flatten_bindings(bindings: dict) -> dict:
    """Flatten ellipsis bindings so they're directly usable by the instantiator."""
    result = {}
    for key, val in bindings.items():
        if isinstance(val, list) and len(val) > 0 and isinstance(val[0], list):
            # Ellipsis-collected: store the list of lists directly
            result[key] = val
        else:
            result[key] = val
    return result


def list_to_pairs(lst: list, tail=None):
    """Convert a Python list to a Scheme list."""
    from .types import Pair, Nil
    result = tail if tail is not None else Nil
    for item in reversed(lst):
        result = Pair(item, result)
    return result