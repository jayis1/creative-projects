"""MiniLang bytecode virtual machine.

A stack-based interpreter with a mark-and-sweep garbage collector.

Design
------
* Each function call creates a new *frame* with its own operand stack and
  locals array.  This keeps the hot dispatch loop allocation-free in steady
  state (the stack is a pre-sized Python list).
* Heap objects (arrays, closures) are tracked by the GC.  The VM keeps a list
  of root objects (current frame's locals + stacks of parent frames).
* ``CALL`` looks up the function chunk by name (stored in the string pool),
  creates a new frame, copies arguments into locals 0..nparams-1, and jumps.
* ``RETURN`` pops the frame and pushes the return value (if any) onto the
  caller's stack.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .bytecode import Instruction, OpCode
from .errors import VMError
from .value import BoundFunc, Closure, Object, Value, ValueTag
from .compiler import CompiledProgram, Chunk


@dataclass
class Frame:
    """A single call frame."""
    chunk: Chunk
    pc: int = 0
    stack: list[Value] = field(default_factory=list)
    locals_: list[Value] = field(default_factory=list)
    caller: "Frame | None" = None
    return_pc: int = 0

    def __init__(self, chunk: Chunk, nlocals: int, caller: "Frame | None" = None,
                 return_pc: int = 0):
        self.chunk = chunk
        self.pc = 0
        self.stack: list[Value] = []
        self.locals_: list[Value] = [Value.nil()] * nlocals
        self.caller = caller
        self.return_pc = return_pc


class VM:
    """The MiniLang bytecode interpreter."""

    def __init__(self, program: CompiledProgram, debug: bool = False,
                 max_steps: int = 10_000_000, max_call_depth: int = 512):
        self.program = program
        self.debug = debug
        self.max_steps = max_steps
        self.max_call_depth = max_call_depth
        self.output: list[str] = []
        self.heap: list[Object] = []   # all allocated heap objects
        self.gc_threshold = 1024
        self._next_gc = 256
        self._builtins: dict[str, BoundFunc] = self._register_builtins()

    # ------------------------------------------------------------------ #
    # public API                                                          #
    # ------------------------------------------------------------------ #
    def run(self) -> Value:
        """Execute the main chunk and return the last top-of-stack value."""
        frame = Frame(self.program.main, self.program.main.nlocals)
        self._call_depth = 0
        return self._execute(frame)

    # ------------------------------------------------------------------ #
    # main dispatch loop                                                  #
    # ------------------------------------------------------------------ #
    def _execute(self, frame: Frame) -> Value:
        steps = 0
        last_value = Value.nil()
        while True:
            if steps > self.max_steps:
                raise VMError("step limit exceeded (infinite loop?)")
            steps += 1
            if frame.pc < 0 or frame.pc >= len(frame.chunk.code):
                raise VMError(f"pc out of range: {frame.pc}")
            ins = frame.chunk.code[frame.pc]
            frame.pc += 1
            op = ins.op

            if op == OpCode.PUSH_INT:
                frame.stack.append(Value.int(ins.operand))
            elif op == OpCode.PUSH_STR:
                frame.stack.append(Value.str_(self.program.strings[ins.operand]))
            elif op == OpCode.PUSH_BOOL:
                frame.stack.append(Value.bool_(bool(ins.operand)))
            elif op == OpCode.PUSH_NIL:
                frame.stack.append(Value.nil())
            elif op == OpCode.LOAD_LOCAL:
                self._check_local(frame, ins.operand)
                frame.stack.append(frame.locals_[ins.operand])
            elif op == OpCode.STORE_LOCAL:
                self._check_local(frame, ins.operand)
                if not frame.stack:
                    raise VMError("stack underflow on STORE_LOCAL")
                frame.locals_[ins.operand] = frame.stack.pop()
            elif op == OpCode.POP:
                if not frame.stack:
                    raise VMError("stack underflow on POP")
                frame.stack.pop()
            elif op == OpCode.ADD:
                b = self._pop(frame); a = self._pop(frame)
                if a.tag == ValueTag.INT and b.tag == ValueTag.INT:
                    frame.stack.append(Value.int(a.payload + b.payload))
                elif a.tag == ValueTag.STRING and b.tag == ValueTag.STRING:
                    frame.stack.append(Value.str_(a.payload + b.payload))
                else:
                    raise VMError(
                        f"'+' requires int+int or string+string, got {a.tag.name}, {b.tag.name}")
            elif op == OpCode.SUB:
                last_value = self._binop_int(frame, lambda a, b: a - b, "-")
            elif op == OpCode.MUL:
                last_value = self._binop_int(frame, lambda a, b: a * b, "*")
            elif op == OpCode.DIV:
                last_value = self._binop_int(frame, self._int_div, "/",
                                             check_zero=True)
            elif op == OpCode.MOD:
                last_value = self._binop_int(frame, self._int_mod, "%",
                                             check_zero=True)
            elif op == OpCode.NEG:
                v = self._pop(frame)
                if v.tag != ValueTag.INT:
                    raise VMError(f"unary '-' on {v.tag.name}")
                frame.stack.append(Value.int(-v.payload))
            elif op == OpCode.EQ:
                b = self._pop(frame); a = self._pop(frame)
                frame.stack.append(Value.bool_(a.equals(b)))
            elif op == OpCode.NEQ:
                b = self._pop(frame); a = self._pop(frame)
                frame.stack.append(Value.bool_(not a.equals(b)))
            elif op == OpCode.LT:
                b = self._pop(frame); a = self._pop(frame)
                self._check_comparable(a, b, "<")
                frame.stack.append(Value.bool_(a.payload < b.payload))
            elif op == OpCode.LE:
                b = self._pop(frame); a = self._pop(frame)
                self._check_comparable(a, b, "<=")
                frame.stack.append(Value.bool_(a.payload <= b.payload))
            elif op == OpCode.GT:
                b = self._pop(frame); a = self._pop(frame)
                self._check_comparable(a, b, ">")
                frame.stack.append(Value.bool_(a.payload > b.payload))
            elif op == OpCode.GE:
                b = self._pop(frame); a = self._pop(frame)
                self._check_comparable(a, b, ">=")
                frame.stack.append(Value.bool_(a.payload >= b.payload))
            elif op == OpCode.NOT:
                v = self._pop(frame)
                if v.tag != ValueTag.BOOL:
                    raise VMError(f"'!' on {v.tag.name}")
                frame.stack.append(Value.bool_(not v.payload))
            elif op == OpCode.AND or op == OpCode.OR:
                # These are handled by the compiler via short-circuit jumps,
                # so a direct AND/OR opcode should not appear.  But if it does:
                raise VMError("AND/OR should be compiled as short-circuit jumps")
            elif op == OpCode.JUMP:
                frame.pc = ins.operand
            elif op == OpCode.JUMP_IF_FALSE:
                v = self._pop(frame)
                if not v.is_truthy():
                    frame.pc = ins.operand
            elif op == OpCode.JUMP_IF_TRUE:
                v = self._pop(frame)
                if v.is_truthy():
                    frame.pc = ins.operand
            elif op == OpCode.NEW_ARRAY:
                count = ins.operand
                if len(frame.stack) < count:
                    raise VMError("stack underflow on NEW_ARRAY")
                if count > 0:
                    items = frame.stack[-count:]
                    del frame.stack[-count:]
                else:
                    items = []
                # Arrays are heap-allocated Python lists; track for GC.
                self.heap.append(items)  # type: ignore[arg-type]
                frame.stack.append(Value.array(items))
            elif op == OpCode.INDEX_GET:
                idx = self._pop(frame)
                arr_v = self._pop(frame)
                if arr_v.tag != ValueTag.ARRAY:
                    raise VMError(f"cannot index {arr_v.tag.name}")
                if idx.tag != ValueTag.INT:
                    raise VMError("index must be int")
                items = arr_v.payload
                i = idx.payload
                if i < 0 or i >= len(items):
                    raise VMError(f"index {i} out of bounds (len {len(items)})")
                frame.stack.append(items[i])
            elif op == OpCode.INDEX_SET:
                val = self._pop(frame)
                idx = self._pop(frame)
                arr_v = self._pop(frame)
                if arr_v.tag != ValueTag.ARRAY:
                    raise VMError(f"cannot index {arr_v.tag.name}")
                if idx.tag != ValueTag.INT:
                    raise VMError("index must be int")
                items = arr_v.payload
                i = idx.payload
                if i < 0 or i >= len(items):
                    raise VMError(f"index {i} out of bounds (len {len(items)})")
                items[i] = val
            elif op == OpCode.CALL:
                # Operand encodes arg_count and name index.
                arg_count = ins.operand // 10000
                name_idx = ins.operand % 10000
                name = self.program.strings[name_idx]
                # Strip "call:" prefix.
                func_name = name[5:] if name.startswith("call:") else name
                if func_name in self._builtins:
                    bf = self._builtins[func_name]
                    if bf.arity != -1 and arg_count != bf.arity:
                        raise VMError(
                            f"builtin {func_name} expects {bf.arity} args, "
                            f"got {arg_count}")
                    if arg_count > 0:
                        args = frame.stack[-arg_count:]
                        del frame.stack[-arg_count:]
                    else:
                        args = []
                    result = bf.fn(args)
                    frame.stack.append(result)
                    last_value = result
                    continue
                if func_name not in self.program.functions:
                    raise VMError(f"unknown function {func_name!r}")
                chunk = self.program.functions[func_name]
                if arg_count != chunk.nparams:
                    raise VMError(
                        f"function {func_name} expects {chunk.nparams} args, "
                        f"got {arg_count}")
                # Pop args, create new frame.
                if arg_count > 0:
                    args = frame.stack[-arg_count:]
                    del frame.stack[-arg_count:]
                else:
                    args = []
                # Call depth limit — prevents Python stack overflow on
                # deep recursion before the step limit can trigger.
                self._call_depth += 1
                if self._call_depth > self.max_call_depth:
                    raise VMError(
                        f"call depth limit exceeded ({self.max_call_depth}) — "
                        f"likely infinite recursion")
                new_frame = Frame(chunk, max(chunk.nlocals, chunk.nparams),
                                  caller=frame, return_pc=frame.pc)
                for i, v in enumerate(args):
                    new_frame.locals_[i] = v
                frame = new_frame
            elif op == OpCode.RETURN:
                has_val = ins.operand == 1
                ret_val = Value.nil()
                if has_val:
                    ret_val = self._pop(frame)
                # Decrement call depth as we return to caller.
                if self._call_depth > 0:
                    self._call_depth -= 1
                if frame.caller is None:
                    return ret_val
                caller = frame.caller
                caller.pc = frame.return_pc
                if has_val:
                    caller.stack.append(ret_val)
                frame = caller
                last_value = ret_val
            elif op == OpCode.PRINT:
                v = self._pop(frame)
                s = v.display()
                self.output.append(s)
                print(s)
            elif op == OpCode.HALT:
                return last_value
            elif op == OpCode.TRACE:
                v = self._pop(frame)
                self.output.append(v.display())
                last_value = v
            else:
                raise VMError(f"unknown opcode {op.name}")

            # Garbage-collect if heap is large enough.
            if len(self.heap) > self._next_gc:
                self._gc(frame)

    # ------------------------------------------------------------------ #
    # helpers                                                             #
    # ------------------------------------------------------------------ #
    def _pop(self, frame: Frame) -> Value:
        if not frame.stack:
            raise VMError("stack underflow")
        return frame.stack.pop()

    def _check_local(self, frame: Frame, slot: int) -> None:
        if slot < 0 or slot >= len(frame.locals_):
            raise VMError(f"local slot {slot} out of range (have {len(frame.locals_)})")

    @staticmethod
    def _int_div(a: int, b: int) -> int:
        """Truncate-toward-zero integer division (C/Java/Rust semantics).

        Python's ``//`` floors toward negative infinity, but most languages
        truncate toward zero.  ``-7 / 2`` should be ``-3``, not ``-4``.
        """
        q = abs(a) // abs(b)
        if (a < 0) != (b < 0):
            return -q
        return q

    @staticmethod
    def _int_mod(a: int, b: int) -> int:
        """Modulo consistent with truncate-toward-zero division.

        ``a % b`` satisfies ``a == (a // b) * b + (a % b)`` under our
        truncating division, so the sign of the result matches the dividend.
        """
        return a - VM._int_div(a, b) * b

    def _binop_int(self, frame: Frame, fn, opname: str, check_zero: bool = False) -> Value:
        b = self._pop(frame)
        a = self._pop(frame)
        self._check_int_pair(a, b, opname)
        if check_zero and b.payload == 0:
            raise VMError(f"division by zero in {opname}")
        result = fn(a.payload, b.payload)
        v = Value.int(result)
        frame.stack.append(v)
        return v

    @staticmethod
    def _check_int_pair(a: Value, b: Value, opname: str) -> None:
        if a.tag != ValueTag.INT or b.tag != ValueTag.INT:
            raise VMError(f"{opname} requires int operands, got {a.tag.name}, {b.tag.name}")

    @staticmethod
    def _check_comparable(a: Value, b: Value, opname: str) -> None:
        """Check that a and b are both int or both string for comparison."""
        if a.tag == ValueTag.INT and b.tag == ValueTag.INT:
            return
        if a.tag == ValueTag.STRING and b.tag == ValueTag.STRING:
            return
        raise VMError(
            f"{opname} requires int or string operands, got {a.tag.name}, {b.tag.name}")

    def _track(self, obj: Object) -> None:
        self.heap.append(obj)

    # ------------------------------------------------------------------ #
    # garbage collector                                                   #
    # ------------------------------------------------------------------ #
    def _gc(self, frame: Frame) -> None:
        """Mark-and-sweep: mark from all live frames, sweep the rest."""
        # Collect roots: all locals and stack values across the call chain.
        marked: set[int] = set()

        def mark_value(v: Value) -> None:
            if v.tag == ValueTag.ARRAY:
                arr_id = id(v.payload)
                if arr_id in marked:
                    return
                marked.add(arr_id)
                for item in v.payload:
                    mark_value(item)
            elif v.tag == ValueTag.CLOSURE:
                cl_id = id(v.payload)
                if cl_id in marked:
                    return
                marked.add(cl_id)
                for uv in v.payload.upvalues:
                    mark_value(uv)

        f = frame
        while f is not None:
            for v in f.locals_:
                mark_value(v)
            for v in f.stack:
                mark_value(v)
            f = f.caller

        # Sweep.
        before = len(self.heap)
        self.heap = [o for o in self.heap if id(o) in marked]
        collected = before - len(self.heap)
        if self.debug:
            print(f"[gc] collected {collected} objects, "
                  f"{len(self.heap)} remaining")
        # Grow threshold exponentially.
        self._next_gc = max(256, len(self.heap) * 2)

    # ------------------------------------------------------------------ #
    # builtins                                                            #
    # ------------------------------------------------------------------ #
    def _register_builtins(self) -> dict[str, BoundFunc]:
        builtins: dict[str, BoundFunc] = {}

        def _print(args: list[Value]) -> Value:
            v = args[0]
            s = v.display()
            self.output.append(s)
            print(s)
            return Value.nil()

        def _len(args: list[Value]) -> Value:
            v = args[0]
            if v.tag == ValueTag.ARRAY:
                return Value.int(len(v.payload))
            if v.tag == ValueTag.STRING:
                return Value.int(len(v.payload))
            raise VMError(f"len() expects array or string, got {v.tag.name}")

        def _push(args: list[Value]) -> Value:
            arr_v, item = args[0], args[1]
            if arr_v.tag != ValueTag.ARRAY:
                raise VMError("push() expects an array")
            arr_v.payload.append(item)
            return Value.nil()

        def _str(args: list[Value]) -> Value:
            return Value.str_(args[0].display())

        def _int(args: list[Value]) -> Value:
            v = args[0]
            if v.tag == ValueTag.INT:
                return v
            if v.tag == ValueTag.STRING:
                try:
                    return Value.int(int(v.payload))
                except ValueError:
                    raise VMError(f"cannot convert {v.payload!r} to int")
            if v.tag == ValueTag.BOOL:
                return Value.int(1 if v.payload else 0)
            raise VMError(f"cannot convert {v.tag.name} to int")

        def _abs(args: list[Value]) -> Value:
            v = args[0]
            if v.tag != ValueTag.INT:
                raise VMError(f"abs() expects int, got {v.tag.name}")
            return Value.int(abs(v.payload))

        def _max(args: list[Value]) -> Value:
            a, b = args[0], args[1]
            if a.tag != ValueTag.INT or b.tag != ValueTag.INT:
                raise VMError("max() expects int")
            return Value.int(max(a.payload, b.payload))

        def _min(args: list[Value]) -> Value:
            a, b = args[0], args[1]
            if a.tag != ValueTag.INT or b.tag != ValueTag.INT:
                raise VMError("min() expects int")
            return Value.int(min(a.payload, b.payload))

        def _assert(args: list[Value]) -> Value:
            v = args[0]
            if v.tag != ValueTag.BOOL:
                raise VMError("assert() expects bool")
            if not v.payload:
                if len(args) > 1 and args[1].tag == ValueTag.STRING:
                    raise VMError(f"assertion failed: {args[1].payload}")
                raise VMError("assertion failed")
            return Value.nil()

        # ---- string manipulation builtins ---- #

        def _upper(args: list[Value]) -> Value:
            v = args[0]
            if v.tag != ValueTag.STRING:
                raise VMError(f"upper() expects string, got {v.tag.name}")
            return Value.str_(v.payload.upper())

        def _lower(args: list[Value]) -> Value:
            v = args[0]
            if v.tag != ValueTag.STRING:
                raise VMError(f"lower() expects string, got {v.tag.name}")
            return Value.str_(v.payload.lower())

        def _contains(args: list[Value]) -> Value:
            s, sub = args[0], args[1]
            if s.tag != ValueTag.STRING or sub.tag != ValueTag.STRING:
                raise VMError("contains() expects two strings")
            return Value.bool_(sub.payload in s.payload)

        def _slice(args: list[Value]) -> Value:
            s, start, end = args[0], args[1], args[2]
            if s.tag != ValueTag.STRING:
                raise VMError(f"slice() expects string, got {s.tag.name}")
            if start.tag != ValueTag.INT or end.tag != ValueTag.INT:
                raise VMError("slice() start/end must be int")
            st = max(0, start.payload)
            en = min(len(s.payload), end.payload)
            if st > en:
                return Value.str_("")
            return Value.str_(s.payload[st:en])

        def _charat(args: list[Value]) -> Value:
            s, idx = args[0], args[1]
            if s.tag != ValueTag.STRING:
                raise VMError(f"charAt() expects string, got {s.tag.name}")
            if idx.tag != ValueTag.INT:
                raise VMError("charAt() index must be int")
            i = idx.payload
            if i < 0 or i >= len(s.payload):
                raise VMError(f"charAt index {i} out of bounds (len {len(s.payload)})")
            return Value.str_(s.payload[i])

        def _split(args: list[Value]) -> Value:
            s, sep = args[0], args[1]
            if s.tag != ValueTag.STRING or sep.tag != ValueTag.STRING:
                raise VMError("split() expects two strings")
            parts = s.payload.split(sep.payload)
            items = [Value.str_(p) for p in parts]
            self.heap.append(items)
            return Value.array(items)

        # ---- array manipulation builtins ---- #

        def _pop(args: list[Value]) -> Value:
            arr_v = args[0]
            if arr_v.tag != ValueTag.ARRAY:
                raise VMError(f"pop() expects array, got {arr_v.tag.name}")
            if not arr_v.payload:
                raise VMError("pop() on empty array")
            return arr_v.payload.pop()

        def _reverse(args: list[Value]) -> Value:
            arr_v = args[0]
            if arr_v.tag != ValueTag.ARRAY:
                raise VMError(f"reverse() expects array, got {arr_v.tag.name}")
            items = list(reversed(arr_v.payload))
            self.heap.append(items)
            return Value.array(items)

        def _concat(args: list[Value]) -> Value:
            a, b = args[0], args[1]
            if a.tag != ValueTag.ARRAY or b.tag != ValueTag.ARRAY:
                raise VMError("concat() expects two arrays")
            items = list(a.payload) + list(b.payload)
            self.heap.append(items)
            return Value.array(items)

        def _find(args: list[Value]) -> Value:
            arr_v, target = args[0], args[1]
            if arr_v.tag != ValueTag.ARRAY:
                raise VMError(f"find() expects array, got {arr_v.tag.name}")
            for i, item in enumerate(arr_v.payload):
                if item.equals(target):
                    return Value.int(i)
            return Value.int(-1)

        def _sort(args: list[Value]) -> Value:
            arr_v = args[0]
            if arr_v.tag != ValueTag.ARRAY:
                raise VMError(f"sort() expects array, got {arr_v.tag.name}")
            # Sort a copy so the original is not mutated.
            items = sorted(arr_v.payload, key=lambda v: v.payload)
            self.heap.append(items)
            return Value.array(items)

        def _sum(args: list[Value]) -> Value:
            arr_v = args[0]
            if arr_v.tag != ValueTag.ARRAY:
                raise VMError(f"sum() expects array, got {arr_v.tag.name}")
            total = 0
            for item in arr_v.payload:
                if item.tag != ValueTag.INT:
                    raise VMError("sum() requires array of ints")
                total += item.payload
            return Value.int(total)

        # ---- type introspection ---- #

        def _typeof(args: list[Value]) -> Value:
            v = args[0]
            names = {
                ValueTag.INT: "int",
                ValueTag.STRING: "string",
                ValueTag.BOOL: "bool",
                ValueTag.NIL: "unit",
                ValueTag.ARRAY: "array",
                ValueTag.CLOSURE: "fn",
                ValueTag.BOUND: "fn",
            }
            return Value.str_(names.get(v.tag, "unknown"))

        # ---- time builtin ---- #

        def _time(args: list[Value]) -> Value:
            import time as _time
            return Value.int(int(_time.time()))

        # ---- random builtin ---- #

        def _randint(args: list[Value]) -> Value:
            import random as _random
            a, b = args[0], args[1]
            if a.tag != ValueTag.INT or b.tag != ValueTag.INT:
                raise VMError("randint() expects two int args")
            return Value.int(_random.randint(a.payload, b.payload))

        def _random(args: list[Value]) -> Value:
            import random as _random
            return Value.int(_random.randint(0, args[0].payload - 1)) if args else Value.int(0)

        builtins["print"] = BoundFunc("print", 1, _print)
        builtins["len"] = BoundFunc("len", 1, _len)
        builtins["push"] = BoundFunc("push", 2, _push)
        builtins["str"] = BoundFunc("str", 1, _str)
        builtins["int"] = BoundFunc("int", 1, _int)
        builtins["abs"] = BoundFunc("abs", 1, _abs)
        builtins["max"] = BoundFunc("max", 2, _max)
        builtins["min"] = BoundFunc("min", 2, _min)
        builtins["assert"] = BoundFunc("assert", -1, _assert)  # variable arity
        # String builtins
        builtins["upper"] = BoundFunc("upper", 1, _upper)
        builtins["lower"] = BoundFunc("lower", 1, _lower)
        builtins["contains"] = BoundFunc("contains", 2, _contains)
        builtins["slice"] = BoundFunc("slice", 3, _slice)
        builtins["charAt"] = BoundFunc("charAt", 2, _charat)
        builtins["split"] = BoundFunc("split", 2, _split)
        # Array builtins
        builtins["pop"] = BoundFunc("pop", 1, _pop)
        builtins["reverse"] = BoundFunc("reverse", 1, _reverse)
        builtins["concat"] = BoundFunc("concat", 2, _concat)
        builtins["find"] = BoundFunc("find", 2, _find)
        builtins["sort"] = BoundFunc("sort", 1, _sort)
        builtins["sum"] = BoundFunc("sum", 1, _sum)
        # Type introspection
        builtins["typeof"] = BoundFunc("typeof", 1, _typeof)
        # Utility
        builtins["time"] = BoundFunc("time", 0, _time)
        builtins["randint"] = BoundFunc("randint", 2, _randint)
        return builtins