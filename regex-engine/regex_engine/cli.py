#!/usr/bin/env python3
"""
Command-line interface for the regex engine.

A professional CLI tool for Thompson NFA-based regular expression matching.
Supports match, search, fullmatch, findall, sub, and split operations.

Usage:
    regex-engine PATTERN [TEXT]
    echo TEXT | regex-engine PATTERN

Examples:
    regex-engine '\\d+' 'hello 123 world'
    regex-engine --findall '[a-z]+' 'hello world'
    regex-engine --sub '\\s+' '_' 'hello   world'
    regex-engine --split ',' 'a,b,c'
    regex-engine --search '\\d+' 'abc123def'
    regex-engine --fullmatch 'hello' 'hello'
    echo 'test123' | regex-engine '\\d+'
"""

import sys
import argparse
import os

# Add parent directory to path for development
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from regex_engine import Pattern, ParseError


def format_match(match, verbose=False):
    """Format a Match object for display.

    Args:
        match: A Match object or None.
        verbose: If True, show group details.

    Returns:
        Formatted string for output.
    """
    if match is None:
        return "No match"
    lines = [f"Match: '{match.group(0)}' at {match.span()}"]
    if verbose and match._groups:
        for i, g in enumerate(match._groups, 1):
            if g is not None:
                lines.append(f"  Group {i}: '{match.group(i)}' at {match.span(i)}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        prog='regex-engine',
        description='Regex engine — Thompson NFA-based regular expression matching',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s '\\d+' 'hello 123 world'          Match pattern at start
  %(prog)s --search '\\d+' 'abc123def'       Search for first match
  %(prog)s --findall '[a-z]+' 'hello world'  Find all matches
  %(prog)s --sub '\\s+' '_' 'hello   world'   Substitute matches
  %(prog)s --split ',' 'a,b,c'               Split by pattern
  %(prog)s --fullmatch 'hello' 'hello'       Full match
  %(prog)s --verbose '\\d+-(\\d+)' '123-456'  Verbose output with groups
  echo 'test123' | %(prog)s '\\d+'            Read from stdin

Performance:
  This engine guarantees O(nm) matching time where n is the text length
  and m is the pattern length. No exponential backtracking!
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
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show detailed match information including groups')
    parser.add_argument('--version', '-V', action='version',
                        version='%(prog)s 2.0.0')

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
    except TypeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        if args.findall:
            results = p.findall(text)
            for r in results:
                if isinstance(r, tuple):
                    print('\t'.join(r))
                else:
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
            print(format_match(m, verbose=args.verbose))
        elif args.fullmatch:
            m = p.fullmatch(text)
            print(format_match(m, verbose=args.verbose))
        else:
            # Default: match
            m = p.match(text)
            print(format_match(m, verbose=args.verbose))
    except (TypeError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()