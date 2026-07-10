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
        if isinstance(a, (list, tuple)):
            for item in a:
                if isinstance(item, (list, tuple)):
                    # 2D range — flatten one more level
                    for sub in item:
                        if _is_error(sub):
                            raise SpreadsheetFuncError(sub)
                        if isinstance(sub, (int, float)) and not isinstance(sub, bool):
                            total += sub
                        elif isinstance(sub, bool):
                            total += 1.0 if sub else 0.0
                        elif isinstance(sub, str):
                            try:
                                total += float(sub.strip())
                            except ValueError:
                                pass
                elif _is_error(item):
                    raise SpreadsheetFuncError(item)
                elif isinstance(item, bool):
                    total += 1.0 if item else 0.0
                elif isinstance(item, (int, float)):
                    total += item
                elif isinstance(item, str):
                    try:
                        total += float(item.strip())
                    except ValueError:
                        pass
        elif isinstance(a, bool):
            total += 1.0 if a else 0.0
        elif isinstance(a, (int, float)):
            total += a
        elif isinstance(a, str):
            try:
                total += float(a.strip())
            except ValueError:
                pass
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


def fn_vlookup(args: List[Any]) -> Any:
    """VLOOKUP(lookup_value, table_array, col_index, [range_lookup]).

    Searches the first column of table_array for lookup_value, returns
    the value in the same row at col_index.  range_lookup defaults to
    approximate match (TRUE).
    """
    if len(args) < 3 or len(args) > 4:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "VLOOKUP needs 3-4 args"))
    _propagate_errors(args)
    lookup_val = args[0]
    table = args[1]
    col_idx = int(_to_number(args[2]))
    exact = len(args) < 4 or not _to_bool(args[3])  # FALSE=exact, TRUE=approx

    if not isinstance(table, (list, tuple)):
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "VLOOKUP table must be a range"))

    # Determine number of columns in the table
    # Table is a flat list representing row-major cells
    # We need to figure out the width. In our model, ranges are returned as
    # flat lists. We'll infer width from the original range.
    # For simplicity, we assume the table is a 2D structure passed as a flat list.
    # We'll try to detect the structure: if it's a list of lists, use that.
    if len(table) == 0:
        raise SpreadsheetFuncError(CellError(ErrorType.NA, "VLOOKUP empty table"))

    # If table is a list of lists (rows), use directly
    if table and isinstance(table[0], (list, tuple)):
        rows = table
    else:
        # flat list — could be a single row (from a 1-row range) or
        # a single column (from a 1-col range).
        # If col_idx > 1, treat as single row (first element is key, rest are columns)
        # Otherwise treat as single column
        if col_idx > 1 and len(table) >= col_idx:
            rows = [list(table)]
        else:
            rows = [[v] for v in table]

    if col_idx < 1 or col_idx > len(rows[0]):
        raise SpreadsheetFuncError(CellError(ErrorType.REF, "VLOOKUP col_index out of range"))

    best_row = None
    for row in rows:
        first_val = row[0]
        if exact:
            if _values_equal(first_val, lookup_val):
                return row[col_idx - 1]
        else:
            # approximate match: find largest value <= lookup_val
            if _values_le(first_val, lookup_val):
                best_row = row
            else:
                break

    if best_row is not None:
        return best_row[col_idx - 1]

    raise SpreadsheetFuncError(CellError(ErrorType.NA, "VLOOKUP: value not found"))


def fn_hlookup(args: List[Any]) -> Any:
    """HLOOKUP(lookup_value, table_array, row_index, [range_lookup])."""
    if len(args) < 3 or len(args) > 4:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "HLOOKUP needs 3-4 args"))
    _propagate_errors(args)
    lookup_val = args[0]
    table = args[1]
    row_idx = int(_to_number(args[2]))
    exact = len(args) < 4 or not _to_bool(args[3])

    if not isinstance(table, (list, tuple)) or len(table) == 0:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "HLOOKUP table must be a range"))

    if table and isinstance(table[0], (list, tuple)):
        rows = table
    else:
        # flat list treated as single row
        rows = [list(table)]

    if row_idx < 1 or row_idx > len(rows):
        raise SpreadsheetFuncError(CellError(ErrorType.REF, "HLOOKUP row_index out of range"))

    header = rows[0]
    best_col = None
    for c, val in enumerate(header):
        if exact:
            if _values_equal(val, lookup_val):
                return rows[row_idx - 1][c]
        else:
            if _values_le(val, lookup_val):
                best_col = c
            else:
                break

    if best_col is not None:
        return rows[row_idx - 1][best_col]

    raise SpreadsheetFuncError(CellError(ErrorType.NA, "HLOOKUP: value not found"))


def fn_match(args: List[Any]) -> float:
    """MATCH(lookup_value, lookup_array, [match_type]).
    match_type: 1=largest <=, 0=exact, -1=smallest >=. Default 1.
    """
    if len(args) < 2 or len(args) > 3:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "MATCH needs 2-3 args"))
    _propagate_errors(args)
    lookup_val = args[0]
    arr = args[1]
    match_type = int(_to_number(args[2])) if len(args) > 2 else 1

    if not isinstance(arr, (list, tuple)):
        arr = [arr]

    if match_type == 0:
        for i, v in enumerate(arr):
            if _values_equal(v, lookup_val):
                return float(i + 1)
    elif match_type == 1:
        best = None
        for i, v in enumerate(arr):
            if _values_le(v, lookup_val):
                best = i
            else:
                break
        if best is not None:
            return float(best + 1)
    elif match_type == -1:
        best = None
        for i, v in enumerate(arr):
            if _values_ge(v, lookup_val):
                best = i
            else:
                break
        if best is not None:
            return float(best + 1)

    raise SpreadsheetFuncError(CellError(ErrorType.NA, "MATCH: no match found"))


def fn_index(args: List[Any]) -> Any:
    """INDEX(array, row_num, [col_num])."""
    if len(args) < 2 or len(args) > 3:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "INDEX needs 2-3 args"))
    _propagate_errors(args)
    arr = args[0]
    row_num = int(_to_number(args[1]))
    col_num = int(_to_number(args[2])) if len(args) > 2 else None

    if not isinstance(arr, (list, tuple)):
        arr = [arr]

    # If arr is a flat list (1-D)
    if arr and not isinstance(arr[0], (list, tuple)):
        if col_num is not None:
            # treat as 2D with 1 row — actually treat arr as a single row
            if row_num == 1 and col_num <= len(arr):
                return arr[col_num - 1]
            elif row_num <= len(arr) and col_num == 1:
                return arr[row_num - 1]
            else:
                raise SpreadsheetFuncError(CellError(ErrorType.REF, "INDEX out of range"))
        else:
            if row_num < 1 or row_num > len(arr):
                raise SpreadsheetFuncError(CellError(ErrorType.REF, "INDEX row out of range"))
            return arr[row_num - 1]

    # 2D array
    rows = arr
    if row_num < 1 or row_num > len(rows):
        raise SpreadsheetFuncError(CellError(ErrorType.REF, "INDEX row out of range"))
    if col_num is None:
        col_num = 1
    if col_num < 1 or col_num > len(rows[row_num - 1]):
        raise SpreadsheetFuncError(CellError(ErrorType.REF, "INDEX col out of range"))
    return rows[row_num - 1][col_num - 1]


def fn_choose(args: List[Any]) -> Any:
    """CHOOSE(index_num, value1, value2, ...) — returns the value at position index_num."""
    if len(args) < 2:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "CHOOSE needs >=2 args"))
    _propagate_errors(args)
    idx = int(_to_number(args[0]))
    if idx < 1 or idx > len(args) - 1:
        raise SpreadsheetFuncError(CellError(ErrorType.NUM, "CHOOSE index out of range"))
    return args[idx]


# ---------------------------------------------------------------------------
# Additional text functions
# ---------------------------------------------------------------------------

def fn_proper(args: List[Any]) -> str:
    """PROPER(text) — capitalize first letter of each word."""
    _propagate_errors(args)
    return _to_str(args[0]).title()


def fn_rept(args: List[Any]) -> str:
    """REPT(text, number_times) — repeat text n times."""
    _propagate_errors(args)
    text = _to_str(args[0])
    n = int(_to_number(args[1]))
    if n < 0:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "REPT count < 0"))
    return text * n


def fn_search(args: List[Any]) -> float:
    """SEARCH(find_text, within_text, [start_num]) — case-insensitive FIND."""
    _propagate_errors(args)
    find_text = _to_str(args[0]).upper()
    within = _to_str(args[1]).upper()
    start = int(_to_number(args[2])) if len(args) > 2 else 1
    if start < 1:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "SEARCH start < 1"))
    idx = within.find(find_text, start - 1)
    if idx == -1:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "SEARCH not found"))
    return float(idx + 1)


def fn_exact(args: List[Any]) -> bool:
    """EXACT(text1, text2) — case-sensitive comparison."""
    _propagate_errors(args)
    return _to_str(args[0]) == _to_str(args[1])


def fn_textjoin(args: List[Any]) -> str:
    """TEXTJOIN(delimiter, ignore_empty, text1, text2, ...)."""
    if len(args) < 3:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "TEXTJOIN needs >=3 args"))
    _propagate_errors(args)
    delimiter = _to_str(args[0])
    ignore_empty = _to_bool(args[1])
    parts = []
    for a in args[2:]:
        if isinstance(a, (list, tuple)):
            for item in a:
                if ignore_empty and (item is None or item == ""):
                    continue
                parts.append(_to_str(item))
        else:
            if ignore_empty and (a is None or a == ""):
                continue
            parts.append(_to_str(a))
    return delimiter.join(parts)


def fn_code(args: List[Any]) -> float:
    """CODE(text) — return ASCII code of first character."""
    _propagate_errors(args)
    s = _to_str(args[0])
    if len(s) == 0:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "CODE of empty string"))
    return float(ord(s[0]))


def fn_char(args: List[Any]) -> str:
    """CHAR(number) — return character for ASCII code."""
    _propagate_errors(args)
    n = int(_to_number(args[0]))
    if n < 0 or n > 1114111:
        raise SpreadsheetFuncError(CellError(ErrorType.NUM, "CHAR code out of range"))
    return chr(n)


# ---------------------------------------------------------------------------
# Additional math/statistics functions
# ---------------------------------------------------------------------------

def fn_sign(args: List[Any]) -> float:
    """SIGN(number) — returns -1, 0, or 1."""
    nums = _num_args(args, "SIGN")
    v = nums[0]
    if v > 0:
        return 1.0
    if v < 0:
        return -1.0
    return 0.0


def fn_gcd(args: List[Any]) -> float:
    """GCD(number1, number2, ...) — greatest common divisor."""
    import math as m
    nums = _num_args(args, "GCD")
    if not nums:
        return 0.0
    result = int(nums[0])
    for n in nums[1:]:
        result = m.gcd(result, int(n))
    return float(result)


def fn_lcm(args: List[Any]) -> float:
    """LCM(number1, number2, ...) — least common multiple."""
    import math as m
    nums = _num_args(args, "LCM")
    if not nums:
        return 0.0
    result = int(nums[0])
    for n in nums[1:]:
        result = m.lcm(result, int(n))
    return float(result)


def fn_fact(args: List[Any]) -> float:
    """FACT(n) — factorial of n."""
    import math as m
    n = int(_num_args(args, "FACT")[0])
    if n < 0:
        raise SpreadsheetFuncError(CellError(ErrorType.NUM, "FACT of negative"))
    return float(m.factorial(n))


def fn_degrees(args: List[Any]) -> float:
    """DEGREES(radians) — convert radians to degrees."""
    return math.degrees(_num_args(args, "DEGREES")[0])


def fn_radians(args: List[Any]) -> float:
    """RADIANS(degrees) — convert degrees to radians."""
    return math.radians(_num_args(args, "RADIANS")[0])


def fn_int(args: List[Any]) -> float:
    """INT(number) — round down to nearest integer."""
    return float(math.floor(_num_args(args, "INT")[0]))


def fn_trunc(args: List[Any]) -> float:
    """TRUNC(number, [digits]) — truncate toward zero."""
    nums = _num_args(args, "TRUNC")
    val = nums[0]
    digits = int(nums[1]) if len(nums) > 1 else 0
    factor = 10 ** digits
    return float(math.trunc(val * factor)) / factor


def fn_stdevp(args: List[Any]) -> float:
    """Population standard deviation."""
    vals = _flatten_numbers(args)
    if not vals:
        raise SpreadsheetFuncError(CellError(ErrorType.NUM, "STDEVP of empty"))
    mean = sum(vals) / len(vals)
    var = sum((x - mean) ** 2 for x in vals) / len(vals)
    return math.sqrt(var)


def fn_varp(args: List[Any]) -> float:
    """Population variance."""
    vals = _flatten_numbers(args)
    if not vals:
        raise SpreadsheetFuncError(CellError(ErrorType.NUM, "VARP of empty"))
    mean = sum(vals) / len(vals)
    return sum((x - mean) ** 2 for x in vals) / len(vals)


def fn_mode(args: List[Any]) -> float:
    """MODE(number1, ...) — most frequently occurring value."""
    from collections import Counter
    vals = _flatten_numbers(args)
    if not vals:
        raise SpreadsheetFuncError(CellError(ErrorType.NA, "MODE of empty"))
    counts = Counter(vals)
    max_count = max(counts.values())
    if max_count == 1:
        raise SpreadsheetFuncError(CellError(ErrorType.NA, "MODE: no repeated value"))
    # return the smallest value with max count
    return float(min(v for v, c in counts.items() if c == max_count))


def fn_rank(args: List[Any]) -> float:
    """RANK(number, ref, [order]) — rank of number in ref.
    order=0 (default) descending, non-zero ascending.
    """
    if len(args) < 2 or len(args) > 3:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "RANK needs 2-3 args"))
    _propagate_errors(args)
    num = _to_number(args[0])
    ref = args[1]
    if not isinstance(ref, (list, tuple)):
        ref = [ref]
    order = int(_to_number(args[2])) if len(args) > 2 else 0

    nums = []
    for v in ref:
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            nums.append(float(v))

    if order == 0:
        sorted_nums = sorted(nums, reverse=True)
    else:
        sorted_nums = sorted(nums)

    # Find rank (1-based position, handling ties with same rank)
    rank = 1
    for v in sorted_nums:
        if v == num:
            return float(rank)
        rank += 1
    raise SpreadsheetFuncError(CellError(ErrorType.NA, "RANK: number not in ref"))


def fn_percentile(args: List[Any]) -> float:
    """PERCENTILE(array, k) — k-th percentile (0..1) using linear interpolation."""
    if len(args) != 2:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "PERCENTILE needs 2 args"))
    _propagate_errors(args)
    vals = _flatten_numbers([args[0]])
    k = _to_number(args[1])
    if k < 0 or k > 1:
        raise SpreadsheetFuncError(CellError(ErrorType.NUM, "PERCENTILE k out of range"))
    if not vals:
        raise SpreadsheetFuncError(CellError(ErrorType.NUM, "PERCENTILE of empty"))
    vals = sorted(vals)
    if len(vals) == 1:
        return vals[0]
    rank = k * (len(vals) - 1)
    lo = int(math.floor(rank))
    hi = int(math.ceil(rank))
    if lo == hi:
        return vals[lo]
    frac = rank - lo
    return vals[lo] * (1 - frac) + vals[hi] * frac


def fn_quartile(args: List[Any]) -> float:
    """QUARTILE(array, quart) — 0=min, 1=Q1, 2=median, 3=Q3, 4=max."""
    if len(args) != 2:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "QUARTILE needs 2 args"))
    quart = int(_to_number(args[1]))
    if quart < 0 or quart > 4:
        raise SpreadsheetFuncError(CellError(ErrorType.NUM, "QUARTILE quart out of range"))
    k = quart / 4.0
    return fn_percentile([args[0], k])


def fn_correl(args: List[Any]) -> float:
    """CORREL(array1, array2) — Pearson correlation coefficient."""
    if len(args) != 2:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "CORREL needs 2 args"))
    _propagate_errors(args)
    x = _flatten_numbers([args[0]])
    y = _flatten_numbers([args[1]])
    if len(x) != len(y) or len(x) < 2:
        raise SpreadsheetFuncError(CellError(ErrorType.NA, "CORREL: arrays must have same length >=2"))
    n = len(x)
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    var_x = sum((xi - mean_x) ** 2 for xi in x)
    var_y = sum((yi - mean_y) ** 2 for yi in y)
    if var_x == 0 or var_y == 0:
        raise SpreadsheetFuncError(CellError(ErrorType.DIV_ZERO, "CORREL: zero variance"))
    return cov / math.sqrt(var_x * var_y)


def fn_slope(args: List[Any]) -> float:
    """SLOPE(known_y, known_x) — slope of linear regression line."""
    if len(args) != 2:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "SLOPE needs 2 args"))
    _propagate_errors(args)
    y = _flatten_numbers([args[0]])
    x = _flatten_numbers([args[1]])
    if len(x) != len(y) or len(x) < 2:
        raise SpreadsheetFuncError(CellError(ErrorType.NA, "SLOPE: arrays must have same length >=2"))
    n = len(x)
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    den = sum((xi - mean_x) ** 2 for xi in x)
    if den == 0:
        raise SpreadsheetFuncError(CellError(ErrorType.DIV_ZERO, "SLOPE: zero variance"))
    return num / den


# ---------------------------------------------------------------------------
# Comparison helpers for lookup functions
# ---------------------------------------------------------------------------

def _values_equal(a: Any, b: Any) -> bool:
    """Compare two values for equality (case-insensitive for strings)."""
    if isinstance(a, str) and isinstance(b, str):
        return a.upper() == b.upper()
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return float(a) == float(b)
    return a == b


def _values_le(a: Any, b: Any) -> bool:
    """Check if a <= b (for approximate VLOOKUP/MATCH)."""
    if isinstance(a, (int, float)) and not isinstance(a, bool) and isinstance(b, (int, float)) and not isinstance(b, bool):
        return float(a) <= float(b)
    if isinstance(a, str) and isinstance(b, str):
        return a.upper() <= b.upper()
    # numbers < strings in Excel sort order
    if isinstance(a, (int, float)) and not isinstance(a, bool) and isinstance(b, str):
        return True
    if isinstance(a, str) and isinstance(b, (int, float)) and not isinstance(b, bool):
        return False
    return str(a) <= str(b)


def _values_ge(a: Any, b: Any) -> bool:
    """Check if a >= b."""
    if isinstance(a, (int, float)) and not isinstance(a, bool) and isinstance(b, (int, float)) and not isinstance(b, bool):
        return float(a) >= float(b)
    if isinstance(a, str) and isinstance(b, str):
        return a.upper() >= b.upper()
    return not _values_le(a, b) or _values_equal(a, b)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _flatten_numbers(args: List[Any]) -> List[float]:
    """Flatten args (which may contain nested lists from ranges) into numbers.
    Handles both flat lists and 2D lists (list of rows)."""
    result: List[float] = []

    def _process(v: Any) -> None:
        if isinstance(v, (list, tuple)):
            for item in v:
                _process(item)
        elif isinstance(v, CellError):
            raise SpreadsheetFuncError(v)
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            result.append(float(v))
        elif isinstance(v, bool):
            result.append(1.0 if v else 0.0)
        elif isinstance(v, str):
            try:
                result.append(float(v.strip()))
            except ValueError:
                pass

    for a in args:
        _process(a)
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
    "SIGN": fn_sign,
    "GCD": fn_gcd,
    "LCM": fn_lcm,
    "FACT": fn_fact,
    "DEGREES": fn_degrees,
    "RADIANS": fn_radians,
    "INT": fn_int,
    "TRUNC": fn_trunc,
    # Statistics
    "COUNT": fn_count,
    "COUNTA": fn_counta,
    "STDEV": fn_stdev,
    "VAR": fn_var,
    "MEDIAN": fn_median,
    "STDEVP": fn_stdevp,
    "VARP": fn_varp,
    "MODE": fn_mode,
    "RANK": fn_rank,
    "PERCENTILE": fn_percentile,
    "QUARTILE": fn_quartile,
    "CORREL": fn_correl,
    "SLOPE": fn_slope,
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
    "IFERROR": fn_iferror,
    "NA": fn_na,
    "CHOOSE": fn_choose,
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
    "PROPER": fn_proper,
    "REPT": fn_rept,
    "SEARCH": fn_search,
    "EXACT": fn_exact,
    "TEXTJOIN": fn_textjoin,
    "CODE": fn_code,
    "CHAR": fn_char,
    # Lookup
    "VLOOKUP": fn_vlookup,
    "HLOOKUP": fn_hlookup,
    "MATCH": fn_match,
    "INDEX": fn_index,
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