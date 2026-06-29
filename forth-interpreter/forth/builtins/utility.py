"""Utility words: WORDS, SEE, FORGET, BYE, TRUE, FALSE, WORDS-CATEGORIZED, STACK-DUMP, RESET."""

import sys

from forth.core import ForthError, _NextIdx


def register_utility_words(i) -> None:
    """Register utility words on *i*."""

    def _words(i, t, n):
        ws = sorted(w.name for w in i.words.values() if not w.hidden)
        i.emit(" ".join(ws) + "\n")
    i.reg("WORDS", _words, doc="List words")

    # WORDS-COUNT ( -- n )  Push number of defined words
    def _words_count(i, t, n):
        count = sum(1 for w in i.words.values() if not w.hidden)
        i.push(count)
    i.reg("WORDS-COUNT", _words_count, doc="Push number of defined words")

    def _see(i, t, n):
        if n + 1 >= len(t):
            raise ForthError("SEE needs a name")
        name = t[n + 1].upper()
        w = i.lookup(name)
        if w is None:
            raise ForthError(f"unknown word: {name}")
        i.emit(f": {name} ")
        if w.native is not None:
            i.emit("(native)")
            if w.doc:
                i.emit(f"  \\ {w.doc}")
        else:
            for d in w.data:
                if d[0] == "lit":
                    i.emit(f"{d[1]} ")
                elif d[0] == "call":
                    i.emit(f"{d[1]} ")
                else:
                    i.emit(f"{d[0]} ")
        i.emit(";\n")
        return _NextIdx(n + 2)
    i.reg("SEE", _see, doc="Decompile word")

    def _forget(i, t, n):
        if n + 1 >= len(t):
            raise ForthError("FORGET needs a name")
        name = t[n + 1].upper()
        if name in i.words:
            del i.words[name]
        if name in i.variables:
            del i.variables[name]
        return _NextIdx(n + 2)
    i.reg("FORGET", _forget, doc="Remove word")

    def _bye(i, t, n):
        raise SystemExit(0)
    i.reg("BYE", _bye, doc="Exit")

    # ── boolean helpers ──
    i.reg("TRUE", lambda i, t, n: i.push(-1), doc="Push true (-1)")
    i.reg("FALSE", lambda i, t, n: i.push(0), doc="Push false (0)")

    # ── RESET — clear stack and return stack ──
    def _reset(i, t, n):
        i.stack.clear()
        i.return_stack.clear()
    i.reg("RESET", _reset, doc="Clear all stacks")

    # ── VERSION — print interpreter version ──
    def _version(i, t, n):
        from forth import __version__
        i.emit(f"Forth {__version__}\n")
    i.reg("VERSION", _version, doc="Print version")

    # ── .S-DETAILED — show stack with types ──
    def _dots_detailed(i, t, n):
        parts = []
        for v in i.stack:
            if isinstance(v, str):
                parts.append(f'"{v}"')
            elif isinstance(v, float):
                parts.append(f"{v:g}")
            else:
                parts.append(str(v))
        i.emit("<" + " ".join(parts) + ">\n")
    i.reg(".S!", _dots_detailed, doc="Show stack with types")

    # ── TIME — push current time in seconds (float) ──
    def _time(i, t, n):
        import time
        i.push(time.time())
    i.reg("TIME", _time, doc="Push Unix epoch time (float)")

    # ── CLOCK — push elapsed milliseconds (approx) ──
    def _clock(i, t, n):
        import time
        i.push(int(time.time() * 1000) & 0x7FFFFFFF)
    i.reg("CLOCK", _clock, doc="Push millisecond clock")

    # ── SEED — set random seed ──
    def _seed(i, t, n):
        import random
        seed = i.pop_int()
        random.seed(seed)
    i.reg("SEED", _seed, doc="Set random seed ( n -- )")

    # ── RANDOM — push random int in [0, n) ──
    def _random(i, t, n):
        import random
        limit = i.pop_int()
        if limit <= 0:
            raise ForthError("RANDOM needs positive limit")
        i.push(random.randint(0, limit - 1))
    i.reg("RANDOM", _random, doc="Push random int [0, n) ( n -- rand )")