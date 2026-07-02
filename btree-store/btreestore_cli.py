#!/usr/bin/env python3
"""
btreestore CLI: command-line interface for the B+Tree persistent store.

Usage:
  btreestore --db FILE put KEY VALUE
  btreestore --db FILE get KEY
  btreestore --db FILE del KEY
  btreestore --db FILE cas KEY EXPECTED NEW_VALUE
  btreestore --db FILE scan [--low K] [--high K] [--include-high] [--reverse]
                              [--limit N] [--offset N] [--format json|tsv]
  btreestore --db FILE prefix PREFIX [--reverse] [--limit N] [--offset N]
  btreestore --db FILE count
  btreestore --db FILE min
  btreestore --db FILE max
  btreestore --db FILE stats [--format json]
  btreestore --db FILE validate
  btreestore --db FILE batch-import FILE.json
  btreestore --db FILE batch-export FILE.json
  btreestore --db FILE compact
  btreestore --db FILE checkpoint
  btreestore --db FILE incr KEY [AMOUNT]
  btreestore --db FILE interactive
  btreestore --config CONFIG.toml --db FILE put KEY VALUE
"""

import argparse
import json
import sys
import os

# Add the project directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from btreestore.store import Store
from btreestore.config import StoreConfig


def _decode(b: bytes) -> str:
    """Decode bytes to string, falling back to hex for binary data."""
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.hex()


def _open_store(args) -> Store:
    """Open a store from CLI arguments, optionally using a config file."""
    config = None
    if args.config:
        config = StoreConfig.from_file(args.config)
        config.path = args.db or config.path
    kwargs = {}
    if config:
        kwargs["config"] = config
    else:
        kwargs["page_size"] = args.page_size
        kwargs["wal_enabled"] = not args.no_wal
        kwargs["log_level"] = args.log_level
        if args.log_file:
            kwargs["log_file"] = args.log_file
        kwargs["sync_on_commit"] = args.sync
    return Store(args.db, **kwargs)


def cmd_put(store, args):
    store.put(args.key.encode(), args.value.encode())
    print(f"OK: {args.key} -> {args.value}")


def cmd_get(store, args):
    val = store.get(args.key.encode())
    if val is None:
        print(f"NOT FOUND: {args.key}")
        sys.exit(1)
    else:
        print(_decode(val))


def cmd_del(store, args):
    existed = store.delete(args.key.encode())
    if existed:
        print(f"DELETED: {args.key}")
    else:
        print(f"NOT FOUND: {args.key}")
        sys.exit(1)


def cmd_cas(store, args):
    expected = args.expected.encode() if args.expected != "__NONE__" else None
    new_val = args.new_value.encode() if args.new_value != "__NONE__" else None
    success = store.cas(args.key.encode(), expected, new_val)
    if success:
        print(f"OK: CAS succeeded for {args.key}")
    else:
        print(f"FAIL: CAS mismatch for {args.key}")
        sys.exit(1)


def cmd_scan(store, args):
    low = args.low.encode() if args.low else None
    high = args.high.encode() if args.high else None
    c = store.cursor(low=low, high=high, include_high=args.include_high,
                     reverse=args.reverse, limit=args.limit, offset=args.offset)
    count = 0
    if args.format == "json":
        data = []
        for k, v in c:
            data.append({"key": _decode(k), "value": _decode(v)})
            count += 1
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        for k, v in c:
            print(f"{_decode(k)}\t{_decode(v)}")
            count += 1
    if args.summary:
        print(f"-- {count} entries --", file=sys.stderr)


def cmd_prefix(store, args):
    c = store.prefix(args.prefix.encode(), reverse=args.reverse,
                     limit=args.limit, offset=args.offset)
    count = 0
    if args.format == "json":
        data = []
        for k, v in c:
            data.append({"key": _decode(k), "value": _decode(v)})
            count += 1
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        for k, v in c:
            print(f"{_decode(k)}\t{_decode(v)}")
            count += 1
    if args.summary:
        print(f"-- {count} entries --", file=sys.stderr)


def cmd_count(store, args):
    print(store.count())


def cmd_min(store, args):
    result = store.min()
    if result is None:
        print("(empty)")
    else:
        print(f"{_decode(result[0])}\t{_decode(result[1])}")


def cmd_max(store, args):
    result = store.max()
    if result is None:
        print("(empty)")
    else:
        print(f"{_decode(result[0])}\t{_decode(result[1])}")


def cmd_stats(store, args):
    s = store.stats()
    if args.format == "json":
        print(json.dumps(s, indent=2))
    else:
        for k, v in s.items():
            print(f"{k}: {v}")


def cmd_validate(store, args):
    if store.validate():
        print("OK: tree structure is valid")
    else:
        print("ERROR: tree structure is invalid!")
        sys.exit(1)


def cmd_compact(store, args):
    n = store.compact()
    print(f"Compacted {n} keys")


def cmd_checkpoint(store, args):
    store.checkpoint()
    print("Checkpoint complete")


def cmd_incr(store, args):
    amount = int(args.amount) if args.amount else 1
    result = store.increment(args.key.encode(), amount)
    print(f"OK: {args.key} -> {result}")


def cmd_batch_import(store, args):
    """Import key-value pairs from a JSON file."""
    with open(args.file, "r") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        print("ERROR: JSON file must contain a dict/object", file=sys.stderr)
        sys.exit(1)
    # Support both {key: value} and {key: {value: v, ...}} formats
    pairs = {}
    for k, v in data.items():
        if isinstance(v, dict) and "value" in v:
            pairs[k.encode()] = v["value"].encode()
        elif isinstance(v, str):
            pairs[k.encode()] = v.encode()
        else:
            pairs[k.encode()] = json.dumps(v).encode()
    txn = store.begin()
    try:
        txn.put_many(pairs)
        store.commit(txn)
        print(f"Imported {len(data)} entries")
    except Exception as e:
        store.rollback(txn)
        print(f"Import failed: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_batch_export(store, args):
    """Export all key-value pairs to a JSON file."""
    c = store.cursor()
    data = {}
    for k, v in c:
        data[_decode(k)] = _decode(v)
    with open(args.file, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Exported {len(data)} entries to {args.file}")


def cmd_interactive(store, args):
    """Simple interactive REPL."""
    print("btreestore interactive. Commands: get KEY, put KEY VALUE, "
          "del KEY, cas KEY EXPECTED:NEW, scan [--reverse] [--limit N], "
          "prefix PREFIX, count, min, max, stats, validate, incr KEY [N], "
          "compact, checkpoint, quit")
    while True:
        try:
            line = input("btree> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        parts = line.split(None, 2)
        cmd = parts[0].lower()
        if cmd in ("quit", "exit", "q"):
            break
        elif cmd == "get" and len(parts) >= 2:
            val = store.get(parts[1].encode())
            if val is None:
                print("(none)")
            else:
                print(_decode(val))
        elif cmd == "put" and len(parts) == 3:
            store.put(parts[1].encode(), parts[2].encode())
            print("OK")
        elif cmd == "del" and len(parts) >= 2:
            if store.delete(parts[1].encode()):
                print("OK")
            else:
                print("(not found)")
        elif cmd == "cas" and len(parts) == 3:
            if ":" in parts[2]:
                exp, new = parts[2].split(":", 1)
            else:
                exp, new = parts[2], parts[2]
            exp_b = exp.encode() if exp != "-" else None
            new_b = new.encode() if new != "-" else None
            if store.cas(parts[1].encode(), exp_b, new_b):
                print("OK")
            else:
                print("FAIL: mismatch")
        elif cmd == "scan":
            words = parts[1:] if len(parts) > 1 else []
            reverse = "--reverse" in words
            limit = None
            for i, w in enumerate(words):
                if w == "--limit" and i + 1 < len(words):
                    limit = int(words[i + 1])
            c = store.cursor(reverse=reverse, limit=limit)
            n = 0
            for k, v in c:
                print(f"  {_decode(k)}\t{_decode(v)}")
                n += 1
            print(f"({n} entries)")
        elif cmd == "prefix" and len(parts) >= 2:
            c = store.prefix(parts[1].encode())
            n = 0
            for k, v in c:
                print(f"  {_decode(k)}\t{_decode(v)}")
                n += 1
            print(f"({n} entries)")
        elif cmd == "count":
            print(store.count())
        elif cmd == "min":
            r = store.min()
            if r:
                print(f"  {_decode(r[0])}\t{_decode(r[1])}")
            else:
                print("  (empty)")
        elif cmd == "max":
            r = store.max()
            if r:
                print(f"  {_decode(r[0])}\t{_decode(r[1])}")
            else:
                print("  (empty)")
        elif cmd == "stats":
            for k, v in store.stats().items():
                print(f"  {k}: {v}")
        elif cmd == "validate":
            print("  OK" if store.validate() else "  ERROR: invalid")
        elif cmd == "incr" and len(parts) >= 2:
            amount = int(parts[2]) if len(parts) >= 3 else 1
            result = store.increment(parts[1].encode(), amount)
            print(f"  OK: {result}")
        elif cmd == "compact":
            n = store.compact()
            print(f"  Compacted {n} keys")
        elif cmd == "checkpoint":
            store.checkpoint()
            print("  OK")
        else:
            print("Unknown command. Type 'quit' to exit.")


def main():
    parser = argparse.ArgumentParser(
        description="btreestore: persistent B+Tree key-value store CLI"
    )
    parser.add_argument("--db", required=False, help="Database file path")
    parser.add_argument("--config", help="Path to config file (JSON or TOML)")
    parser.add_argument("--page-size", type=int, default=4096,
                        help="Page size in bytes (default: 4096)")
    parser.add_argument("--no-wal", action="store_true",
                        help="Disable Write-Ahead Log")
    parser.add_argument("--log-level", default="INFO",
                        help="Log level (DEBUG, INFO, WARNING, ERROR)")
    parser.add_argument("--log-file", help="Path to log file")
    parser.add_argument("--sync", action="store_true",
                        help="Sync (fsync) on every commit")
    sub = parser.add_subparsers(dest="command", required=True)

    put_p = sub.add_parser("put", help="Insert or update a key")
    put_p.add_argument("key")
    put_p.add_argument("value")

    get_p = sub.add_parser("get", help="Get value for key")
    get_p.add_argument("key")

    del_p = sub.add_parser("del", help="Delete a key")
    del_p.add_argument("key")

    cas_p = sub.add_parser("cas", help="Compare-and-swap")
    cas_p.add_argument("key")
    cas_p.add_argument("expected", help="Expected value (use __NONE__ for absent)")
    cas_p.add_argument("new_value", help="New value (use __NONE__ to delete)")

    scan_p = sub.add_parser("scan", help="Scan keys in order")
    scan_p.add_argument("--low", help="Lower bound key (inclusive)")
    scan_p.add_argument("--high", help="Upper bound key (exclusive by default)")
    scan_p.add_argument("--include-high", action="store_true",
                         help="Include the upper bound key")
    scan_p.add_argument("--reverse", action="store_true",
                        help="Scan in descending key order")
    scan_p.add_argument("--limit", type=int, help="Maximum number of entries")
    scan_p.add_argument("--offset", type=int, default=0,
                        help="Number of entries to skip")
    scan_p.add_argument("--format", choices=["tsv", "json"], default="tsv",
                        help="Output format (default: tsv)")
    scan_p.add_argument("--summary", action="store_true",
                        help="Print count to stderr")

    prefix_p = sub.add_parser("prefix", help="Scan keys with a prefix")
    prefix_p.add_argument("prefix")
    prefix_p.add_argument("--reverse", action="store_true",
                           help="Scan in descending key order")
    prefix_p.add_argument("--limit", type=int, help="Maximum number of entries")
    prefix_p.add_argument("--offset", type=int, default=0,
                           help="Number of entries to skip")
    prefix_p.add_argument("--format", choices=["tsv", "json"], default="tsv",
                           help="Output format (default: tsv)")
    prefix_p.add_argument("--summary", action="store_true")

    sub.add_parser("count", help="Count total keys")
    sub.add_parser("min", help="Get the minimum key")
    sub.add_parser("max", help="Get the maximum key")

    stats_p = sub.add_parser("stats", help="Show database statistics")
    stats_p.add_argument("--format", choices=["tsv", "json"], default="tsv",
                          help="Output format (default: tsv)")

    sub.add_parser("validate", help="Validate B+Tree structure")
    sub.add_parser("compact", help="Compact the tree (rebuild with all keys)")
    sub.add_parser("checkpoint", help="Checkpoint the WAL")

    incr_p = sub.add_parser("incr", help="Atomically increment a numeric value")
    incr_p.add_argument("key")
    incr_p.add_argument("amount", nargs="?", default="1", help="Increment amount (default: 1)")

    import_p = sub.add_parser("batch-import", help="Import from JSON file")
    import_p.add_argument("file")

    export_p = sub.add_parser("batch-export", help="Export to JSON file")
    export_p.add_argument("file")

    sub.add_parser("interactive", help="Interactive REPL")

    args = parser.parse_args()

    if not args.db and not args.config:
        parser.error("--db or --config is required")

    store = _open_store(args)
    try:
        {
            "put": cmd_put,
            "get": cmd_get,
            "del": cmd_del,
            "cas": cmd_cas,
            "scan": cmd_scan,
            "prefix": cmd_prefix,
            "count": cmd_count,
            "min": cmd_min,
            "max": cmd_max,
            "stats": cmd_stats,
            "validate": cmd_validate,
            "compact": cmd_compact,
            "checkpoint": cmd_checkpoint,
            "incr": cmd_incr,
            "batch-import": cmd_batch_import,
            "batch-export": cmd_batch_export,
            "interactive": cmd_interactive,
        }[args.command](store, args)
    finally:
        store.close()


if __name__ == "__main__":
    main()