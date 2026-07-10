"""
Configuration support for the spreadsheet engine.

Loads workbook configurations from YAML or JSON files to set up sheets,
named ranges, initial cell values, and engine options.

Example YAML config:

    sheets:
      - name: Budget
        cells:
          A1: "5000"
          A2: "=A1*0.3"
      - name: Summary
        cells:
          B1: "=Budget!A1+Budget!A2"

    named_ranges:
      Revenue: "Budget!A1"
      TaxRate: "Budget!A2"

    options:
      max_rows: 1048576
      max_cols: 16384
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from .engine import Engine
from .sheet import Sheet


class ConfigError(Exception):
    """Raised when configuration loading or validation fails."""


def load_config(path: str, engine: Optional[Engine] = None) -> Engine:
    """Load a configuration file and apply it to an Engine.

    Supports YAML (.yaml/.yml) and JSON (.json) files based on extension.
    If *engine* is None, a new Engine is created.

    Returns the configured engine (after recalculation).
    """
    if not os.path.isfile(path):
        raise ConfigError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    ext = os.path.splitext(path)[1].lower()
    if ext in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as exc:
            raise ConfigError("PyYAML is required for YAML config files") from exc
        data = yaml.safe_load(text)
    elif ext == ".json":
        data = json.loads(text)
    else:
        # Try to auto-detect
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            try:
                import yaml
                data = yaml.safe_load(text)
            except ImportError:
                raise ConfigError(f"Cannot parse config file: {path}")

    return apply_config(data, engine)


def apply_config(data: Dict[str, Any], engine: Optional[Engine] = None) -> Engine:
    """Apply a configuration dictionary to an Engine."""
    if not isinstance(data, dict):
        raise ConfigError("Config must be a mapping/object")

    if engine is None:
        engine = Engine()

    # --- Sheets ---
    for sheet_def in data.get("sheets", []):
        if not isinstance(sheet_def, dict):
            raise ConfigError("Each sheet definition must be a mapping")
        name = sheet_def.get("name")
        if not name:
            raise ConfigError("Sheet definition missing 'name'")
        if name not in engine.sheets:
            engine.add_sheet(name)

        cells = sheet_def.get("cells", {})
        if not isinstance(cells, dict):
            raise ConfigError(f"Sheet '{name}' cells must be a mapping")
        for ref, value in cells.items():
            engine.set(name, ref, str(value))

    # --- Named ranges ---
    for nr_name, nr_ref in data.get("named_ranges", {}).items():
        if "!" in nr_ref:
            sheet, ref = nr_ref.split("!", 1)
        else:
            # Use the first sheet as default
            sheet = engine.sheet_names()[0] if engine.sheet_names() else "Sheet1"
            ref = nr_ref
        engine.define_name(nr_name, sheet, ref)

    # --- Options ---
    options = data.get("options", {})
    if isinstance(options, dict):
        if options.get("auto_recalc", True):
            engine.recalculate()

    return engine


def save_config(engine: Engine, path: str) -> None:
    """Save the current engine state as a JSON configuration file."""
    data: Dict[str, Any] = {"sheets": [], "named_ranges": {}, "options": {}}

    for name in engine.sheet_names():
        sheet: Sheet = engine.get_sheet(name)
        cells = {}
        for cell in sheet.non_empty_cells():
            cells[cell.ref] = cell.raw
        data["sheets"].append({"name": name, "cells": cells})

    for nr_name, nr in engine.list_names().items():
        from .cell import format_a1
        ref = f"{nr.sheet}!{format_a1(nr.start_row, nr.start_col)}"
        if nr.is_range:
            ref += f":{format_a1(nr.end_row, nr.end_col)}"
        data["named_ranges"][nr_name] = ref

    data["options"]["auto_recalc"] = False

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)