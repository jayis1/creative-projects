"""CLI interface for the B+ Tree database engine."""

from __future__ import annotations

import argparse
import json
import sys
import os

from .database import Database
from .config import DatabaseConfig
from . import io as db_io


def interactive_shell(db: Database) -> None:
    """Run an interactive shell for querying the database."""
    print(f"B+ Tree Database Shell v{db.__class__.__module__.split('.')[0] if hasattr(db.__class__, '__module__') else '3.0'}")
    print("Type 'help' for commands, 'quit' to exit.")
    print(f"Database: {len(db)} keys, order={db._tree.order}")
    if db._cache is not None:
        print(f"Cache: enabled (max_size={db._cache.max_size})")
    print()

    while True:
        try:
            line = input("bplus-db> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not line:
            continue

        cmd = line.lower()

        if cmd in ("quit", "exit", "q"):
            print("Bye!")
            break
        elif cmd == "help":
            print("""
Available commands:
  SELECT * FROM db                          - List all entries
  SELECT * FROM db WHERE key = 'x'          - Get value for key 'x'
  SELECT * FROM db WHERE key >= 'a' AND key <= 'z'  - Range query
  INSERT INTO db KEY 'x' VALUE 'y'          - Insert key-value pair
  DELETE FROM db WHERE key = 'x'            - Delete key 'x'
  COUNT db                                  - Count total keys
  PUT <key> <value>                         - Shorthand insert
  GET <key>                                 - Shorthand lookup
  DEL <key>                                 - Shorthand delete
  RANGE <start> <end>                       - Shorthand range query
  PREFIX <prefix>                           - Prefix scan
  TTL <key> <seconds>                       - Set TTL on a key
  TTLGET <key>                              - Get remaining TTL
  EXPIRED                                   - Remove all expired keys
  CURSOR [prefix] [page_size]               - Iterate with pagination
  STATS                                     - Show database stats
  CACHE                                     - Show cache stats
  TREE                                      - Show tree structure
  VALIDATE                                  - Validate tree invariants
  KEYS                                      - List all keys
  SAVE [path]                               - Save to disk (JSON)
  SAVEBIN [path]                            - Save to disk (binary)
  EXPORT_CSV <path>                         - Export to CSV
  IMPORT_CSV <path>                         - Import from CSV
  EXPORT_JSONL <path>                       - Export to JSON Lines
  IMPORT_JSONL <path>                        - Import from JSON Lines
  EXPORT_PICKLE <path>                      - Export to pickle
  IMPORT_PICKLE <path>                       - Import from pickle
  HELP                                      - Show this help
  QUIT                                      - Exit shell
""")
        elif cmd == "stats":
            stats = db.stats()
            for k, v in stats.items():
                if isinstance(v, dict):
                    print(f"  {k}:")
                    for sk, sv in v.items():
                        print(f"    {sk}: {sv}")
                else:
                    print(f"  {k}: {v}")
        elif cmd == "tree":
            print(db.tree_structure())
        elif cmd == "validate":
            violations = db.validate()
            if violations:
                print("VIOLATIONS FOUND:")
                for v in violations:
                    print(f"  - {v}")
            else:
                print("Tree is valid. No violations found.")
        elif cmd == "keys":
            keys = db.keys()
            for k in keys:
                print(f"  {k!r}")
            print(f"({len(keys)} keys)")
        elif cmd == "cache":
            cache_stats = db.cache_stats()
            if cache_stats is None:
                print("Cache is disabled.")
            else:
                for k, v in cache_stats.items():
                    print(f"  {k}: {v}")
        elif cmd == "expired":
            count = db.cleanup_expired()
            print(f"Removed {count} expired keys.")
        elif line.upper().startswith("SELECT") or line.upper().startswith("INSERT") or line.upper().startswith("DELETE") or line.upper().startswith("COUNT"):
            try:
                result = db.execute(line)
                if result is None:
                    print("(no results)")
                elif isinstance(result, list):
                    for k, v in result:
                        print(f"  {k!r} => {v!r}")
                    print(f"({len(result)} results)")
                else:
                    print(f"  {result}")
            except Exception as e:
                print(f"Error: {e}")
        elif cmd.startswith("put "):
            parts = line.split(None, 2)
            if len(parts) < 3:
                print("Usage: PUT <key> <value>")
                continue
            # Try to parse value as JSON, fall back to string
            try:
                value = json.loads(parts[2])
            except (json.JSONDecodeError, ValueError):
                value = parts[2]
            db.put(parts[1], value)
            print("OK")
        elif cmd.startswith("get "):
            key = line.split(None, 1)[1]
            val = db.get(key)
            if val is None and not db.contains(key):
                print("(not found)")
            else:
                print(f"  {val!r}")
        elif cmd.startswith("del "):
            key = line.split(None, 1)[1]
            if db.delete(key):
                print("Deleted")
            else:
                print("(not found)")
        elif cmd.startswith("range "):
            parts = line.split(None, 2)
            if len(parts) < 3:
                print("Usage: RANGE <start> <end>")
                continue
            results = db.range_query(parts[1], parts[2])
            for k, v in results:
                print(f"  {k!r} => {v!r}")
            print(f"({len(results)} results)")
        elif cmd.startswith("prefix "):
            prefix = line.split(None, 1)[1]
            results = db.prefix_scan(prefix)
            for k, v in results:
                print(f"  {k!r} => {v!r}")
            print(f"({len(results)} results)")
        elif cmd.startswith("ttl "):
            parts = line.split(None, 2)
            if len(parts) < 3:
                print("Usage: TTL <key> <seconds>")
                continue
            try:
                seconds = float(parts[2])
                db.set_ttl(parts[1], seconds)
                print(f"TTL set: {parts[1]!r} expires in {seconds}s")
            except KeyError as e:
                print(f"Error: {e}")
            except ValueError:
                print("Error: seconds must be a number")
        elif cmd.startswith("ttlget "):
            key = line.split(None, 1)[1]
            remaining = db.get_ttl(key)
            if remaining is None:
                print(f"  No TTL set for {key!r}")
            elif remaining == 0.0:
                print(f"  {key!r} has expired")
            else:
                print(f"  {key!r} expires in {remaining:.1f}s")
        elif cmd.startswith("cursor"):
            parts = line.split(None, 2)
            prefix = parts[1] if len(parts) > 1 else None
            page_size = int(parts[2]) if len(parts) > 2 else 50
            cur = db.cursor(prefix=prefix, page_size=page_size)
            total = 0
            while not cur.exhausted:
                page = cur.fetch_page()
                if not page:
                    break
                for k, v in page:
                    print(f"  {k!r} => {v!r}")
                total += len(page)
            print(f"({total} results)")
        elif cmd.startswith("export_csv "):
            path = line.split(None, 1)[1]
            count = db_io.export_csv(db, path)
            print(f"Exported {count} rows to {path}")
        elif cmd.startswith("import_csv "):
            path = line.split(None, 1)[1]
            count = db_io.import_csv(db, path)
            print(f"Imported {count} rows from {path}")
        elif cmd.startswith("export_jsonl "):
            path = line.split(None, 1)[1]
            count = db_io.export_json_lines(db, path)
            print(f"Exported {count} rows to {path}")
        elif cmd.startswith("import_jsonl "):
            path = line.split(None, 1)[1]
            count = db_io.import_json_lines(db, path)
            print(f"Imported {count} rows from {path}")
        elif cmd.startswith("export_pickle "):
            path = line.split(None, 1)[1]
            count = db_io.export_pickle(db, path)
            print(f"Exported {count} entries to {path}")
        elif cmd.startswith("import_pickle "):
            path = line.split(None, 1)[1]
            count = db_io.import_pickle(db, path)
            print(f"Imported {count} entries from {path}")
        elif cmd.startswith("savebin"):
            parts = line.split(None, 1)
            path = parts[1] if len(parts) > 1 else None
            try:
                db.save_binary(path)
                print("Saved (binary).")
            except Exception as e:
                print(f"Error saving: {e}")
        elif cmd.startswith("save"):
            parts = line.split(None, 1)
            path = parts[1] if len(parts) > 1 else None
            try:
                db.save(path)
                print("Saved.")
            except Exception as e:
                print(f"Error saving: {e}")
        else:
            print(f"Unknown command: {line!r}. Type 'help' for commands.")


def main():
    parser = argparse.ArgumentParser(
        description="B+ Tree Database Engine v3.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  bplus-db shell                    Interactive shell
  bplus-db shell -d mydb.json       Open database file
  bplus-db shell -c config.toml     Use config file
  bplus-db execute "SELECT * FROM db WHERE key >= 'a'"
  bplus-db load data.json           Load and inspect a database
  bplus-db validate data.json       Validate tree invariants
  bplus-db export data.json out.csv Export database to CSV
  bplus-db import data.json in.csv  Import CSV into database
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Shell command
    shell_parser = subparsers.add_parser("shell", help="Interactive shell")
    shell_parser.add_argument("-d", "--database", help="Database file to open")
    shell_parser.add_argument("-o", "--order", type=int, default=64, help="B+ tree order")
    shell_parser.add_argument("-c", "--config", help="Config file (JSON or TOML)")
    shell_parser.add_argument("--cache", type=int, default=0, help="Enable LRU cache with given size (0=disabled)")

    # Execute command
    exec_parser = subparsers.add_parser("execute", help="Execute a query")
    exec_parser.add_argument("query", help="SQL-like query to execute")
    exec_parser.add_argument("-d", "--database", help="Database file to open")
    exec_parser.add_argument("-o", "--order", type=int, default=64, help="B+ tree order")

    # Load command
    load_parser = subparsers.add_parser("load", help="Load a database file")
    load_parser.add_argument("file", help="Database file to load")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate tree invariants")
    validate_parser.add_argument("file", help="Database file to validate")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export database to file")
    export_parser.add_argument("database", help="Database file to export from")
    export_parser.add_argument("output", help="Output file (extension determines format: .csv, .jsonl, .pkl)")
    export_parser.add_argument("-o", "--order", type=int, default=64, help="B+ tree order")

    # Import command
    import_parser = subparsers.add_parser("import", help="Import data into database")
    import_parser.add_argument("database", help="Database file to save into")
    import_parser.add_argument("input", help="Input file (.csv, .jsonl, .pkl)")
    import_parser.add_argument("-o", "--order", type=int, default=64, help="B+ tree order")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "shell":
        config = None
        if hasattr(args, "config") and args.config:
            config = DatabaseConfig.from_file(args.config)

        if hasattr(args, "database") and args.database and os.path.exists(args.database):
            db = Database.load(args.database)
            print(f"Loaded database from {args.database}")
        elif config is not None:
            db = Database(config=config)
        else:
            db = Database(order=args.order)

        # Enable cache if requested
        if hasattr(args, "cache") and args.cache > 0:
            from .cache import LRUCache
            db._cache = LRUCache(max_size=args.cache)
            print(f"Cache enabled (max_size={args.cache})")

        interactive_shell(db)

    elif args.command == "execute":
        if args.database and os.path.exists(args.database):
            db = Database.load(args.database)
        else:
            db = Database(order=args.order)
        result = db.execute(args.query)
        if result is not None:
            if isinstance(result, list):
                for k, v in result:
                    print(f"{k!r} => {v!r}")
                print(f"({len(result)} results)")
            else:
                print(result)

    elif args.command == "load":
        db = Database.load(args.file)
        print(f"Loaded database from {args.file}")
        print(f"Keys: {len(db)}")
        print(f"Stats: {db.stats()}")

    elif args.command == "validate":
        db = Database.load(args.file)
        violations = db.validate()
        if violations:
            print(f"FOUND {len(violations)} VIOLATIONS:")
            for v in violations:
                print(f"  - {v}")
            sys.exit(1)
        else:
            print("Tree is valid. No violations found.")

    elif args.command == "export":
        db = Database.load(args.database)
        ext = os.path.splitext(args.output)[1].lower()
        if ext == ".csv":
            count = db_io.export_csv(db, args.output)
        elif ext == ".jsonl":
            count = db_io.export_json_lines(db, args.output)
        elif ext in (".pkl", ".pickle"):
            count = db_io.export_pickle(db, args.output)
        else:
            print(f"Unsupported export format: {ext}")
            sys.exit(1)
        print(f"Exported {count} entries to {args.output}")

    elif args.command == "import":
        db = Database(order=args.order)
        ext = os.path.splitext(args.input)[1].lower()
        if ext == ".csv":
            count = db_io.import_csv(db, args.input)
        elif ext == ".jsonl":
            count = db_io.import_json_lines(db, args.input)
        elif ext in (".pkl", ".pickle"):
            count = db_io.import_pickle(db, args.input)
        else:
            print(f"Unsupported import format: {ext}")
            sys.exit(1)
        db.save(args.database)
        print(f"Imported {count} entries, saved to {args.database}")


if __name__ == "__main__":
    main()