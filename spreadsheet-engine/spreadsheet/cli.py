"""
CLI for the spreadsheet engine.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List

from .engine import Engine, EngineError
from .sheet import _format_value


def cmd_set(engine: Engine, args) -> int:
    engine.set(args.sheet, args.ref, args.value)
    engine.recalculate()
    print(f"Set {args.sheet}!{args.ref} = {args.value}")
    return 0


def cmd_get(engine: Engine, args) -> int:
    val = engine.get(args.sheet, args.ref)
    if val is None:
        print("(empty)")
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
        with open(args.output, "w") as f:
            f.write(text)
        print(f"Exported to {args.output}")
    else:
        print(text)
    return 0


def cmd_csv_import(engine: Engine, args) -> int:
    with open(args.file) as f:
        text = f.read()
    engine.import_csv(args.sheet, text)
    engine.recalculate()
    print(f"Imported CSV into {args.sheet}")
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
    # Set formula in a temporary cell, evaluate, then remove
    row, col = 1048575, 16383  # last cell as scratch
    sheet.set(row, col, "=" + args.formula)
    engine.recalculate()
    val = sheet.get(row, col)
    sheet.set(row, col, "")
    print(_format_value(val))
    return 0


def cmd_run(engine: Engine, args) -> int:
    """Run a script file: each line is 'set SHEET REF VALUE'."""
    with open(args.file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 3)
            if len(parts) < 3:
                continue
            cmd, sheet, ref = parts[0], parts[1], parts[2]
            value = parts[3] if len(parts) > 3 else ""
            if cmd.lower() == "set":
                engine.set(sheet, ref, value)
        engine.recalculate()
    # display all sheets
    for name in engine.sheet_names():
        print(f"\n=== {name} ===")
        print(engine.display(name))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="spreadsheet",
        description="From-scratch spreadsheet formula engine",
    )
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("set", help="Set a cell value")
    sp.add_argument("sheet")
    sp.add_argument("ref", help="Cell reference e.g. A1")
    sp.add_argument("value", help="Cell value or formula (prefix with =)")
    sp.set_defaults(func=cmd_set)

    sp = sub.add_parser("get", help="Get a cell value")
    sp.add_argument("sheet")
    sp.add_argument("ref")
    sp.set_defaults(func=cmd_get)

    sp = sub.add_parser("recalc", help="Recalculate all sheets")
    sp.set_defaults(func=cmd_recalc)

    sp = sub.add_parser("display", help="Display a sheet as ASCII grid")
    sp.add_argument("sheet")
    sp.add_argument("--max-rows", type=int, default=20)
    sp.add_argument("--max-cols", type=int, default=10)
    sp.set_defaults(func=cmd_display)

    sp = sub.add_parser("csv-export", help="Export sheet to CSV")
    sp.add_argument("sheet")
    sp.add_argument("-o", "--output", help="Output file (stdout if omitted)")
    sp.set_defaults(func=cmd_csv_export)

    sp = sub.add_parser("csv-import", help="Import CSV into a sheet")
    sp.add_argument("sheet")
    sp.add_argument("file")
    sp.set_defaults(func=cmd_csv_import)

    sp = sub.add_parser("json-save", help="Save engine state to JSON")
    sp.add_argument("-o", "--output", required=True)
    sp.set_defaults(func=cmd_json_save)

    sp = sub.add_parser("json-load", help="Load engine state from JSON")
    sp.add_argument("file")
    sp.set_defaults(func=cmd_json_load)

    sp = sub.add_parser("eval", help="Evaluate a formula expression")
    sp.add_argument("sheet")
    sp.add_argument("formula", help="Formula without leading =")
    sp.set_defaults(func=cmd_eval)

    sp = sub.add_parser("run", help="Run a script file")
    sp.add_argument("file")
    sp.set_defaults(func=cmd_run)

    return p


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    engine = Engine()
    # always create a default sheet
    if "Sheet1" not in engine.sheets:
        engine.add_sheet("Sheet1")
    try:
        return args.func(engine, args)
    except (EngineError, Exception) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())