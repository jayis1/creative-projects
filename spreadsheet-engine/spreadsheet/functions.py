"""
Built-in functions for the spreadsheet engine.

All functions accept evaluated argument values (already-resolved to
Python types) and return a Python scalar / CellError.

Value conventions:
  - Numbers are float or int
  - Strings are str
  - Booleans are bool
  - Errors are CellError instances
"""

from __future__ import annotations

import math
import re
from typing import Any, Callable, Dict, List

from .cell import CellError, ErrorType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_number(v: Any) -> float:
    """Coerce a value to float, raising ValueError on failure."""
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip())
        except ValueError:
            raise ValueError(f"Cannot convert {v!r} to number")
    if isinstance(v, CellError):
        raise SpreadsheetFuncError(v)
    raise ValueError(f"Cannot convert {type(v).__name__} to number")


def _to_str(v: Any) -> str:
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, float):
        if v == int(v):
            return str(int(v))
        return repr(v)
    if isinstance(v, int):
        return str(v)
    if isinstance(v, CellError):
        return str(v)
    return str(v)


def _to_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        s = v.strip().upper()
        if s == "TRUE":
            return True
        if s == "FALSE":
            return False
        return len(s) > 0
    if isinstance(v, CellError):
        raise SpreadsheetFuncError(v)
    return bool(v)


def _is_error(v: Any) -> bool:
    return isinstance(v, CellError)


class SpreadsheetFuncError(Exception):
    """Carry a CellError out of a function."""

    def __init__(self, err: CellError):
        self.err = err
        super().__init__(str(err))


def _propagate_errors(args: List[Any]) -> None:
    """If any arg is a CellError, raise SpreadsheetFuncError with the first."""
    for a in args:
        if isinstance(a, CellError):
            raise SpreadsheetFuncError(a)


def _num_args(args: List[Any], name: str) -> List[float]:
    _propagate_errors(args)
    return [_to_number(a) for a in args]


# ---------------------------------------------------------------------------
# Math functions
# ---------------------------------------------------------------------------

def fn_sum(args: List[Any]) -> float:
    _propagate_errors(args)
    total = 0.0
    for a in args:
        if isinstance(a, (list, tuple)):  # range expanded into a list
            for item in a:
                if _is_error(item):
                    raise SpreadsheetFuncError(item)
                total += _to_number(item)
        elif isinstance(a, bool):
            total += 1.0 if a else 0.0
        elif isinstance(a, (int, float)):
            total += a
        elif isinstance(a, str):
            try:
                total += float(a.strip())
            except ValueError:
                pass  # Excel ignores non-numeric strings in SUM
        elif isinstance(a, CellError):
            raise SpreadsheetFuncError(a)
    return total


def fn_average(args: List[Any]) -> float:
    vals = []
    for a in args:
        if isinstance(a, (list, tuple)):
            vals.extend(_flatten_numbers(a))
        elif isinstance(a, bool):
            vals.append(1.0 if a else 0.0)
        elif isinstance(a, (int, float)):
            vals.append(float(a))
        elif isinstance(a, str):
            try:
                vals.append(float(a.strip()))
            except ValueError:
                pass
        elif isinstance(a, CellError):
            raise SpreadsheetFuncError(a)
    if not vals:
        raise SpreadsheetFuncError(CellError(ErrorType.DIV_ZERO, "AVERAGE of empty range"))
    return sum(vals) / len(vals)


def fn_product(args: List[Any]) -> float:
    _propagate_errors(args)
    result = 1.0
    count = 0
    for a in args:
        if isinstance(a, (list, tuple)):
            for item in a:
                if isinstance(item, (int, float)) and not isinstance(item, bool):
                    result *= item
                    count += 1
        elif isinstance(a, (int, float)) and not isinstance(a, bool):
            result *= a
            count += 1
    return result


def fn_abs(args: List[Any]) -> float:
    nums = _num_args(args, "ABS")
    if len(nums) != 1:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "ABS needs 1 arg"))
    return abs(nums[0])


def fn_sqrt(args: List[Any]) -> float:
    nums = _num_args(args, "SQRT")
    if len(nums) != 1:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "SQRT needs 1 arg"))
    if nums[0] < 0:
        raise SpreadsheetFuncError(CellError(ErrorType.NUM, "SQRT of negative"))
    return math.sqrt(nums[0])


def fn_power(args: List[Any]) -> float:
    nums = _num_args(args, "POWER")
    if len(nums) != 2:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "POWER needs 2 args"))
    try:
        return math.pow(nums[0], nums[1])
    except (ValueError, OverflowError):
        raise SpreadsheetFuncError(CellError(ErrorType.NUM, "POWER overflow"))


def fn_exp(args: List[Any]) -> float:
    nums = _num_args(args, "EXP")
    return math.exp(nums[0])


def fn_ln(args: List[Any]) -> float:
    nums = _num_args(args, "LN")
    if nums[0] <= 0:
        raise SpreadsheetFuncError(CellError(ErrorType.NUM, "LN of non-positive"))
    return math.log(nums[0])


def fn_log(args: List[Any]) -> float:
    nums = _num_args(args, "LOG")
    base = nums[1] if len(nums) > 1 else 10.0
    if nums[0] <= 0 or base <= 0 or base == 1:
        raise SpreadsheetFuncError(CellError(ErrorType.NUM, "LOG invalid"))
    return math.log(nums[0], base)


def fn_sin(args: List[Any]) -> float:
    return math.sin(_num_args(args, "SIN")[0])


def fn_cos(args: List[Any]) -> float:
    return math.cos(_num_args(args, "COS")[0])


def fn_tan(args: List[Any]) -> float:
    return math.tan(_num_args(args, "TAN")[0])


def fn_asin(args: List[Any]) -> float:
    v = _num_args(args, "ASIN")[0]
    if v < -1 or v > 1:
        raise SpreadsheetFuncError(CellError(ErrorType.NUM, "ASIN domain"))
    return math.asin(v)


def fn_acos(args: List[Any]) -> float:
    v = _num_args(args, "ACOS")[0]
    if v < -1 or v > 1:
        raise SpreadsheetFuncError(CellError(ErrorType.NUM, "ACOS domain"))
    return math.acos(v)


def fn_atan(args: List[Any]) -> float:
    return math.atan(_num_args(args, "ATAN")[0])


def fn_atan2(args: List[Any]) -> float:
    nums = _num_args(args, "ATAN2")
    if len(nums) != 2:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "ATAN2 needs 2 args"))
    return math.atan2(nums[0], nums[1])


def fn_round(args: List[Any]) -> float:
    nums = _num_args(args, "ROUND")
    if len(nums) != 2:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "ROUND needs 2 args"))
    n = int(nums[1])
    # Use banker's rounding avoidance: Python's round() does banker's rounding
    # Excel does standard rounding (round half away from zero)
    val = nums[0]
    factor = 10 ** n
    return math.floor(val * factor + 0.5) / factor if val >= 0 else math.ceil(val * factor - 0.5) / factor


def fn_floor(args: List[Any]) -> float:
    nums = _num_args(args, "FLOOR")
    return math.floor(nums[0])


def fn_ceiling(args: List[Any]) -> float:
    nums = _num_args(args, "CEILING")
    return math.ceil(nums[0])


def fn_mod(args: List[Any]) -> float:
    nums = _num_args(args, "MOD")
    if len(nums) != 2:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "MOD needs 2 args"))
    if nums[1] == 0:
        raise SpreadsheetFuncError(CellError(ErrorType.DIV_ZERO, "MOD by zero"))
    return nums[0] - nums[1] * math.floor(nums[0] / nums[1])


def fn_pi(args: List[Any]) -> float:
    return math.pi


def fn_rand(args: List[Any]) -> float:
    import random
    return random.random()


def fn_max(args: List[Any]) -> float:
    vals = _flatten_numbers(args)
    if not vals:
        return 0.0
    return max(vals)


def fn_min(args: List[Any]) -> float:
    vals = _flatten_numbers(args)
    if not vals:
        return 0.0
    return min(vals)


# ---------------------------------------------------------------------------
# Statistics functions
# ---------------------------------------------------------------------------

def fn_count(args: List[Any]) -> float:
    """Count cells containing numbers."""
    count = 0
    for a in args:
        if isinstance(a, (list, tuple)):
            for item in a:
                if isinstance(item, (int, float)) and not isinstance(item, bool):
                    count += 1
        elif isinstance(a, (int, float)) and not isinstance(a, bool):
            count += 1
    return float(count)


def fn_counta(args: List[Any]) -> float:
    """Count non-empty cells."""
    count = 0
    for a in args:
        if isinstance(a, (list, tuple)):
            count += sum(1 for item in a if item is not None and item != "")
        elif a is not None and a != "":
            count += 1
    return float(count)


def fn_stdev(args: List[Any]) -> float:
    """Sample standard deviation."""
    vals = _flatten_numbers(args)
    if len(vals) < 2:
        raise SpreadsheetFuncError(CellError(ErrorType.NUM, "STDEV needs >=2 values"))
    mean = sum(vals) / len(vals)
    var = sum((x - mean) ** 2 for x in vals) / (len(vals) - 1)
    return math.sqrt(var)


def fn_var(args: List[Any]) -> float:
    """Sample variance."""
    vals = _flatten_numbers(args)
    if len(vals) < 2:
        raise SpreadsheetFuncError(CellError(ErrorType.NUM, "VAR needs >=2 values"))
    mean = sum(vals) / len(vals)
    return sum((x - mean) ** 2 for x in vals) / (len(vals) - 1)


def fn_median(args: List[Any]) -> float:
    vals = sorted(_flatten_numbers(args))
    if not vals:
        raise SpreadsheetFuncError(CellError(ErrorType.NUM, "MEDIAN of empty"))
    n = len(vals)
    mid = n // 2
    if n % 2 == 1:
        return vals[mid]
    return (vals[mid - 1] + vals[mid]) / 2


# ---------------------------------------------------------------------------
# Logic functions
# ---------------------------------------------------------------------------

def fn_if(args: List[Any]) -> Any:
    if len(args) < 2 or len(args) > 3:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "IF needs 2-3 args"))
    cond = _to_bool(args[0])
    if cond:
        return args[1]
    elif len(args) == 3:
        return args[2]
    return False


def fn_and(args: List[Any]) -> bool:
    _propagate_errors(args)
    for a in args:
        if isinstance(a, (list, tuple)):
            for item in a:
                if not _to_bool(item):
                    return False
        else:
            if not _to_bool(a):
                return False
    return True


def fn_or(args: List[Any]) -> bool:
    _propagate_errors(args)
    for a in args:
        if isinstance(a, (list, tuple)):
            for item in a:
                if _to_bool(item):
                    return True
        else:
            if _to_bool(a):
                return True
    return False


def fn_not(args: List[Any]) -> bool:
    _propagate_errors(args)
    if len(args) != 1:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "NOT needs 1 arg"))
    return not _to_bool(args[0])


def fn_true(args: List[Any]) -> bool:
    return True


def fn_false(args: List[Any]) -> bool:
    return False


def fn_iserror(args: List[Any]) -> bool:
    if len(args) != 1:
        return False
    return isinstance(args[0], CellError)


def fn_isnumber(args: List[Any]) -> bool:
    if len(args) != 1:
        return False
    v = args[0]
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def fn_istext(args: List[Any]) -> bool:
    if len(args) != 1:
        return False
    return isinstance(args[0], str)


def fn_isblank(args: List[Any]) -> bool:
    if len(args) != 1:
        return False
    return args[0] is None or args[0] == ""


# ---------------------------------------------------------------------------
# Text functions
# ---------------------------------------------------------------------------

def fn_len(args: List[Any]) -> float:
    _propagate_errors(args)
    return float(len(_to_str(args[0])))


def fn_upper(args: List[Any]) -> str:
    _propagate_errors(args)
    return _to_str(args[0]).upper()


def fn_lower(args: List[Any]) -> str:
    _propagate_errors(args)
    return _to_str(args[0]).lower()


def fn_trim(args: List[Any]) -> str:
    _propagate_errors(args)
    return _to_str(args[0]).strip()


def fn_concat(args: List[Any]) -> str:
    _propagate_errors(args)
    parts = []
    for a in args:
        if isinstance(a, (list, tuple)):
            for item in a:
                parts.append(_to_str(item))
        else:
            parts.append(_to_str(a))
    return "".join(parts)


def fn_concatenate(args: List[Any]) -> str:
    return fn_concat(args)


def fn_left(args: List[Any]) -> str:
    _propagate_errors(args)
    s = _to_str(args[0])
    n = int(_to_number(args[1])) if len(args) > 1 else 1
    return s[:n]


def fn_right(args: List[Any]) -> str:
    _propagate_errors(args)
    s = _to_str(args[0])
    n = int(_to_number(args[1])) if len(args) > 1 else 1
    return s[-n:] if n > 0 else ""


def fn_mid(args: List[Any]) -> str:
    _propagate_errors(args)
    s = _to_str(args[0])
    start = int(_to_number(args[1]))
    length = int(_to_number(args[2]))
    if start < 1:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "MID start < 1"))
    return s[start - 1: start - 1 + length]


def fn_replace(args: List[Any]) -> str:
    _propagate_errors(args)
    old = _to_str(args[0])
    start = int(_to_number(args[1]))
    length = int(_to_number(args[2]))
    new = _to_str(args[3])
    if start < 1:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "REPLACE start < 1"))
    return old[:start - 1] + new + old[start - 1 + length:]


def fn_substitute(args: List[Any]) -> str:
    _propagate_errors(args)
    text = _to_str(args[0])
    old = _to_str(args[1])
    new = _to_str(args[2])
    if len(args) > 3:
        instance = int(_to_number(args[3]))
        # replace only the nth occurrence
        count = 0
        idx = 0
        while True:
            found = text.find(old, idx)
            if found == -1:
                break
            count += 1
            if count == instance:
                return text[:found] + new + text[found + len(old):]
            idx = found + len(old)
        return text
    return text.replace(old, new)


def fn_value(args: List[Any]) -> float:
    _propagate_errors(args)
    return _to_number(args[0])


def fn_text(args: List[Any]) -> str:
    """Simplified TEXT function: supports '0', '#', and '0.00' style formats."""
    _propagate_errors(args)
    num = _to_number(args[0])
    fmt = _to_str(args[1])
    # Very simplified format handling
    if "." in fmt:
        decimals = len(fmt) - fmt.index(".") - 1
        return f"{num:.{decimals}f}"
    else:
        return str(int(num))


def fn_find(args: List[Any]) -> float:
    """FIND(find_text, within_text, [start_num]) — case-sensitive."""
    _propagate_errors(args)
    find_text = _to_str(args[0])
    within = _to_str(args[1])
    start = int(_to_number(args[2])) if len(args) > 2 else 1
    if start < 1:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "FIND start < 1"))
    idx = within.find(find_text, start - 1)
    if idx == -1:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "FIND not found"))
    return float(idx + 1)


# ---------------------------------------------------------------------------
# Lookup functions
# ---------------------------------------------------------------------------

def fn_iferror(args: List[Any]) -> Any:
    if len(args) != 2:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "IFERROR needs 2 args"))
    val = args[0]
    if isinstance(val, CellError):
        return args[1]
    return val


def fn_na(args: List[Any]) -> CellError:
    return CellError(ErrorType.NA, "N/A")


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _flatten_numbers(args: List[Any]) -> List[float]:
    """Flatten args (which may contain nested lists from ranges) into numbers."""
    result: List[float] = []
    for a in args:
        if isinstance(a, (list, tuple)):
            for item in a:
                if isinstance(item, CellError):
                    raise SpreadsheetFuncError(item)
                if isinstance(item, (int, float)) and not isinstance(item, bool):
                    result.append(float(item))
                elif isinstance(item, bool):
                    result.append(1.0 if item else 0.0)
        elif isinstance(a, CellError):
            raise SpreadsheetFuncError(a)
        elif isinstance(a, (int, float)) and not isinstance(a, bool):
            result.append(float(a))
        elif isinstance(a, bool):
            result.append(1.0 if a else 0.0)
        elif isinstance(a, str):
            try:
                result.append(float(a.strip()))
            except ValueError:
                pass
    return result


# ---------------------------------------------------------------------------
# Function registry
# ---------------------------------------------------------------------------

FUNCTIONS: Dict[str, Callable] = {
    # Math
    "SUM": fn_sum,
    "AVERAGE": fn_average,
    "PRODUCT": fn_product,
    "ABS": fn_abs,
    "SQRT": fn_sqrt,
    "POWER": fn_power,
    "EXP": fn_exp,
    "LN": fn_ln,
    "LOG": fn_log,
    "SIN": fn_sin,
    "COS": fn_cos,
    "TAN": fn_tan,
    "ASIN": fn_asin,
    "ACOS": fn_acos,
    "ATAN": fn_atan,
    "ATAN2": fn_atan2,
    "ROUND": fn_round,
    "FLOOR": fn_floor,
    "CEILING": fn_ceiling,
    "MOD": fn_mod,
    "PI": fn_pi,
    "RAND": fn_rand,
    "MAX": fn_max,
    "MIN": fn_min,
    # Statistics
    "COUNT": fn_count,
    "COUNTA": fn_counta,
    "STDEV": fn_stdev,
    "VAR": fn_var,
    "MEDIAN": fn_median,
    # Logic
    "IF": fn_if,
    "AND": fn_and,
    "OR": fn_or,
    "NOT": fn_not,
    "TRUE": fn_true,
    "FALSE": fn_false,
    "ISERROR": fn_iserror,
    "ISNUMBER": fn_isnumber,
    "ISTEXT": fn_istext,
    "ISBLANK": fn_isblank,
    # Text
    "LEN": fn_len,
    "UPPER": fn_upper,
    "LOWER": fn_lower,
    "TRIM": fn_trim,
    "CONCAT": fn_concat,
    "CONCATENATE": fn_concatenate,
    "LEFT": fn_left,
    "RIGHT": fn_right,
    "MID": fn_mid,
    "REPLACE": fn_replace,
    "SUBSTITUTE": fn_substitute,
    "VALUE": fn_value,
    "TEXT": fn_text,
    "FIND": fn_find,
    # Lookup
    "IFERROR": fn_iferror,
    "NA": fn_na,
}


def call_function(name: str, args: List[Any]) -> Any:
    """Look up and call a spreadsheet function by name."""
    name = name.upper()
    if name not in FUNCTIONS:
        raise SpreadsheetFuncError(CellError(ErrorType.NAME, f"Unknown function: {name}"))
    try:
        result = FUNCTIONS[name](args)
    except SpreadsheetFuncError:
        raise
    except ZeroDivisionError:
        raise SpreadsheetFuncError(CellError(ErrorType.DIV_ZERO, "Division by zero"))
    except ValueError as e:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, str(e)))
    except OverflowError:
        raise SpreadsheetFuncError(CellError(ErrorType.NUM, "Overflow"))
    return result