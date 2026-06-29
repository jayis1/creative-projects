"""Control-flow words: IF/ELSE/THEN, BEGIN/UNTIL, BEGIN/WHILE/REPEAT, AGAIN,
DO/LOOP, DO/+LOOP, LEAVE, EXIT, RECURSE, I, J."""

from forth.core import ForthError, _ExitBody, _NextIdx
from forth.builtins._helpers import NativeFn


def register_control_flow(i) -> None:
    """Register control-flow words on *i*."""

    # ── IF / ELSE / THEN ──
    def _if(i, t, n):
        i.current_def.append(["if", None])
        i.return_stack.append(("if-fixup", len(i.current_def) - 1))
        return n + 1
    i.reg("IF", _if, immediate=True, doc="IF ( flag -- )")

    def _else(i, t, n):
        if not i.return_stack or i.return_stack[-1][0] != "if-fixup":
            raise ForthError("ELSE without IF")
        if_pos = i.return_stack.pop()[1]
        i.current_def.append(["jump", None])
        jump_pos = len(i.current_def) - 1
        i.current_def[if_pos][1] = len(i.current_def)
        i.return_stack.append(("if-fixup", jump_pos))
        return n + 1
    i.reg("ELSE", _else, immediate=True, doc="ELSE")

    def _then(i, t, n):
        if not i.return_stack or i.return_stack[-1][0] != "if-fixup":
            raise ForthError("THEN without IF")
        pos = i.return_stack.pop()[1]
        i.current_def[pos][1] = len(i.current_def)
        return n + 1
    i.reg("THEN", _then, immediate=True, doc="THEN")

    # ── BEGIN / UNTIL / WHILE / REPEAT / AGAIN ──
    def _begin(i, t, n):
        i.return_stack.append(("begin", len(i.current_def)))
        return n + 1
    i.reg("BEGIN", _begin, immediate=True, doc="BEGIN")

    def _until(i, t, n):
        if not i.return_stack or i.return_stack[-1][0] != "begin":
            raise ForthError("UNTIL without BEGIN")
        begin_pos = i.return_stack.pop()[1]
        i.current_def.append(["until", begin_pos])
        return n + 1
    i.reg("UNTIL", _until, immediate=True, doc="UNTIL")

    def _while(i, t, n):
        if not i.return_stack or i.return_stack[-1][0] != "begin":
            raise ForthError("WHILE without BEGIN")
        i.current_def.append(["while", None])
        i.return_stack.append(("while-fixup", len(i.current_def) - 1))
        return n + 1
    i.reg("WHILE", _while, immediate=True, doc="WHILE")

    def _repeat(i, t, n):
        if not i.return_stack or i.return_stack[-1][0] != "while-fixup":
            raise ForthError("REPEAT without WHILE")
        while_pos = i.return_stack.pop()[1]
        if not i.return_stack or i.return_stack[-1][0] != "begin":
            raise ForthError("REPEAT without BEGIN")
        begin_pos = i.return_stack.pop()[1]
        i.current_def.append(["jump", begin_pos])
        i.current_def[while_pos][1] = len(i.current_def)
        return n + 1
    i.reg("REPEAT", _repeat, immediate=True, doc="REPEAT")

    def _again(i, t, n):
        if not i.return_stack or i.return_stack[-1][0] != "begin":
            raise ForthError("AGAIN without BEGIN")
        begin_pos = i.return_stack.pop()[1]
        i.current_def.append(["jump", begin_pos])
        return n + 1
    i.reg("AGAIN", _again, immediate=True, doc="AGAIN")

    # ── DO / LOOP / +LOOP / LEAVE ──
    def _do(i, t, n):
        i.current_def.append(["do", None])
        i.return_stack.append(("do-fixup", len(i.current_def) - 1))
        i.return_stack.append(("do-leave", []))
        return n + 1
    i.reg("DO", _do, immediate=True, doc="DO")

    def _loop(i, t, n):
        if not i.return_stack or i.return_stack[-1][0] != "do-leave":
            raise ForthError("LOOP without DO")
        leave_positions = i.return_stack.pop()[1]
        if not i.return_stack or i.return_stack[-1][0] != "do-fixup":
            raise ForthError("LOOP without DO")
        do_pos = i.return_stack.pop()[1]
        i.current_def.append(["loop", do_pos + 1])
        i.current_def[do_pos][1] = len(i.current_def)
        for lp in leave_positions:
            i.current_def[lp][1] = len(i.current_def)
        return n + 1
    i.reg("LOOP", _loop, immediate=True, doc="LOOP")

    def _plus_loop(i, t, n):
        if not i.return_stack or i.return_stack[-1][0] != "do-leave":
            raise ForthError("+LOOP without DO")
        leave_positions = i.return_stack.pop()[1]
        if not i.return_stack or i.return_stack[-1][0] != "do-fixup":
            raise ForthError("+LOOP without DO")
        do_pos = i.return_stack.pop()[1]
        i.current_def.append(["plusloop", do_pos + 1])
        i.current_def[do_pos][1] = len(i.current_def)
        for lp in leave_positions:
            i.current_def[lp][1] = len(i.current_def)
        return n + 1
    i.reg("+LOOP", _plus_loop, immediate=True, doc="+LOOP")

    def _leave(i, t, n):
        found = False
        for item in i.return_stack:
            if isinstance(item, tuple) and item[0] == "do-leave":
                found = True
                break
        if not found:
            raise ForthError("LEAVE outside DO")
        i.current_def.append(["leave", None])
        for k in range(len(i.return_stack) - 1, -1, -1):
            item = i.return_stack[k]
            if isinstance(item, tuple) and item[0] == "do-leave":
                i.return_stack[k] = ("do-leave", item[1] + [len(i.current_def) - 1])
                break
        return n + 1
    i.reg("LEAVE", _leave, immediate=True, doc="LEAVE")

    # ── EXIT ──
    def _exit(i, t, n):
        raise _ExitBody()
    i.reg("EXIT", _exit, doc="Return from word")

    # ── RECURSE ──
    def _recurse(i, t, n):
        i.current_def.append(["call", i.current_name.upper()])
        return n + 1
    i.reg("RECURSE", _recurse, immediate=True, doc="Recursive self-call")

    # ── loop index access ──
    def _i(i, t, n):
        state = i._find_loop_state()
        if state is None:
            raise ForthError("I outside DO loop")
        i.push(state[1])
    i.reg("I", _i, doc="Loop index")

    def _j(i, t, n):
        count = 0
        for item in reversed(i.return_stack):
            if isinstance(item, list) and item and item[0] == "loop-state":
                count += 1
                if count == 2:
                    i.push(item[1])
                    return
        raise ForthError("J outside nested DO loop")
    i.reg("J", _j, doc="Outer loop index")

    # ── UNLOOP — remove loop state without incrementing (for EXIT inside loops) ──
    def _unloop(i, t, n):
        i._pop_loop_state()
    i.reg("UNLOOP", _unloop, doc="Remove innermost loop state")