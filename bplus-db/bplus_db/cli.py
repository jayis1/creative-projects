"""CLI interface for the B+ Tree database engine."""

from __future__ import annotations

import argparse
import sys
import os

from .database import Database


def interactive_shell(db: Database) -> None:
    """Run an interactive shell for querying the database."""
    print("B+ Tree Database Shell v2.0")
    print("Type 'help' for commands, 'quit' to exit.")
    print(f"Database: {len(db)} keys, order={db._tree.order}")
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
  STATS                                     - Show database stats
  TREE                                      - Show tree structure
  VALIDATE                                  - Validate tree invariants
  KEYS                                      - List all keys
  SAVE [path]                               - Save to disk (JSON)
  SAVEBIN [path]                            - Save to disk (binary)
  HELP                                      - Show this help
  QUIT                                      - Exit shell
""")
        elif cmd == "stats":
            stats = db.stats()
            for k, v in stats.items():
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
            db.put(parts[1], parts[2])
            print("OK")
        elif cmd.startswith("get "):
            key = line.split(None, 1)[1]
            val = db.get(key)
            if val is None:
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
        description="B+ Tree Database Engine v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  bplus-db shell                    Interactive shell
  bplus-db shell -d mydb.json       Open database file
  bplus-db execute "SELECT * FROM db WHERE key >= 'a'"
  bplus-db load data.json           Load and inspect a database
  bplus-db validate data.json       Validate tree invariants
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Shell command
    shell_parser = subparsers.add_parser("shell", help="Interactive shell")
    shell_parser.add_argument("-d", "--database", help="Database file to open")
    shell_parser.add_argument("-o", "--order", type=int, default=64, help="B+ tree order")

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

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "shell":
        if args.database and os.path.exists(args.database):
            db = Database.load(args.database)
            print(f"Loaded database from {args.database}")
        else:
            db = Database(order=args.order)
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


if __name__ == "__main__":
    main()