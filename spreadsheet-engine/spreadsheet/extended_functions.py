"""
Extended built-in functions for the spreadsheet engine.

Adds date/time, financial, and information functions to the core function registry.
"""

from __future__ import annotations

import datetime
import math
from typing import Any, Dict, List

from .cell import CellError, ErrorType
from .functions import (
    SpreadsheetFuncError,
    _to_number,
    _to_str,
    _to_bool,
    _propagate_errors,
    _flatten_numbers,
    FUNCTIONS,
)


# ---------------------------------------------------------------------------
# Date / Time functions
# ---------------------------------------------------------------------------

def fn_today(args: List[Any]) -> float:
    """TODAY() — serial number of today's date (days since 1899-12-30, Excel epoch)."""
    _propagate_errors(args)
    today = datetime.date.today()
    epoch = datetime.date(1899, 12, 30)
    return float((today - epoch).days)


def fn_now(args: List[Any]) -> float:
    """NOW() — serial number of current date+time."""
    _propagate_errors(args)
    now = datetime.datetime.now()
    epoch = datetime.datetime(1899, 12, 30)
    delta = now - epoch
    return float(delta.days + delta.seconds / 86400.0)


def fn_date(args: List[Any]) -> float:
    """DATE(year, month, day) — Excel serial date."""
    nums = [_to_number(a) for a in args]
    if len(nums) != 3:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "DATE needs 3 args"))
    year, month, day = int(nums[0]), int(nums[1]), int(nums[2])
    # Excel epoch: 1899-12-30 (for 1900 system)
    epoch = datetime.date(1899, 12, 30)
    try:
        # Handle month overflow (month=13 -> next year)
        year += (month - 1) // 12
        month = (month - 1) % 12 + 1
        d = datetime.date(year, month, 1)
        # Add days - 1 (since day=1 means first of month)
        from datetime import timedelta
        d = d + timedelta(days=day - 1)
        return float((d - epoch).days)
    except (ValueError, OverflowError):
        raise SpreadsheetFuncError(CellError(ErrorType.NUM, "DATE: invalid date"))


def fn_year(args: List[Any]) -> float:
    """YEAR(serial_number) — year from Excel serial date."""
    _propagate_errors(args)
    serial = int(_to_number(args[0]))
    epoch = datetime.date(1899, 12, 30)
    try:
        d = epoch + datetime.timedelta(days=serial)
        return float(d.year)
    except (ValueError, OverflowError):
        raise SpreadsheetFuncError(CellError(ErrorType.NUM, "YEAR: invalid serial"))


def fn_month(args: List[Any]) -> float:
    """MONTH(serial_number) — month (1-12) from Excel serial date."""
    _propagate_errors(args)
    serial = int(_to_number(args[0]))
    epoch = datetime.date(1899, 12, 30)
    try:
        d = epoch + datetime.timedelta(days=serial)
        return float(d.month)
    except (ValueError, OverflowError):
        raise SpreadsheetFuncError(CellError(ErrorType.NUM, "MONTH: invalid serial"))


def fn_day(args: List[Any]) -> float:
    """DAY(serial_number) — day of month (1-31) from Excel serial date."""
    _propagate_errors(args)
    serial = int(_to_number(args[0]))
    epoch = datetime.date(1899, 12, 30)
    try:
        d = epoch + datetime.timedelta(days=serial)
        return float(d.day)
    except (ValueError, OverflowError):
        raise SpreadsheetFuncError(CellError(ErrorType.NUM, "DAY: invalid serial"))


def fn_weekday(args: List[Any]) -> float:
    """WEEKDAY(serial, [return_type]) — day of week."""
    _propagate_errors(args)
    serial = int(_to_number(args[0]))
    return_type = int(_to_number(args[1])) if len(args) > 1 else 1
    epoch = datetime.date(1899, 12, 30)
    try:
        d = epoch + datetime.timedelta(days=serial)
    except (ValueError, OverflowError):
        raise SpreadsheetFuncError(CellError(ErrorType.NUM, "WEEKDAY: invalid serial"))
    weekday = d.weekday()  # 0=Monday, 6=Sunday
    if return_type == 1:
        # Sunday=1 .. Saturday=7
        return float(weekday + 2 if weekday < 6 else 1)
    elif return_type == 2:
        # Monday=1 .. Sunday=7
        return float(weekday + 1)
    elif return_type == 3:
        # Monday=0 .. Sunday=6
        return float(weekday)
    else:
        raise SpreadsheetFuncError(CellError(ErrorType.NUM, "WEEKDAY: invalid return_type"))


def fn_hour(args: List[Any]) -> float:
    """HOUR(serial) — hour (0-23) from Excel serial datetime."""
    _propagate_errors(args)
    serial = _to_number(args[0])
    frac = serial - int(serial)
    total_seconds = frac * 86400
    return float(int(total_seconds) // 3600)


def fn_minute(args: List[Any]) -> float:
    """MINUTE(serial) — minute (0-59)."""
    _propagate_errors(args)
    serial = _to_number(args[0])
    frac = serial - int(serial)
    total_seconds = frac * 86400
    return float((int(total_seconds) % 3600) // 60)


def fn_second(args: List[Any]) -> float:
    """SECOND(serial) — second (0-59)."""
    _propagate_errors(args)
    serial = _to_number(args[0])
    frac = serial - int(serial)
    total_seconds = frac * 86400
    return float(int(total_seconds) % 60)


# ---------------------------------------------------------------------------
# Financial functions
# ---------------------------------------------------------------------------

def fn_pv(args: List[Any]) -> float:
    """PV(rate, nper, pmt, [fv], [type]) — present value of an annuity."""
    nums = [_to_number(a) for a in args]
    if len(nums) < 3:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "PV needs >=3 args"))
    rate = nums[0]
    nper = nums[1]
    pmt = nums[2]
    fv = nums[3] if len(nums) > 3 else 0
    pmt_type = int(nums[4]) if len(nums) > 4 else 0  # 0=end, 1=beginning

    if rate == 0:
        return -(pmt * nper + fv)
    factor = (1 + rate) ** nper
    # Excel: PV = -(PMT*(1+r*type)*(1-(1+r)^-n)/r + FV*(1+r)^-n)
    pv_pmt = -pmt * (1 + rate * pmt_type) * (1 - 1 / factor) / rate
    pv_fv = -fv / factor
    return pv_pmt + pv_fv


def fn_fv(args: List[Any]) -> float:
    """FV(rate, nper, pmt, [pv], [type]) — future value of an annuity."""
    nums = [_to_number(a) for a in args]
    if len(nums) < 3:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "FV needs >=3 args"))
    rate = nums[0]
    nper = nums[1]
    pmt = nums[2]
    pv = nums[3] if len(nums) > 3 else 0
    pmt_type = int(nums[4]) if len(nums) > 4 else 0

    if rate == 0:
        return -(pv + pmt * nper)
    factor = (1 + rate) ** nper
    # Excel: FV = -(PMT*(1+r*type)*((1+r)^n - 1)/r + PV*(1+r)^n)
    fv_pmt = -pmt * (1 + rate * pmt_type) * (factor - 1) / rate
    fv_pv = -pv * factor
    return fv_pmt + fv_pv


def fn_pmt(args: List[Any]) -> float:
    """PMT(rate, nper, pv, [fv], [type]) — periodic payment for an annuity."""
    nums = [_to_number(a) for a in args]
    if len(nums) < 3:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "PMT needs >=3 args"))
    rate = nums[0]
    nper = nums[1]
    pv = nums[2]
    fv = nums[3] if len(nums) > 3 else 0
    pmt_type = int(nums[4]) if len(nums) > 4 else 0

    if rate == 0:
        return -(pv + fv) / nper
    factor = (1 + rate) ** nper
    pmt = -(pv * factor + fv) / ((1 + rate * pmt_type) * (factor - 1) / rate)
    return pmt


def fn_npv(args: List[Any]) -> float:
    """NPV(rate, value1, value2, ...) — net present value of cash flows."""
    _propagate_errors(args)
    if len(args) < 2:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "NPV needs >=2 args"))
    rate = _to_number(args[0])
    cash_flows = _flatten_numbers(args[1:])
    total = 0.0
    for i, cf in enumerate(cash_flows):
        total += cf / ((1 + rate) ** (i + 1))
    return total


def fn_irr(args: List[Any]) -> float:
    """IRR(values, [guess]) — internal rate of return via Newton's method.

    Values can be passed as individual arguments or as a single range/array.
    """
    _propagate_errors(args)
    if len(args) < 1:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "IRR needs >=1 arg"))
    # Flatten all args except the guess
    values = _flatten_numbers(args[:1]) if isinstance(args[0], (list, tuple)) else []
    if not values:
        # If args are individual scalars, extract them
        for a in args:
            if isinstance(a, (int, float)) and not isinstance(a, bool):
                values.append(float(a))
    if len(values) < 2:
        raise SpreadsheetFuncError(CellError(ErrorType.NUM, "IRR needs >=2 cash flows"))
    guess = _to_number(args[-1]) if len(args) > 1 and isinstance(args[-1], (int, float)) else 0.1

    # Newton's method
    rate = guess
    for _ in range(100):
        npv = 0.0
        dnpv = 0.0
        for i, v in enumerate(values):
            factor = (1 + rate) ** i
            npv += v / factor
            if i > 0:
                dnpv -= i * v / ((1 + rate) ** (i + 1))
        if abs(npv) < 1e-10:
            return rate
        if dnpv == 0:
            break
        rate -= npv / dnpv
        if rate <= -1:
            rate = -0.99

    # Try bisection if Newton didn't converge
    lo, hi = -0.99, 10.0
    for _ in range(100):
        mid = (lo + hi) / 2
        npv = sum(v / ((1 + mid) ** i) for i, v in enumerate(values))
        if abs(npv) < 1e-10:
            return mid
        if npv > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def fn_rate(args: List[Any]) -> float:
    """RATE(nper, pmt, pv, [fv], [type], [guess]) — interest rate per period."""
    nums = [_to_number(a) for a in args]
    if len(nums) < 3:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "RATE needs >=3 args"))
    nper = nums[0]
    pmt = nums[1]
    pv = nums[2]
    fv = nums[3] if len(nums) > 3 else 0
    pmt_type = int(nums[4]) if len(nums) > 4 else 0
    guess = nums[5] if len(nums) > 5 else 0.1

    # Newton's method on the annuity equation
    rate = guess
    for _ in range(100):
        factor = (1 + rate) ** nper
        f = pv * factor + pmt * (1 + rate * pmt_type) * (factor - 1) / rate + fv
        df = pv * nper * (1 + rate) ** (nper - 1) + \
             pmt * (1 + pmt_type) * (nper * (1 + rate) ** (nper - 1) * rate - (factor - 1)) / (rate ** 2)
        if abs(f) < 1e-10:
            return rate
        if df == 0:
            break
        rate -= f / df
    return rate


def fn_sln(args: List[Any]) -> float:
    """SLN(cost, salvage, life) — straight-line depreciation per period."""
    nums = [_to_number(a) for a in args]
    if len(nums) != 3:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "SLN needs 3 args"))
    cost, salvage, life = nums
    if life == 0:
        raise SpreadsheetFuncError(CellError(ErrorType.DIV_ZERO, "SLN: life=0"))
    return (cost - salvage) / life


def fn_syd(args: List[Any]) -> float:
    """SYD(cost, salvage, life, period) — sum-of-years' digits depreciation."""
    nums = [_to_number(a) for a in args]
    if len(nums) != 4:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "SYD needs 4 args"))
    cost, salvage, life, period = nums
    if life == 0:
        raise SpreadsheetFuncError(CellError(ErrorType.DIV_ZERO, "SYD: life=0"))
    return (cost - salvage) * (life - period + 1) / (life * (life + 1) / 2)


# ---------------------------------------------------------------------------
# Information functions
# ---------------------------------------------------------------------------

def fn_isna(args: List[Any]) -> bool:
    return len(args) == 1 and isinstance(args[0], CellError) and args[0].type == ErrorType.NA


def fn_isref(args: List[Any]) -> bool:
    # In our engine, we don't have a dedicated reference type at eval time,
    # but we can check if the value is a list (from a range) or scalar.
    return True  # Any arg is technically a valid reference in our model


def fn_islogical(args: List[Any]) -> bool:
    return len(args) == 1 and isinstance(args[0], bool)


def defn_isnontext(args: List[Any]) -> bool:
    if len(args) != 1:
        return False
    v = args[0]
    return not isinstance(v, str) or v is None


def fn_iserr(args: List[Any]) -> bool:
    """ISERR — TRUE if value is any error except #N/A."""
    if len(args) != 1:
        return False
    v = args[0]
    return isinstance(v, CellError) and v.type != ErrorType.NA


def fn_isodd(args: List[Any]) -> bool:
    """ISODD(number) — TRUE if number is odd."""
    _propagate_errors(args)
    return int(_to_number(args[0])) % 2 != 0


def fn_iseven(args: List[Any]) -> bool:
    """ISEVEN(number) — TRUE if number is even."""
    _propagate_errors(args)
    return int(_to_number(args[0])) % 2 == 0


def fn_istext_enhanced(args: List[Any]) -> bool:
    """ISTEXT — TRUE if value is text (string)."""
    if len(args) != 1:
        return False
    return isinstance(args[0], str) and not isinstance(args[0], bool)


def fn_type(args: List[Any]) -> float:
    """TYPE(value) — returns type code: 1=number, 2=text, 4=logical, 16=error, 64=array."""
    if len(args) != 1:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "TYPE needs 1 arg"))
    v = args[0]
    if isinstance(v, CellError):
        return 16.0
    if isinstance(v, bool):
        return 4.0
    if isinstance(v, (int, float)):
        return 1.0
    if isinstance(v, str):
        return 2.0
    if isinstance(v, (list, tuple)):
        return 64.0
    return 128.0


def fn_errortype(args: List[Any]) -> float:
    """ERROR.TYPE(error) — numeric code for error type."""
    if len(args) != 1 or not isinstance(args[0], CellError):
        raise SpreadsheetFuncError(CellError(ErrorType.NA, "ERROR.TYPE: not an error"))
    codes = {
        ErrorType.NULL: 1,
        ErrorType.DIV_ZERO: 2,
        ErrorType.VALUE: 3,
        ErrorType.REF: 4,
        ErrorType.NAME: 5,
        ErrorType.NUM: 6,
        ErrorType.NA: 7,
    }
    return float(codes.get(args[0].type, 8))


# ---------------------------------------------------------------------------
# Register extended functions
# ---------------------------------------------------------------------------

EXTENDED_FUNCTIONS: Dict[str, Any] = {
    # Date/Time
    "TODAY": fn_today,
    "NOW": fn_now,
    "DATE": fn_date,
    "YEAR": fn_year,
    "MONTH": fn_month,
    "DAY": fn_day,
    "WEEKDAY": fn_weekday,
    "HOUR": fn_hour,
    "MINUTE": fn_minute,
    "SECOND": fn_second,
    # Financial
    "PV": fn_pv,
    "FV": fn_fv,
    "PMT": fn_pmt,
    "NPV": fn_npv,
    "IRR": fn_irr,
    "RATE": fn_rate,
    "SLN": fn_sln,
    "SYD": fn_syd,
    # Information
    "ISNA": fn_isna,
    "ISREF": fn_isref,
    "ISLOGICAL": fn_islogical,
    "ISNONTEXT": defn_isnontext,
    "ISERR": fn_iserr,
    "ISODD": fn_isodd,
    "ISEVEN": fn_iseven,
    "TYPE": fn_type,
    "ERROR.TYPE": fn_errortype,
}


def register_extended_functions() -> None:
    """Register all extended functions in the main FUNCTIONS registry."""
    for name, func in EXTENDED_FUNCTIONS.items():
        if name not in FUNCTIONS:
            FUNCTIONS[name] = func


# Auto-register on import
register_extended_functions()