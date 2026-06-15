#!/usr/bin/env python3
"""
Command-line interface for the regex engine.

Usage:
    regex-engine PATTERN [TEXT]
    echo TEXT | regex-engine PATTERN

Examples:
    regex-engine '\\d+' 'hello 123 world'
    regex-engine --findall '[a-z]+' 'hello world'
    regex-engine --sub '\\s+' '_' 'hello   world'
    regex-engine --split ',' 'a,b,c'
"""

import sys
import argparse

# Add parent directory to path for development
sys.path.insert(0, '/root/projects/creative-projects/regex-engine')

from regex_engine import Pattern, ParseError


def main():
    parser = argparse.ArgumentParser(
        description='Regex engine — Thompson NFA-based regular expression matching',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s '\\d+' 'hello 123 world'       Match pattern
  %(prog)s --findall '[a-z]+' 'hello world'  Find all matches
  %(prog)s --sub '\\s+' '_' 'hello   world'   Substitute
  %(prog)s --split ',' 'a,b,c'             Split
  %(prog)s --fullmatch 'hello' 'hello'     Full match
        """)
    parser.add_argument('pattern', help='Regular expression pattern')
    parser.add_argument('text', nargs='?', help='Text to match against (or read from stdin)')
    parser.add_argument('--match', '-m', action='store_true',
                        help='Match at start of string (default)')
    parser.add_argument('--search', '-s', action='store_true',
                        help='Search for first match anywhere')
    parser.add_argument('--fullmatch', '-f', action='store_true',
                        help='Match entire string')
    parser.add_argument('--findall', '-a', action='store_true',
                        help='Find all matches')
    parser.add_argument('--sub', '-r', metavar='REPLACEMENT',
                        help='Substitute matches with REPLACEMENT')
    parser.add_argument('--split', '-p', action='store_true',
                        help='Split text by pattern')
    parser.add_argument('--count', '-c', type=int, default=0,
                        help='Max count for sub/split operations')

    args = parser.parse_args()

    # Get text from argument or stdin
    text = args.text
    if text is None:
        if not sys.stdin.isatty():
            text = sys.stdin.read().rstrip('\n')
        else:
            parser.error("TEXT argument required (or pipe to stdin)")

    try:
        p = Pattern(args.pattern)
    except ParseError as e:
        print(f"Error: Invalid regex pattern: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        if args.findall:
            results = p.findall(text)
            for r in results:
                print(r)
        elif args.sub is not None:
            result = p.sub(args.sub, text, count=args.count)
            print(result)
        elif args.split:
            result = p.split(text, maxsplit=args.count)
            for r in result:
                print(r)
        elif args.search:
            m = p.search(text)
            if m:
                print(f"Match: '{m.group(0)}' at {m.span()}")
            else:
                print("No match")
        elif args.fullmatch:
            m = p.fullmatch(text)
            if m:
                print(f"Full match: '{m.group(0)}'")
            else:
                print("No match")
        else:
            # Default: match
            m = p.match(text)
            if m:
                print(f"Match: '{m.group(0)}' at {m.span()}")
            else:
                print("No match")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()