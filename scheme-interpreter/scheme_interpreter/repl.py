"""Interactive REPL for the Scheme interpreter."""

from __future__ import annotations

import sys
from .interpreter import Interpreter, SchemeError, SchemeExit
from .parser import ParseError
from .lexer import LexError
from .types import scheme_repr, scheme_display, Unspecified, is_true


PROMPT = "scheme> "
CONT_PROMPT = "... "


def run_repl(infile=None):
    """Run the read-eval-print loop."""
    interp = Interpreter()
    from .primitives import set_global_interpreter
    set_global_interpreter(interp)

    inp = infile or sys.stdin
    out = sys.stdout

    # Multi-line buffer: accumulate input until we have complete forms
    buffer = ""

    while True:
        try:
            if buffer:
                out.write(CONT_PROMPT)
            else:
                out.write(PROMPT)
            out.flush()
            line = inp.readline()
            if not line:
                break
            buffer += line
            # Try to parse all complete forms
            try:
                from .parser import parse
                forms = parse(buffer)
            except (ParseError, LexError):
                # Incomplete input — keep reading
                continue
            except Exception:
                # Other parse errors — show and reset
                out.write(f"Error: parsing failed\n")
                buffer = ""
                continue
            buffer = ""
            for form in forms:
                try:
                    result = interp.eval_form(form)
                    if result is not Unspecified and result is not None:
                        out.write(scheme_repr(result) + "\n")
                except SchemeExit as e:
                    return e.code
                except SchemeError as e:
                    out.write(f"Error: {e}\n")
                except ParseError as e:
                    out.write(f"ParseError: {e}\n")
                except LexError as e:
                    out.write(f"LexError: {e}\n")
                except RecursionError:
                    out.write("Error: maximum recursion depth exceeded\n")
                except Exception as e:
                    out.write(f"Error: {e}\n")
        except KeyboardInterrupt:
            out.write("\n")
            buffer = ""
            continue
        except EOFError:
            break
    out.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(run_repl())