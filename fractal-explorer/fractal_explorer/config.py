"""Configuration file loading and CLI/config merging."""
from __future__ import annotations

import json
from typing import Optional, Set


def _load_config(path: str):
    """Load a JSON / YAML / TOML config file into a dict."""
    with open(path) as f:
        text = f.read()
    if path.endswith(".json"):
        return json.loads(text)
    if path.endswith(".toml"):
        try:
            import tomllib  # py3.11+
            return tomllib.loads(text)
        except Exception:
            try:
                import tomli
                return tomli.loads(text)
            except Exception:
                raise RuntimeError(
                    "TOML config requires Python 3.11+ or tomli")
    if path.endswith((".yaml", ".yml")):
        try:
            import yaml
            return yaml.safe_load(text)
        except Exception:
            raise RuntimeError("YAML config requires PyYAML")
    return json.loads(text)


def _merge_config(args, cfg: dict, explicit: Optional[Set[str]] = None):
    """Merge config-dict values into an argparse Namespace.

    Config values fill in attributes that the user did *not* explicitly pass
    on the command line. ``explicit`` is the set of attribute names that were
    explicitly provided via CLI flags; these are never overridden.
    """
    explicit = explicit or set()
    for k, v in cfg.items():
        ak = k.replace("-", "_")
        if hasattr(args, ak) and ak not in explicit:
            setattr(args, ak, v)
    return args


def _detect_explicit_args(parser, argv):
    """Return the set of dest names the user explicitly passed on the CLI."""
    explicit: Set[str] = set()
    all_option_strings = []

    def _walk(p):
        for action in p._actions:
            all_option_strings.append((action.option_strings, action.dest))
            if hasattr(action, "choices") and isinstance(action.choices, dict):
                for sub in action.choices.values():
                    _walk(sub)

    _walk(parser)

    for opt_strings, dest in all_option_strings:
        for opt in opt_strings:
            if opt in argv:
                explicit.add(dest)
                break
    return explicit