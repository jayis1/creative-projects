"""Command-line interface for the BASIC interpreter.

Provides a full CLI with:
- File execution mode: basic-interpreter program.bas
- One-liner mode: basic-interpreter -e 'PRINT 42'
- Interactive REPL mode: basic-interpreter
- Configuration file support: basic-interpreter --config config.toml
- Trace mode: basic-interpreter --trace program.bas
"""

from __future__ import annotations

import argparse
import sys
import os
import re
import logging

from basic_interpreter.interpreter import Interpreter
from basic_interpreter.errors import BasicError, BasicStopException

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="basic-interpreter",
        description="BASIC Language Interpreter v3.0 — A full-featured interpreter for a classic BASIC dialect",
        epilog="""\
examples:
  basic-interpreter program.bas           # run a BASIC program
  basic-interpreter -e 'PRINT "Hello"'    # one-liner mode
  basic-interpreter                        # interactive REPL
  basic-interpreter --trace program.bas   # trace line execution
  basic-interpreter --max-iter 1000000 program.bas  # custom iteration limit
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="BASIC source file to run",
    )
    parser.add_argument(
        "-e", "--eval",
        help="Evaluate a one-liner BASIC statement",
        metavar="STATEMENT",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Trace line-by-line execution (show line numbers)",
    )
    parser.add_argument(
        "--max-iter",
        type=int,
        default=10_000_000,
        help="Maximum iteration count (default: 10,000,000)",
        metavar="N",
    )
    parser.add_argument(
        "--config",
        help="Path to configuration file (TOML/JSON)",
        metavar="FILE",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version="%(prog)s 3.0.0",
    )
    return parser


def repl(interp: Interpreter) -> None:
    """Run the interactive BASIC REPL.

    Supports commands: RUN, LIST, NEW, SAVE, LOAD, EDIT, DELETE, QUIT
    """
    interp.stdout.write("BASIC Interpreter v3.0\n")
    interp.stdout.write("Type HELP for a list of commands.\n")
    interp.stdout.write("> ")
    interp.stdout.flush()

    program_lines: dict[int, str] = {}

    try:
        while True:
            try:
                line = input()
            except EOFError:
                break

            line = line.strip()
            if not line:
                interp.stdout.write("> ")
                interp.stdout.flush()
                continue

            upper = line.upper().strip()

            if upper in ("QUIT", "EXIT", "SYSTEM"):
                break

            if upper == "HELP":
                interp.stdout.write("""\
Commands:
  RUN           - Run the loaded program
  LIST [n[-m]]  - List program lines (optionally filtered)
  NEW           - Clear program and variables
  SAVE filename - Save program to file
  LOAD filename - Load program from file
  EDIT n        - Edit line n
  DELETE n[-m]  - Delete line(s)
  QUIT          - Exit the REPL

BASIC statements:
  LET, PRINT, INPUT, IF/THEN/ELSE, FOR/NEXT, WHILE/WEND,
  DO/LOOP, GOTO, GOSUB/RETURN, DIM, READ/DATA/RESTORE,
  SELECT CASE, ON ERROR, DEF FN, and more.
""")
                interp.stdout.write("> ")
                interp.stdout.flush()
                continue

            if upper == "LIST":
                for ln in sorted(program_lines.keys()):
                    interp.stdout.write(f"{ln} {program_lines[ln]}\n")
                interp.stdout.write("> ")
                interp.stdout.flush()
                continue

            if upper.startswith("LIST"):
                rest = line[4:].strip()
                try:
                    if "-" in rest:
                        parts = rest.split("-", 1)
                        start = int(parts[0].strip())
                        end = int(parts[1].strip()) if parts[1].strip() else 99999
                    else:
                        start = int(rest.strip())
                        end = start
                    for ln in sorted(program_lines.keys()):
                        if start <= ln <= end:
                            interp.stdout.write(f"{ln} {program_lines[ln]}\n")
                except ValueError:
                    pass
                interp.stdout.write("> ")
                interp.stdout.flush()
                continue

            if upper == "RUN":
                source = "\n".join(f"{ln} {program_lines[ln]}" for ln in sorted(program_lines.keys()))
                try:
                    interp.load(source)
                    interp.run()
                except BasicError as e:
                    interp.stdout.write(f"Error: {e}\n")
                except BasicStopException:
                    interp.stdout.write("Break\n")
                interp.stdout.write("OK\n> ")
                interp.stdout.flush()
                continue

            if upper == "NEW":
                program_lines.clear()
                for f in interp._files.values():
                    f.close()
                interp = Interpreter()
                interp.stdout.write("OK\n> ")
                interp.stdout.flush()
                continue

            if upper.startswith("SAVE"):
                filename = line[4:].strip()
                if not filename:
                    interp.stdout.write("Usage: SAVE filename\n")
                else:
                    try:
                        with open(filename, "w") as f:
                            for ln in sorted(program_lines.keys()):
                                f.write(f"{ln} {program_lines[ln]}\n")
                        interp.stdout.write(f"Saved {len(program_lines)} lines to {filename}\n")
                    except OSError as e:
                        interp.stdout.write(f"Error: {e}\n")
                interp.stdout.write("> ")
                interp.stdout.flush()
                continue

            if upper.startswith("LOAD"):
                filename = line[4:].strip()
                if not filename:
                    interp.stdout.write("Usage: LOAD filename\n")
                else:
                    try:
                        with open(filename, "r") as f:
                            for raw in f:
                                raw = raw.rstrip()
                                match = re.match(r'^(\d+)\s+(.*)', raw)
                                if match:
                                    program_lines[int(match.group(1))] = match.group(2)
                        interp.stdout.write(f"Loaded {len(program_lines)} lines from {filename}\n")
                    except FileNotFoundError:
                        interp.stdout.write(f"File not found: {filename}\n")
                    except OSError as e:
                        interp.stdout.write(f"Error: {e}\n")
                interp.stdout.write("> ")
                interp.stdout.flush()
                continue

            if upper.startswith("DELETE"):
                rest = line[6:].strip()
                try:
                    if "-" in rest:
                        parts = rest.split("-", 1)
                        start = int(parts[0].strip())
                        end = int(parts[1].strip()) if parts[1].strip() else 99999
                        for ln in list(program_lines.keys()):
                            if start <= ln <= end:
                                del program_lines[ln]
                    else:
                        line_num = int(rest)
                        program_lines.pop(line_num, None)
                except ValueError:
                    interp.stdout.write("Usage: DELETE line or DELETE start-end\n")
                interp.stdout.write("> ")
                interp.stdout.flush()
                continue

            if upper.startswith("EDIT"):
                rest = line[4:].strip()
                try:
                    line_num = int(rest)
                    if line_num in program_lines:
                        interp.stdout.write(f"{line_num} {program_lines[line_num]}\n")
                        new_line = input("? ").strip()
                        if new_line:
                            program_lines[line_num] = new_line
                    else:
                        interp.stdout.write(f"Line {line_num} not found\n")
                except ValueError:
                    interp.stdout.write("Usage: EDIT line\n")
                interp.stdout.write("> ")
                interp.stdout.flush()
                continue

            match = re.match(r'^(\d+)\s+(.*)', line)
            if match:
                line_num = int(match.group(1))
                code = match.group(2)
                program_lines[line_num] = code
                interp.stdout.write("> ")
                interp.stdout.flush()
                continue

            if re.match(r'^\d+$', line):
                line_num = int(line)
                program_lines.pop(line_num, None)
                interp.stdout.write("> ")
                interp.stdout.flush()
                continue

            try:
                interp.load(line)
            except BasicError as e:
                interp.stdout.write(f"Error: {e}\n")
            interp.stdout.write("> ")
            interp.stdout.flush()
    except KeyboardInterrupt:
        interp.stdout.write("\n")

    for f in interp._files.values():
        try:
            f.close()
        except Exception:
            pass
    interp.stdout.write("Goodbye!\n")


def main() -> None:
    """Main entry point for the BASIC interpreter CLI."""
    parser = build_parser()
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.trace else logging.WARNING
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    # Load config file if specified
    from basic_interpreter.config import InterpreterConfig
    config = InterpreterConfig()
    if args.config:
        config = load_config(args.config)

    interp = Interpreter(config=config)
    interp.trace = args.trace
    interp.max_iterations = args.max_iter

    if args.eval:
        try:
            interp.load(args.eval)
        except BasicError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if args.file:
        try:
            with open(args.file, "r") as f:
                source = f.read()
        except FileNotFoundError:
            print(f"File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        try:
            interp.load(source)
            interp.run()
        except BasicError as e:
            line_num = interp.sorted_lines[interp.pc] if interp.pc < len(interp.sorted_lines) else "?"
            print(f"Error at line {line_num}: {e}", file=sys.stderr)
            sys.exit(1)
        except BasicStopException:
            print("Break")
        finally:
            for f in interp._files.values():
                try:
                    f.close()
                except Exception:
                    pass
        return

    repl(interp)


def load_config(path: str) -> InterpreterConfig:
    """Load configuration from a TOML or JSON file.

    Args:
        path: Path to the configuration file.

    Returns:
        InterpreterConfig with values from the file.
    """
    import json

    config = InterpreterConfig()

    try:
        with open(path, "r") as f:
            content = f.read()

        # Try TOML first (Python 3.11+ has tomllib)
        if path.endswith(".toml"):
            try:
                import tomllib
                data = tomllib.loads(content)
            except ImportError:
                try:
                    import tomli as tomllib
                    data = tomllib.loads(content)
                except ImportError:
                    # Fall back to simple parsing for basic sections
                    print("Warning: TOML support requires Python 3.11+ or tomli package. Using defaults.", file=sys.stderr)
                    return config
        else:
            data = json.loads(content)

        # Apply config values
        if "max_iterations" in data:
            config.max_iterations = int(data["max_iterations"])
        if "max_iter" in data:
            config.max_iterations = int(data["max_iter"])
        if "zone_width" in data:
            config.zone_width = int(data["zone_width"])
        if "trace" in data:
            config.trace = bool(data["trace"])
        if "random_seed" in data:
            config.random_seed = int(data["random_seed"]) if data["random_seed"] is not None else None

    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not load config from {path}: {e}", file=sys.stderr)

    return config


if __name__ == "__main__":
    main()