"""
Enhanced CLI for the spreadsheet engine.

Adds:
  - Interactive REPL mode
  - Configuration file support (--config / load / save)
  - Logging with --verbose / --quiet
  - Function listing (--functions)
  - Audit subcommand
  - Batch import from CSV with auto-sheet-creation
  - Named range management
  - Sheet operations (add, list, copy, clear)
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
from typing import List, Optional

from .engine import Engine, EngineError
from .sheet import _format_value
from .cell import CellError, ErrorType
from .config import load_config, save_config, ConfigError
from .logging_utils import configure as configure_logging
from .optimizer import batch_set, CachedEngine


def cmd_set(engine: Engine, args) -> int:
    engine.set(args.sheet, args.ref, args.value)
    engine.recalculate()
    val = engine.get(args.sheet, args.ref)
    print(f"Set {args.sheet}!{args.ref} = {args.value}")
    if args.verbose:
        print(f"  Computed value: {_format_value(val)}")
    return 0


def cmd_get(engine: Engine, args) -> int:
    val = engine.get(args.sheet, args.ref)
    if val is None:
        print("(empty)")
    elif isinstance(val, CellError):
        print(str(val))
    else:
        print(_format_value(val))
    return 0


def cmd_recalc(engine: Engine, args) -> int:
    stats = engine.recalculate()
    print(f"Recalculated: {stats['evaluated']} cells, "
          f"{stats['errors']} errors, {stats['cycles']} cycles")
    return 0


def cmd_display(engine: Engine, args) -> int:
    print(engine.display(args.sheet, args.max_rows, args.max_cols))
    return 0


def cmd_csv_export(engine: Engine, args) -> int:
    text = engine.export_csv(args.sheet)
    if args.output:
        with open(args.output, "w", newline="") as f:
            f.write(text)
        print(f"Exported to {args.output}")
    else:
        print(text, end="")
    return 0


def cmd_csv_import(engine: Engine, args) -> int:
    with open(args.file) as f:
        text = f.read()
    engine.import_csv(args.sheet, text)
    engine.recalculate()
    print(f"Imported CSV into {args.sheet}")
    if args.verbose:
        print(engine.display(args.sheet))
    return 0


def cmd_json_save(engine: Engine, args) -> int:
    data = engine.to_dict()
    with open(args.output, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved to {args.output}")
    return 0


def cmd_json_load(engine: Engine, args) -> int:
    with open(args.file) as f:
        data = json.load(f)
    engine.from_dict(data)
    engine.recalculate()
    print(f"Loaded from {args.file}")
    return 0


def cmd_eval(engine: Engine, args) -> int:
    """Evaluate a formula expression and print the result."""
    sheet = engine.get_sheet(args.sheet)
    row, col = 1048575, 16383  # last cell as scratch
    sheet.set(row, col, "=" + args.formula)
    engine.recalculate()
    val = sheet.get(row, col)
    sheet.set(row, col, "")
    if isinstance(val, CellError):
        print(str(val), file=sys.stderr)
        return 1
    print(_format_value(val))
    return 0


def cmd_run(engine: Engine, args) -> int:
    """Run a script file with commands: set, addsheet, name, display."""
    with open(args.file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 3)
            cmd = parts[0].lower()
            if cmd == "addsheet" and len(parts) >= 2:
                if parts[1] not in engine.sheets:
                    engine.add_sheet(parts[1])
            elif cmd == "set" and len(parts) >= 4:
                engine.set(parts[1], parts[2], parts[3])
            elif cmd == "set" and len(parts) == 3:
                engine.set(parts[1], parts[2], "")
            elif cmd == "name" and len(parts) >= 4:
                # name NAME SHEET REF
                engine.define_name(parts[1], parts[2], parts[3])
            elif cmd == "display" and len(parts) >= 2:
                print(engine.display(parts[1]))
    engine.recalculate()
    for name in engine.sheet_names():
        print(f"\n=== {name} ===")
        print(engine.display(name))
    return 0


def cmd_functions(engine: Engine, args) -> int:
    """List all available built-in functions."""
    from .functions import FUNCTIONS
    funcs = sorted(FUNCTIONS.keys())
    print(f"Available functions ({len(funcs)}):")
    for i, name in enumerate(funcs):
        if (i % 4) == 0:
            print()
        print(f"  {name:<16s}", end="")
    print()
    return 0


def cmd_audit(engine: Engine, args) -> int:
    """Audit a cell: show formula, value, precedents, and dependents."""
    audit = engine.audit_cell(args.sheet, args.ref)
    if audit.get("status") == "empty":
        print(f"Cell {args.sheet}!{args.ref} is empty")
        return 0
    print(f"Cell:  {args.sheet}!{args.ref}")
    print(f"Raw:   {audit.get('raw', '')}")
    print(f"Value: {audit.get('value', '')}")
    print(f"Type:  {audit.get('type', '')}")
    precs = audit.get("precedents", [])
    deps = audit.get("dependents", [])
    print(f"Precedents ({len(precs)}):")
    for p in precs:
        print(f"  {p['sheet']}!{p['ref']}")
    print(f"Dependents ({len(deps)}):")
    for d in deps:
        print(f"  {d['sheet']}!{d['ref']}")
    return 0


def cmd_load_config(engine: Engine, args) -> int:
    """Load configuration from a YAML/JSON file."""
    try:
        load_config(args.file, engine)
        print(f"Loaded configuration from {args.file}")
        return 0
    except ConfigError as e:
        print(f"Config error: {e}", file=sys.stderr)
        return 1


def cmd_save_config(engine: Engine, args) -> int:
    """Save current state to a JSON config file."""
    save_config(engine, args.output)
    print(f"Saved configuration to {args.output}")
    return 0


def cmd_add_sheet(engine: Engine, args) -> int:
    engine.add_sheet(args.name)
    print(f"Added sheet: {args.name}")
    return 0


def cmd_list_sheets(engine: Engine, args) -> int:
    names = engine.sheet_names()
    if not names:
        print("(no sheets)")
    else:
        for name in names:
            sheet = engine.get_sheet(name)
            cell_count = len(sheet.non_empty_cells())
            print(f"  {name}: {cell_count} non-empty cells")
    return 0


def cmd_copy_sheet(engine: Engine, args) -> int:
    engine.copy_sheet(args.source, args.dest)
    print(f"Copied {args.source} -> {args.dest}")
    return 0


def cmd_clear_sheet(engine: Engine, args) -> int:
    engine.clear_sheet(args.name)
    print(f"Cleared sheet: {args.name}")
    return 0


def cmd_name(engine: Engine, args) -> int:
    """Define or list named ranges."""
    if args.action == "define":
        if not args.ref:
            print("Error: --ref required for define", file=sys.stderr)
            return 1
        engine.define_name(args.name, args.sheet, args.ref)
        print(f"Defined named range: {args.name} = {args.sheet}!{args.ref}")
    elif args.action == "list":
        names = engine.list_names()
        if not names:
            print("(no named ranges)")
        else:
            for name, nr in names.items():
                print(f"  {name}: {nr}")
    elif args.action == "get":
        nr = engine.get_name(args.name)
        if nr is None:
            print(f"Named range '{args.name}' not found", file=sys.stderr)
            return 1
        print(f"{nr}")
    return 0


def cmd_interactive(engine: Engine, args) -> int:
    """Interactive REPL mode."""
    print("Spreadsheet Engine REPL — type 'help' for commands, 'quit' to exit")
    while True:
        try:
            line = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line.lower() in ("quit", "exit", "q"):
            break
        if line.lower() == "help":
            print("Commands:")
            print("  set SHEET REF VALUE    Set a cell")
            print("  get SHEET REF          Get a cell value")
            print("  recalc                 Recalculate all")
            print("  display SHEET          Show sheet grid")
            print("  sheets                 List sheets")
            print("  functions              List available functions")
            print("  audit SHEET REF        Audit a cell")
            print("  quit                   Exit REPL")
            continue

        parts = line.split()
        cmd = parts[0].lower()
        try:
            if cmd == "set" and len(parts) >= 4:
                engine.set(parts[1], parts[2], " ".join(parts[3:]))
                engine.recalculate()
                val = engine.get(parts[1], parts[2])
                print(f"  => {_format_value(val)}")
            elif cmd == "get" and len(parts) >= 3:
                val = engine.get(parts[1], parts[2])
                print(f"  {_format_value(val)}" if val is not None else "  (empty)")
            elif cmd == "recalc":
                stats = engine.recalculate()
                print(f"  {stats['evaluated']} cells, {stats['errors']} errors, {stats['cycles']} cycles")
            elif cmd == "display" and len(parts) >= 2:
                print(engine.display(parts[1]))
            elif cmd == "sheets":
                for name in engine.sheet_names():
                    print(f"  {name}")
            elif cmd == "functions":
                from .functions import FUNCTIONS
                print(f"  {len(FUNCTIONS)} functions: {', '.join(sorted(FUNCTIONS.keys())[:20])}...")
            elif cmd == "audit" and len(parts) >= 3:
                audit = engine.audit_cell(parts[1], parts[2])
                for k, v in audit.items():
                    print(f"  {k}: {v}")
            else:
                print(f"  Unknown command or wrong args: {line}")
        except Exception as e:
            print(f"  Error: {e}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="spreadsheet",
        description="From-scratch spreadsheet formula engine",
        epilog="Use 'spreadsheet interactive' for a REPL session.",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    p.add_argument("-q", "--quiet", action="store_true", help="Suppress non-error output")
    sub = p.add_subparsers(dest="command", required=True)

    # set
    sp = sub.add_parser("set", help="Set a cell value")
    sp.add_argument("sheet")
    sp.add_argument("ref", help="Cell reference e.g. A1")
    sp.add_argument("value", help="Cell value or formula (prefix with =)")
    sp.set_defaults(func=cmd_set)

    # get
    sp = sub.add_parser("get", help="Get a cell value")
    sp.add_argument("sheet")
    sp.add_argument("ref")
    sp.set_defaults(func=cmd_get)

    # recalc
    sp = sub.add_parser("recalc", help="Recalculate all sheets")
    sp.set_defaults(func=cmd_recalc)

    # display
    sp = sub.add_parser("display", help="Display a sheet as ASCII grid")
    sp.add_argument("sheet")
    sp.add_argument("--max-rows", type=int, default=20)
    sp.add_argument("--max-cols", type=int, default=10)
    sp.set_defaults(func=cmd_display)

    # csv-export
    sp = sub.add_parser("csv-export", help="Export sheet to CSV")
    sp.add_argument("sheet")
    sp.add_argument("-o", "--output", help="Output file (stdout if omitted)")
    sp.set_defaults(func=cmd_csv_export)

    # csv-import
    sp = sub.add_parser("csv-import", help="Import CSV into a sheet")
    sp.add_argument("sheet")
    sp.add_argument("file")
    sp.set_defaults(func=cmd_csv_import)

    # json-save
    sp = sub.add_parser("json-save", help="Save engine state to JSON")
    sp.add_argument("-o", "--output", required=True)
    sp.set_defaults(func=cmd_json_save)

    # json-load
    sp = sub.add_parser("json-load", help="Load engine state from JSON")
    sp.add_argument("file")
    sp.set_defaults(func=cmd_json_load)

    # eval
    sp = sub.add_parser("eval", help="Evaluate a formula expression")
    sp.add_argument("sheet")
    sp.add_argument("formula", help="Formula without leading =")
    sp.set_defaults(func=cmd_eval)

    # run
    sp = sub.add_parser("run", help="Run a script file")
    sp.add_argument("file")
    sp.set_defaults(func=cmd_run)

    # functions
    sp = sub.add_parser("functions", help="List all available functions")
    sp.set_defaults(func=cmd_functions)

    # audit
    sp = sub.add_parser("audit", help="Audit a cell's formula and dependencies")
    sp.add_argument("sheet")
    sp.add_argument("ref")
    sp.set_defaults(func=cmd_audit)

    # load-config
    sp = sub.add_parser("load-config", help="Load workbook from YAML/JSON config")
    sp.add_argument("file")
    sp.set_defaults(func=cmd_load_config)

    # save-config
    sp = sub.add_parser("save-config", help="Save current workbook to JSON config")
    sp.add_argument("-o", "--output", required=True)
    sp.set_defaults(func=cmd_save_config)

    # add-sheet
    sp = sub.add_parser("add-sheet", help="Add a new sheet")
    sp.add_argument("name")
    sp.set_defaults(func=cmd_add_sheet)

    # list-sheets
    sp = sub.add_parser("list-sheets", help="List all sheets")
    sp.set_defaults(func=cmd_list_sheets)

    # copy-sheet
    sp = sub.add_parser("copy-sheet", help="Copy a sheet")
    sp.add_argument("source")
    sp.add_argument("dest")
    sp.set_defaults(func=cmd_copy_sheet)

    # clear-sheet
    sp = sub.add_parser("clear-sheet", help="Clear all cells in a sheet")
    sp.add_argument("name")
    sp.set_defaults(func=cmd_clear_sheet)

    # name
    sp = sub.add_parser("name", help="Manage named ranges")
    sp.add_argument("action", choices=["define", "list", "get"])
    sp.add_argument("--name", default="", help="Named range name")
    sp.add_argument("--sheet", default="Sheet1", help="Sheet name")
    sp.add_argument("--ref", default="", help="Cell or range reference")
    sp.set_defaults(func=cmd_name)

    # interactive
    sp = sub.add_parser("interactive", help="Start interactive REPL")
    sp.set_defaults(func=cmd_interactive)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging(verbose=getattr(args, "verbose", False),
                      quiet=getattr(args, "quiet", False))

    engine = Engine()
    if "Sheet1" not in engine.sheets:
        engine.add_sheet("Sheet1")
    try:
        return args.func(engine, args)
    except (EngineError, Exception) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())