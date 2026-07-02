#!/usr/bin/env python3
"""btree-store CLI: command-line interface for the B+Tree persistent store.

Usage:
  python cli.py --db FILE put KEY VALUE
  python cli.py --db FILE get KEY
  python cli.py --db FILE del KEY
  python cli.py --db FILE scan [--low K] [--high K] [--limit N]
  python cli.py --db FILE prefix PREFIX [--limit N]
  python cli.py --db FILE count
  python cli.py --db FILE stats
  python cli.py --db FILE validate
  python cli.py --db FILE batch-import FILE.json
  python cli.py --db FILE batch-export FILE.json
  python cli.py --db FILE interactive
"""

import argparse
import json
import sys
import os

# Add the project directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import btree


def cmd_put(store, args):
    store.put(args.key.encode(), args.value.encode())
    print(f"OK: {args.key} -> {args.value}")


def cmd_get(store, args):
    val = store.get(args.key.encode())
    if val is None:
        print(f"NOT FOUND: {args.key}")
        sys.exit(1)
    else:
        try:
            print(val.decode('utf-8'))
        except UnicodeDecodeError:
            sys.stdout.buffer.write(val)
            sys.stdout.write('\n')


def cmd_del(store, args):
    existed = store.delete(args.key.encode())
    if existed:
        print(f"DELETED: {args.key}")
    else:
        print(f"NOT FOUND: {args.key}")
        sys.exit(1)


def cmd_scan(store, args):
    low = args.low.encode() if args.low else None
    high = args.high.encode() if args.high else None
    c = store.cursor(low=low, high=high, include_high=args.include_high)
    count = 0
    for k, v in c:
        try:
            ks = k.decode('utf-8')
        except UnicodeDecodeError:
            ks = k.hex()
        try:
            vs = v.decode('utf-8')
        except UnicodeDecodeError:
            vs = v.hex()
        print(f"{ks}\t{vs}")
        count += 1
        if args.limit and count >= args.limit:
            break
    if args.summary:
        print(f"-- {count} entries --", file=sys.stderr)


def cmd_prefix(store, args):
    c = store.prefix(args.prefix.encode())
    count = 0
    for k, v in c:
        try:
            ks = k.decode('utf-8')
        except UnicodeDecodeError:
            ks = k.hex()
        try:
            vs = v.decode('utf-8')
        except UnicodeDecodeError:
            vs = v.hex()
        print(f"{ks}\t{vs}")
        count += 1
        if args.limit and count >= args.limit:
            break
    if args.summary:
        print(f"-- {count} entries --", file=sys.stderr)


def cmd_count(store, args):
    print(store.count())


def cmd_stats(store, args):
    s = store.stats()
    for k, v in s.items():
        print(f"{k}: {v}")


def cmd_validate(store, args):
    if store.validate():
        print("OK: tree structure is valid")
    else:
        print("ERROR: tree structure is invalid!")
        sys.exit(1)


def cmd_batch_import(store, args):
    """Import key-value pairs from a JSON file.

    JSON format: {"key1": "value1", "key2": "value2", ...}
    All keys/values must be strings (will be UTF-8 encoded).
    """
    with open(args.file, 'r') as f:
        data = json.load(f)
    txn = store.begin()
    try:
        for k, v in data.items():
            txn.put(k.encode(), v.encode())
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
        try:
            ks = k.decode('utf-8')
            vs = v.decode('utf-8')
        except UnicodeDecodeError:
            ks = k.hex()
            vs = v.hex()
        data[ks] = vs
    with open(args.file, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Exported {len(data)} entries to {args.file}")


def cmd_interactive(store, args):
    """Simple interactive REPL."""
    print("btree-store interactive. Commands: get KEY, put KEY VALUE, "
          "del KEY, scan, count, stats, quit")
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
        if cmd in ('quit', 'exit', 'q'):
            break
        elif cmd == 'get' and len(parts) >= 2:
            val = store.get(parts[1].encode())
            if val is None:
                print("(none)")
            else:
                try:
                    print(val.decode())
                except UnicodeDecodeError:
                    print(val.hex())
        elif cmd == 'put' and len(parts) == 3:
            store.put(parts[1].encode(), parts[2].encode())
            print("OK")
        elif cmd == 'del' and len(parts) >= 2:
            if store.delete(parts[1].encode()):
                print("OK")
            else:
                print("(not found)")
        elif cmd == 'scan':
            c = store.cursor()
            n = 0
            for k, v in c:
                try:
                    ks = k.decode()
                except UnicodeDecodeError:
                    ks = k.hex()
                try:
                    vs = v.decode()
                except UnicodeDecodeError:
                    vs = v.hex()
                print(f"  {ks}\t{vs}")
                n += 1
            print(f"({n} entries)")
        elif cmd == 'count':
            print(store.count())
        elif cmd == 'stats':
            for k, v in store.stats().items():
                print(f"  {k}: {v}")
        else:
            print("Unknown command. Type 'quit' to exit.")


def main():
    parser = argparse.ArgumentParser(
        description="btree-store: persistent B+Tree key-value store CLI"
    )
    parser.add_argument('--db', required=True, help='Database file path')
    parser.add_argument('--page-size', type=int, default=4096,
                        help='Page size in bytes (default: 4096)')
    sub = parser.add_subparsers(dest='command', required=True)

    put_p = sub.add_parser('put', help='Insert or update a key')
    put_p.add_argument('key')
    put_p.add_argument('value')

    get_p = sub.add_parser('get', help='Get value for key')
    get_p.add_argument('key')

    del_p = sub.add_parser('del', help='Delete a key')
    del_p.add_argument('key')

    scan_p = sub.add_parser('scan', help='Scan keys in order')
    scan_p.add_argument('--low', help='Lower bound key (inclusive)')
    scan_p.add_argument('--high', help='Upper bound key (exclusive by default)')
    scan_p.add_argument('--include-high', action='store_true',
                         help='Include the upper bound key')
    scan_p.add_argument('--limit', type=int, help='Maximum number of entries')
    scan_p.add_argument('--summary', action='store_true',
                        help='Print count to stderr')

    prefix_p = sub.add_parser('prefix', help='Scan keys with a prefix')
    prefix_p.add_argument('prefix')
    prefix_p.add_argument('--limit', type=int, help='Maximum number of entries')
    prefix_p.add_argument('--summary', action='store_true')

    sub.add_parser('count', help='Count total keys')
    sub.add_parser('stats', help='Show database statistics')
    sub.add_parser('validate', help='Validate B+Tree structure')

    import_p = sub.add_parser('batch-import', help='Import from JSON file')
    import_p.add_argument('file')

    export_p = sub.add_parser('batch-export', help='Export to JSON file')
    export_p.add_argument('file')

    sub.add_parser('interactive', help='Interactive REPL')

    args = parser.parse_args()

    store = btree.Store(args.db, page_size=args.page_size)
    try:
        {
            'put': cmd_put,
            'get': cmd_get,
            'del': cmd_del,
            'scan': cmd_scan,
            'prefix': cmd_prefix,
            'count': cmd_count,
            'stats': cmd_stats,
            'validate': cmd_validate,
            'batch-import': cmd_batch_import,
            'batch-export': cmd_batch_export,
            'interactive': cmd_interactive,
        }[args.command](store, args)
    finally:
        store.close()


if __name__ == '__main__':
    main()