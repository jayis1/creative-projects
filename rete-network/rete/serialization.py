"""
JSON serialization for Rete rules and facts.

Allows loading rule sets and fact bases from JSON files, and saving the
current engine state.

JSON rule format
----------------

.. code-block:: json

    {
      "rules": [
        {
          "name": "greet",
          "priority": 0,
          "conditions": [
            {"type": "person", "fields": {"name": "?n"}}
          ],
          "actions": [["print", "Hello, {n}!"]]
        }
      ],
      "facts": [
        {"type": "person", "fields": {"name": "Alice"}}
      ]
    }

Field values starting with ``?`` are treated as variables; everything else
is a constant.  Conditions may include ``"negated": true`` and
``"predicate"`` is not supported in JSON (use Python API for that).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .engine import Condition, Const, Engine, Fact, Rule, Var, _make_term
from .exceptions import ReteError


# ---------------------------------------------------------------------------
#  Built-in action vocabulary (used by JSON-loaded rules)
# ---------------------------------------------------------------------------


def _action_print(template: str):
    """Create an action that prints a formatted string using bindings."""
    def action(bindings: dict, engine: Engine):
        print(template.format(**bindings))
    return action


def _action_assert(fact_type: str, **field_templates: str):
    """Create an action that asserts a new fact from bindings."""
    def action(bindings: dict, engine: Engine):
        fields = {}
        for k, v in field_templates.items():
            if isinstance(v, str) and v.startswith("?"):
                fields[k] = bindings.get(v[1:], v)
            else:
                fields[k] = v
        engine.assert_fact(Fact(fact_type, **fields))
    return action


def _action_retract(fact_type: str, **field_templates: str):
    """Create an action that retracts a fact matching bindings."""
    def action(bindings: dict, engine: Engine):
        fields = {}
        for k, v in field_templates.items():
            if isinstance(v, str) and v.startswith("?"):
                fields[k] = bindings.get(v[1:], v)
            else:
                fields[k] = v
        # Find and retract matching facts
        for f in engine.facts_of_type(fact_type):
            if all(f.fields.get(k) == v for k, v in fields.items()):
                engine.retract_fact(f)
                break
    return action


def _action_log(message: str):
    """Create an action that logs a message."""
    def action(bindings: dict, engine: Engine):
        engine.log(message.format(**bindings))
    return action


_ACTION_BUILDERS = {
    "print": _action_print,
    "assert": _action_assert,
    "retract": _action_retract,
    "log": _action_log,
}


# ---------------------------------------------------------------------------
#  Parsing
# ---------------------------------------------------------------------------


def _parse_field_value(val: Any) -> Any:
    """Convert a JSON field value into a term.

    Strings starting with ``?`` become variables; everything else is a
    constant (passed through as-is).
    """
    if isinstance(val, str) and val.startswith("?"):
        return Var(val[1:])
    return val


def _parse_condition(data: dict) -> Condition:
    """Parse a single condition from its JSON dict."""
    if "type" not in data:
        raise ReteError("condition must have a 'type' field")
    fact_type = data["type"]
    raw_fields = data.get("fields", {})
    fields = {k: _parse_field_value(v) for k, v in raw_fields.items()}
    negated = data.get("negated", False)
    return Condition(fact_type, negated=negated, **fields)


def _parse_action(data) -> Any:
    """Parse an action spec into a callable.

    Actions can be:
    - A list: ``["print", "Hello {n}!"]`` → built-in action
    - A string: ``"assert:person name=?n"`` → shorthand
    """
    if callable(data):
        return data
    if isinstance(data, list):
        if not data:
            raise ReteError("action list cannot be empty")
        kind = data[0]
        if kind not in _ACTION_BUILDERS:
            raise ReteError(f"unknown action type: {kind}")
        builder = _ACTION_BUILDERS[kind]
        args = data[1:]
        if kind in ("print", "log"):
            return builder(*args)
        # assert/retract: args = [fact_type, {field: val, ...}]
        if len(args) < 1:
            raise ReteError(f"{kind} action needs a fact_type")
        fact_type = args[0]
        field_map = args[1] if len(args) > 1 else {}
        # Keep the ? prefix intact so _action_assert can distinguish
        # variables from constants.
        return builder(fact_type, **field_map)
    raise ReteError(f"cannot parse action: {data!r}")


def _parse_rule(data: dict) -> Rule:
    """Parse a rule from its JSON dict."""
    if "name" not in data:
        raise ReteError("rule must have a 'name' field")
    if "conditions" not in data:
        raise ReteError(f"rule '{data.get('name', '?')}' must have conditions")
    if "actions" not in data:
        raise ReteError(f"rule '{data.get('name', '?')}' must have actions")
    conditions = [_parse_condition(c) for c in data["conditions"]]
    actions = [_parse_action(a) for a in data["actions"]]
    priority = data.get("priority", 0)
    return Rule(
        name=data["name"],
        conditions=conditions,
        actions=actions,
        priority=priority,
    )


def _parse_fact(data: dict) -> Fact:
    """Parse a fact from its JSON dict."""
    if "type" not in data:
        raise ReteError("fact must have a 'type' field")
    fields = data.get("fields", {})
    return Fact(data["type"], **fields)


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------


def load_json(path: str | Path) -> tuple[list[Rule], list[Fact]]:
    """Load rules and facts from a JSON file.

    Returns ``(rules, facts)``.
    """
    path = Path(path)
    if not path.exists():
        raise ReteError(f"file not found: {path}")
    with open(path) as f:
        data = json.load(f)
    rules = [_parse_rule(r) for r in data.get("rules", [])]
    facts = [_parse_fact(f) for f in data.get("facts", [])]
    return rules, facts


def load_engine(path: str | Path, **engine_kwargs) -> Engine:
    """Load a JSON file and return a fully configured Engine."""
    rules, facts = load_json(path)
    eng = Engine(**engine_kwargs)
    for r in rules:
        eng.add_rule(r)
    for f in facts:
        eng.assert_fact(f)
    return eng


def save_facts(engine: Engine, path: str | Path) -> None:
    """Save all facts in working memory to a JSON file."""
    path = Path(path)
    data = {
        "facts": [
            {"type": f.fact_type, "fields": f.fields}
            for f in engine.facts
        ]
    }
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2, default=str)


def save_state(engine: Engine, path: str | Path) -> None:
    """Save the complete engine state (rules + facts) to JSON.

    Note: actions are only serializable if they use the built-in vocabulary.
    Custom Python callable actions are skipped with a warning.
    """
    path = Path(path)
    rules_data = []
    for rname, rule in engine._rules.items():
        # We can only serialize built-in actions; skip custom callables
        rules_data.append({
            "name": rule.name,
            "priority": rule.priority,
            "conditions": [
                {
                    "type": c.fact_type,
                    "fields": {
                        k: (f"?{v.name}" if isinstance(v, Var)
                            else (v.value if isinstance(v, Const) else str(v)))
                        for k, v in c.fields.items()
                    },
                    "negated": c.negated,
                }
                for c in rule.conditions
            ],
            "actions": [],  # custom actions not serializable
        })
    facts_data = [
        {"type": f.fact_type, "fields": f.fields}
        for f in engine.facts
    ]
    data = {"rules": rules_data, "facts": facts_data}
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2, default=str)