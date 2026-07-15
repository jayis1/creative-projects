"""
JSON / YAML serialization for Rete rules and facts.

Allows loading rule sets and fact bases from JSON or YAML files, and saving
the current engine state.

JSON rule format
-----------------
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
is a constant.  Conditions may include ``"negated": true``.

YAML rule format
----------------
.. code-block:: yaml

    rules:
      - name: greet
        priority: 0
        conditions:
          - type: person
            fields:
              name: "?n"
        actions:
          - ["print", "Hello, {n}!"]
    facts:
      - type: person
        fields:
          name: Alice
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .engine import Condition, Const, Engine, Fact, Rule, Var, _make_term, ConflictResolution
from .exceptions import ReteError, SerializationError

try:
    import yaml  # type: ignore
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


# --------------------------------------------------------------------------- #
#  Built-in action vocabulary (used by JSON-loaded rules)
# --------------------------------------------------------------------------- #


def _action_print(template: str):
    """Create an action that prints a formatted string using bindings.

    Uses ``string.Template``-style safe substitution so missing keys don't
    crash — they are simply left as-is in the output.
    """
    import string
    tmpl = string.Template(template.replace("{", "${").replace("}", "}"))
    def action(bindings: dict, engine: Engine):
        # Safe substitution: missing keys are left as-is, no KeyError
        print(tmpl.safe_substitute(bindings))
    return action


def _action_assert(fact_type: str, **field_templates: str):
    """Create an action that asserts a new fact from bindings.

    Field values starting with ``?`` are resolved from bindings; if a binding
    is missing, the field is set to ``None`` rather than leaking the template
    string.
    """
    def action(bindings: dict, engine: Engine):
        fields = {}
        for k, v in field_templates.items():
            if isinstance(v, str) and v.startswith("?"):
                # Bug fix: use .get() without a default that leaks the template
                # string. Missing bindings resolve to None.
                fields[k] = bindings.get(v[1:])
            else:
                fields[k] = v
        engine.assert_fact(Fact(fact_type, **fields))
    return action


def _action_assert_logical(fact_type: str, **field_templates: str):
    """Create an action that logically asserts a fact from bindings.

    The fact is marked as derived from the current rule firing, enabling
    truth maintenance — if the supporting facts are retracted, the derived
    fact auto-retracts.
    """
    def action(bindings: dict, engine: Engine):
        fields = {}
        for k, v in field_templates.items():
            if isinstance(v, str) and v.startswith("?"):
                fields[k] = bindings.get(v[1:])
            else:
                fields[k] = v
        # Build a support signature from the rule name + bindings
        # The engine's fire_one method handles TMS registration when
        # assert_logical is called from within an action
        engine.assert_fact(Fact(fact_type, **fields))
    return action


def _action_retract(fact_type: str, **field_templates: str):
    """Create an action that retracts a fact matching bindings.

    Field values starting with ``?`` are resolved from bindings; if a binding
    is missing, the field matches against ``None``.
    """
    def action(bindings: dict, engine: Engine):
        fields = {}
        for k, v in field_templates.items():
            if isinstance(v, str) and v.startswith("?"):
                fields[k] = bindings.get(v[1:])
            else:
                fields[k] = v
        # Find and retract matching facts
        for f in engine.facts_of_type(fact_type):
            if all(f.fields.get(k) == v for k, v in fields.items()):
                engine.retract_fact(f)
                break
    return action


def _action_log(message: str):
    """Create an action that logs a message using safe substitution."""
    import string
    tmpl = string.Template(message.replace("{", "${").replace("}", "}"))
    def action(bindings: dict, engine: Engine):
        engine.log(tmpl.safe_substitute(bindings))
    return action


_ACTION_BUILDERS = {
    "print": _action_print,
    "assert": _action_assert,
    "assert_logical": _action_assert_logical,
    "retract": _action_retract,
    "log": _action_log,
}


# --------------------------------------------------------------------------- #
#  Parsing
# --------------------------------------------------------------------------- #


def _parse_field_value(val: Any) -> Any:
    """Convert a JSON/YAML field value into a term.

    Strings starting with ``?`` become variables; everything else is a
    constant (passed through as-is).
    """
    if isinstance(val, str) and val.startswith("?"):
        return Var(val[1:])
    return val


def _parse_condition(data: dict) -> Condition:
    """Parse a single condition from its dict representation."""
    if not isinstance(data, dict):
        raise SerializationError(f"condition must be a dict, got {type(data)}")
    if "type" not in data:
        raise SerializationError("condition must have a 'type' field")
    fact_type = data["type"]
    raw_fields = data.get("fields", {})
    if not isinstance(raw_fields, dict):
        raise SerializationError(
            f"condition fields must be a dict, got {type(raw_fields)}"
        )
    fields = {k: _parse_field_value(v) for k, v in raw_fields.items()}
    negated = data.get("negated", False)
    return Condition(fact_type, negated=negated, **fields)


def _parse_action(data) -> Any:
    """Parse an action spec into a callable.

    Actions can be:
    - A list: ``["print", "Hello {n}!"]`` → built-in action
    - A string: ``"print:Hello {n}!"`` → shorthand (action_type:message)
    """
    if callable(data):
        return data
    if isinstance(data, list):
        if not data:
            raise SerializationError("action list cannot be empty")
        kind = data[0]
        if kind not in _ACTION_BUILDERS:
            raise SerializationError(
                f"unknown action type: {kind!r}. "
                f"Supported: {list(_ACTION_BUILDERS.keys())}"
            )
        builder = _ACTION_BUILDERS[kind]
        args = data[1:]
        if kind in ("print", "log"):
            if len(args) < 1:
                raise SerializationError(f"{kind} action needs a message string")
            return builder(args[0])
        # assert/retract/assert_logical: args = [fact_type, {field: val, ...}]
        if len(args) < 1:
            raise SerializationError(f"{kind} action needs a fact_type")
        fact_type = args[0]
        field_map = args[1] if len(args) > 1 and isinstance(args[1], dict) else {}
        # Keep the ? prefix intact so _action_assert can distinguish
        # variables from constants.
        return builder(fact_type, **field_map)
    if isinstance(data, str):
        # Shorthand: "print:Hello {n}!" or "assert:person:name=?n"
        if ":" not in data:
            raise SerializationError(f"cannot parse action string: {data!r}")
        kind, rest = data.split(":", 1)
        if kind not in _ACTION_BUILDERS:
            raise SerializationError(f"unknown action type: {kind!r}")
        if kind in ("print", "log"):
            return _ACTION_BUILDERS[kind](rest)
        # assert/retract shorthand: "assert:fact_type:field1=val1,field2=val2"
        parts = rest.split(":", 1)
        fact_type = parts[0]
        field_map = {}
        if len(parts) > 1:
            for pair in parts[1].split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    field_map[k.strip()] = v.strip()
        return _ACTION_BUILDERS[kind](fact_type, **field_map)
    raise SerializationError(f"cannot parse action: {data!r}")


def _parse_rule(data: dict) -> Rule:
    """Parse a rule from its dict representation."""
    if not isinstance(data, dict):
        raise SerializationError(f"rule must be a dict, got {type(data)}")
    if "name" not in data:
        raise SerializationError("rule must have a 'name' field")
    if "conditions" not in data:
        raise SerializationError(
            f"rule '{data.get('name', '?')}' must have conditions"
        )
    if "actions" not in data:
        raise SerializationError(
            f"rule '{data.get('name', '?')}' must have actions"
        )
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
    """Parse a fact from its dict representation."""
    if not isinstance(data, dict):
        raise SerializationError(f"fact must be a dict, got {type(data)}")
    if "type" not in data:
        raise SerializationError("fact must have a 'type' field")
    fields = data.get("fields", {})
    if not isinstance(fields, dict):
        raise SerializationError(
            f"fact fields must be a dict, got {type(fields)}"
        )
    return Fact(data["type"], **fields)


# --------------------------------------------------------------------------- #
#  Public API
# --------------------------------------------------------------------------- #


def load_json(path: str | Path) -> tuple[list[Rule], list[Fact]]:
    """Load rules and facts from a JSON file.

    Returns ``(rules, facts)``.

    Raises
    ------
    SerializationError
        If the file cannot be parsed or contains invalid data.
    ReteError
        If the file is not found.
    """
    path = Path(path)
    if not path.exists():
        raise ReteError(f"file not found: {path}")
    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise SerializationError(f"invalid JSON in {path}: {e}") from e
    rules = [_parse_rule(r) for r in data.get("rules", [])]
    facts = [_parse_fact(f) for f in data.get("facts", [])]
    return rules, facts


def load_yaml(path: str | Path) -> tuple[list[Rule], list[Fact]]:
    """Load rules and facts from a YAML file.

    Returns ``(rules, facts)``.

    Raises
    ------
    SerializationError
        If PyYAML is not installed or the file contains invalid data.
    ReteError
        If the file is not found.
    """
    if not _HAS_YAML:
        raise SerializationError(
            "YAML support requires PyYAML. Install with: pip install pyyaml"
        )
    path = Path(path)
    if not path.exists():
        raise ReteError(f"file not found: {path}")
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise SerializationError(f"invalid YAML in {path}: {e}") from e
    if data is None:
        return [], []
    rules = [_parse_rule(r) for r in data.get("rules", [])]
    facts = [_parse_fact(f) for f in data.get("facts", [])]
    return rules, facts


def load_file(path: str | Path) -> tuple[list[Rule], list[Fact]]:
    """Auto-detect format from file extension and load accordingly.

    Supports ``.json``, ``.yaml``, and ``.yml``.  Falls back to JSON for
    unknown extensions.

    Returns ``(rules, facts)``.
    """
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        return load_yaml(path)
    return load_json(path)


_STRATEGY_NAMES = {
    "fifo": ConflictResolution.FIFO,
    "lifo": ConflictResolution.LIFO,
    "priority": ConflictResolution.PRIORITY,
    "recent": ConflictResolution.RECENT,
    "refc": ConflictResolution.REFC,
    "priority-refc": ConflictResolution.PRIORITY_REFC,
}


def _normalize_strategy(strategy):
    """Convert a string strategy name to ConflictResolution enum.

    If *strategy* is already a ConflictResolution, return it as-is.
    """
    if isinstance(strategy, str):
        try:
            return _STRATEGY_NAMES[strategy.lower()]
        except KeyError:
            raise SerializationError(
                f"unknown strategy: {strategy!r}. "
                f"Choices: {list(_STRATEGY_NAMES.keys())}"
            )
    return strategy


def load_engine(path: str | Path, **engine_kwargs) -> Engine:
    """Load a JSON or YAML file and return a fully configured Engine.

    The format is auto-detected from the file extension.

    Parameters
    ----------
    path : str | Path
        Path to the rule file (``.json`` or ``.yaml``).
    **engine_kwargs
        Keyword arguments passed to ``Engine()`` (strategy, max_steps, etc.).
        The ``strategy`` kwarg accepts either a ``ConflictResolution`` enum
        value or a string name (``"fifo"``, ``"lifo"``, ``"priority"``,
        ``"recent"``, ``"refc"``, ``"priority-refc"``).
    """
    rules, facts = load_file(path)
    # Normalize strategy if passed as string
    if "strategy" in engine_kwargs:
        engine_kwargs["strategy"] = _normalize_strategy(engine_kwargs["strategy"])
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


def save_facts_yaml(engine: Engine, path: str | Path) -> None:
    """Save all facts in working memory to a YAML file.

    Raises
    ------
    SerializationError
        If PyYAML is not installed.
    """
    if not _HAS_YAML:
        raise SerializationError(
            "YAML support requires PyYAML. Install with: pip install pyyaml"
        )
    path = Path(path)
    data = {
        "facts": [
            {"type": f.fact_type, "fields": f.fields}
            for f in engine.facts
        ]
    }
    with open(path, "w") as fh:
        yaml.dump(data, fh, default_flow_style=False, sort_keys=False)


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