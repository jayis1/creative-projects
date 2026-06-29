"""CASE/OF/ENDOF/ENDCASE words."""

from forth.core import ForthError


def register_case_ops(i) -> None:
    """Register CASE/OF/ENDOF/ENDCASE on *i*."""

    def _case(i, t, n):
        """CASE ( n -- )  Start a case statement."""
        i.return_stack.append(("case", []))
        return n + 1
    i.reg("CASE", _case, immediate=True, doc="CASE statement")

    def _of(i, t, n):
        """OF ( test -- )  Compare case_val with test; if equal, run body."""
        i.current_def.append(["call", "OVER"])
        i.current_def.append(["call", "="])
        i.current_def.append(["if", None])
        i.return_stack.append(("of-fixup", len(i.current_def) - 1))
        i.current_def.append(["call", "DROP"])
        return n + 1
    i.reg("OF", _of, immediate=True, doc="OF clause")

    def _endof(i, t, n):
        """ENDOF — end of an OF clause, jump past ENDCASE."""
        if not i.return_stack or i.return_stack[-1][0] != "of-fixup":
            raise ForthError("ENDOF without OF")
        if_pos = i.return_stack.pop()[1]
        i.current_def.append(["jump", None])
        jump_pos = len(i.current_def) - 1
        i.current_def[if_pos][1] = len(i.current_def)
        if i.return_stack and i.return_stack[-1][0] == "case":
            i.return_stack[-1][1].append(jump_pos)
        return n + 1
    i.reg("ENDOF", _endof, immediate=True, doc="ENDOF clause")

    def _endcase(i, t, n):
        """ENDCASE — end of case statement, drop the case value."""
        if i.return_stack and i.return_stack[-1][0] == "case":
            drop_pos = len(i.current_def)
            for pos in i.return_stack[-1][1]:
                i.current_def[pos][1] = drop_pos + 1  # jump past DROP
            i.return_stack.pop()
        i.current_def.append(["call", "DROP"])
        return n + 1
    i.reg("ENDCASE", _endcase, immediate=True, doc="ENDCASE")