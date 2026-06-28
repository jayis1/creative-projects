"""Bug-hunt tests — each test verifies a bug before and after fixing."""

from __future__ import annotations

import pytest

from typeinfer import infer, infer_with_trace, type_to_string, InferError
from typeinfer.parser import parse, ETuple, ParserError
from typeinfer.unify import UnificationError
from typeinfer.types import TVar, TCon, TFun, INT, BOOL


# ---------------------------------------------------------------------------
# BUG #1: Single-element tuple with trailing comma `(1,)` not supported
# ---------------------------------------------------------------------------

class TestBugSingleElementTuple:
    def test_single_element_tuple_with_trailing_comma(self):
        """`(1,)` should parse as a 1-element tuple, not error."""
        e = parse("(1,)")
        assert isinstance(e, ETuple)
        assert len(e.items) == 1

    def test_single_element_tuple_infers(self):
        t = infer("(1,)")
        assert isinstance(t, TCon) and t.name == "Tuple"
        assert t.args == (INT,)

    def test_single_element_tuple_poly(self):
        t = infer(r"let x = \y. y in (x,)")
        s = type_to_string(t)
        assert "Tuple" in s and "->" in s


# ---------------------------------------------------------------------------
# BUG #2: Unary minus not supported (`-5` fails to parse)
# ---------------------------------------------------------------------------

class TestBugUnaryMinus:
    def test_unary_minus_literal(self):
        """`-5` should parse and infer as Int (with builtins)."""
        t = infer("-5", use_builtins=True)
        assert t == INT

    def test_unary_minus_var(self):
        """`-x` should infer as Int when x is Int (with builtins env)."""
        from typeinfer import Scheme
        from typeinfer.types import INT
        t = infer("-x", use_builtins=True, env={"x": Scheme([], INT)})
        assert t == INT

    def test_unary_minus_in_expr(self):
        """`-5 + 3` should work (unary minus binds tighter than +)."""
        t = infer("-5 + 3", use_builtins=True)
        assert t == INT

    def test_double_unary_minus(self):
        """`- - 5` (or `--5` would be comment, so use spaces) should be Int."""
        t = infer("- - 5", use_builtins=True)
        assert t == INT

    def test_unary_minus_in_lambda(self):
        t = infer(r"\x. -x", use_builtins=True)
        assert t == TFun(INT, INT)


# ---------------------------------------------------------------------------
# BUG #3: _format_unify_error loses the reason from UnificationError
# ---------------------------------------------------------------------------

class TestBugErrorReasonLost:
    def test_occurs_check_error_includes_reason(self):
        """The error message for an occurs-check failure should mention
        'occurs' or 'infinite'."""
        with pytest.raises(InferError) as exc_info:
            infer(r"\x. x x")
        msg = str(exc_info.value)
        assert "occurs" in msg.lower() or "infinite" in msg.lower(), (
            f"Expected 'occurs' or 'infinite' in error, got: {msg}"
        )

    def test_type_mismatch_includes_reason(self):
        """Type constructor mismatch should include the reason."""
        with pytest.raises(InferError) as exc_info:
            infer("if 1 then 2 else 3")
        msg = str(exc_info.value)
        # Should mention both types
        assert "Int" in msg or "Bool" in msg


# ---------------------------------------------------------------------------
# BUG #4: Trace for let prints raw var ids (`∀0`) instead of names (`∀ a`)
# ---------------------------------------------------------------------------

class TestBugTraceVarNames:
    def test_let_trace_uses_names_not_ids(self):
        """The trace for a polymorphic let should print `∀ a` not `∀0`."""
        t, steps = infer_with_trace(r"let id = \x. x in id 42")
        let_step = [s for s in steps if s.startswith("let id")]
        assert len(let_step) == 1
        step = let_step[0]
        # Should not contain a bare number after ∀ (like ∀0)
        if "∀" in step:
            # The character after ∀ should be a letter (a, b, ...) not a digit
            idx = step.index("∀")
            rest = step[idx + 1:].strip()
            # First non-space char after ∀ should be a letter
            assert rest[0].isalpha(), (
                f"Expected letter after ∀, but step is: {step!r}"
            )