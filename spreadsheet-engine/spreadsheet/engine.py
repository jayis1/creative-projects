"""
Engine — the core spreadsheet engine.

Manages multiple sheets, parses formulas, evaluates cell references,
resolves dependencies, detects cycles, and performs recalculation
via topological sort.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Tuple

from .cell import Cell, CellError, CellType, ErrorType, format_a1, parse_a1
from .functions import SpreadsheetFuncError, call_function
from .parser import (
    Bool,
    BinOp,
    CellRef,
    FuncCall,
    Num,
    RangeRef,
    Str,
    UnaryOp,
    extract_refs,
    parse_formula,
)
from .sheet import Sheet, _format_value


class EngineError(Exception):
    """Top-level engine exception."""


class Engine:
    """
    The spreadsheet engine.

    Usage:
        engine = Engine()
        sheet = engine.add_sheet("Sheet1")
        engine.set("Sheet1", "A1", "=B1+B2")
        engine.set("Sheet1", "B1", "10")
        engine.set("Sheet1", "B2", "20")
        engine.recalculate()
        print(engine.get("Sheet1", "A1"))  # 30.0
    """

    def __init__(self):
        self.sheets: Dict[str, Sheet] = {}
        self._eval_stack: Set[Tuple[str, int, int]] = set()  # for cycle detection

    # ---- sheet management ----

    def add_sheet(self, name: str) -> Sheet:
        if name in self.sheets:
            raise EngineError(f"Sheet {name!r} already exists")
        sheet = Sheet(name)
        self.sheets[name] = sheet
        return sheet

    def get_sheet(self, name: str) -> Sheet:
        if name not in self.sheets:
            raise EngineError(f"Sheet {name!r} does not exist")
        return self.sheets[name]

    def remove_sheet(self, name: str) -> None:
        if name not in self.sheets:
            raise EngineError(f"Sheet {name!r} does not exist")
        del self.sheets[name]

    def sheet_names(self) -> List[str]:
        return list(self.sheets.keys())

    # ---- cell access (convenience with sheet name + A1) ----

    def set(self, sheet: str, ref: str, raw: str) -> None:
        """Set a cell's raw value in the given sheet."""
        s = self.get_sheet(sheet)
        row, col = parse_a1(ref)
        s.set(row, col, raw)

    def get(self, sheet: str, ref: str) -> Any:
        """Get a cell's computed value from the given sheet."""
        s = self.get_sheet(sheet)
        row, col = parse_a1(ref)
        return s.get(row, col)

    def set_value(self, sheet: str, ref: str, value: Any) -> None:
        """Set a cell's value directly (Python value, not formula string)."""
        s = self.get_sheet(sheet)
        row, col = parse_a1(ref)
        s.set_value(row, col, value)

    # ---- formula evaluation ----

    def evaluate_cell(self, sheet_name: str, row: int, col: int) -> Any:
        """Evaluate a single cell, resolving formula dependencies recursively."""
        sheet = self.get_sheet(sheet_name)
        cell = sheet.cells.get((row, col))
        if cell is None or cell.is_empty():
            return None

        # Non-formula cells return their stored value
        if cell.type != CellType.FORMULA:
            return cell.value

        # Cycle detection
        key = (sheet_name, row, col)
        if key in self._eval_stack:
            # circular reference detected
            cell.value = CellError(ErrorType.CYCLE, f"Circular reference at {format_a1(row, col)}")
            cell.type = CellType.ERROR
            return cell.value

        # Parse formula if not already parsed
        if cell.formula is None:
            try:
                cell.formula = parse_formula(cell.raw)
            except Exception as e:
                cell.value = CellError(ErrorType.PARSE, f"Parse error: {e}")
                cell.type = CellType.ERROR
                return cell.value

        # Evaluate the AST
        self._eval_stack.add(key)
        try:
            result = self._eval_ast(cell.formula, sheet_name)
        except SpreadsheetFuncError as e:
            result = e.err
        except Exception as e:
            result = CellError(ErrorType.VALUE, f"Evaluation error: {e}")
        finally:
            self._eval_stack.discard(key)

        # Store result
        if isinstance(result, CellError):
            cell.value = result
            cell.type = CellType.ERROR
        else:
            cell.value = result
            cell.type = CellType.FORMULA  # keep as formula type, value is computed

        return result

    def _eval_ast(self, node: Any, current_sheet: str) -> Any:
        """Evaluate an AST node in the context of current_sheet."""
        if isinstance(node, Num):
            return node.value
        if isinstance(node, Str):
            return node.value
        if isinstance(node, Bool):
            return node.value
        if isinstance(node, UnaryOp):
            val = self._eval_ast(node.operand, current_sheet)
            if isinstance(val, CellError):
                return val
            if node.op == "-":
                try:
                    return -float(val)
                except (TypeError, ValueError):
                    return CellError(ErrorType.VALUE, "Cannot negate non-number")
            return val
        if isinstance(node, BinOp):
            left = self._eval_ast(node.left, current_sheet)
            right = self._eval_ast(node.right, current_sheet)
            return self._apply_binop(node.op, left, right)
        if isinstance(node, CellRef):
            sheet_name = node.sheet if node.sheet else current_sheet
            return self._resolve_ref(sheet_name, node.row, node.col)
        if isinstance(node, RangeRef):
            return self._resolve_range(node, current_sheet)
        if isinstance(node, FuncCall):
            args = [self._eval_ast(a, current_sheet) for a in node.args]
            return call_function(node.name, args)
        raise EngineError(f"Unknown AST node type: {type(node).__name__}")

    def _resolve_ref(self, sheet_name: str, row: int, col: int) -> Any:
        """Resolve a cell reference to its value (recursively evaluating)."""
        if sheet_name not in self.sheets:
            return CellError(ErrorType.REF, f"Sheet {sheet_name!r} not found")
        val = self.evaluate_cell(sheet_name, row, col)
        return val if val is not None else 0.0  # empty cells = 0 in arithmetic

    def _resolve_range(self, node: RangeRef, current_sheet: str) -> List[Any]:
        """Resolve a range reference to a flat list of cell values."""
        sheet_name = node.sheet if node.sheet else current_sheet
        if sheet_name not in self.sheets:
            return [CellError(ErrorType.REF, f"Sheet {sheet_name!r} not found")]
        r1, r2 = node.start.row, node.end.row
        c1, c2 = node.start.col, node.end.col
        r_lo, r_hi = min(r1, r2), max(r1, r2)
        c_lo, c_hi = min(c1, c2), max(c1, c2)
        result = []
        for r in range(r_lo, r_hi + 1):
            for c in range(c_lo, c_hi + 1):
                val = self.evaluate_cell(sheet_name, r, c)
                result.append(val)
        return result

    def _apply_binop(self, op: str, left: Any, right: Any) -> Any:
        """Apply a binary operator to two evaluated values."""
        # Error propagation
        if isinstance(left, CellError):
            return left
        if isinstance(right, CellError):
            return right

        # String concatenation with &
        if op == "&":
            return self._to_str_val(left) + self._to_str_val(right)

        # Comparison operators
        if op in ("=", "<>", ">", "<", ">=", "<="):
            return self._apply_comparison(op, left, right)

        # Arithmetic
        if op == "+":
            try:
                return self._coerce_num(left) + self._coerce_num(right)
            except (TypeError, ValueError):
                return CellError(ErrorType.VALUE, "Cannot add non-numeric values")
        if op == "-":
            try:
                return self._coerce_num(left) - self._coerce_num(right)
            except (TypeError, ValueError):
                return CellError(ErrorType.VALUE, "Cannot subtract non-numeric values")
        if op == "*":
            try:
                return self._coerce_num(left) * self._coerce_num(right)
            except (TypeError, ValueError):
                return CellError(ErrorType.VALUE, "Cannot multiply non-numeric values")
        if op == "/":
            try:
                r = self._coerce_num(right)
                if r == 0:
                    return CellError(ErrorType.DIV_ZERO, "Division by zero")
                return self._coerce_num(left) / r
            except (TypeError, ValueError):
                return CellError(ErrorType.VALUE, "Cannot divide non-numeric values")
        if op == "^":
            try:
                l = self._coerce_num(left)
                r = self._coerce_num(right)
                return float(l) ** float(r)
            except (TypeError, ValueError):
                return CellError(ErrorType.VALUE, "Cannot exponentiate non-numeric values")
        raise EngineError(f"Unknown operator: {op!r}")

    @staticmethod
    def _to_str_val(v: Any) -> str:
        """Convert a value to display string for concatenation."""
        if v is None:
            return ""
        if isinstance(v, bool):
            return "TRUE" if v else "FALSE"
        if isinstance(v, float):
            if v == int(v):
                return str(int(v))
            return repr(v)
        if isinstance(v, int):
            return str(v)
        return str(v)

    def _apply_comparison(self, op: str, left: Any, right: Any) -> bool:
        """Apply a comparison operator, with Excel-like type coercion."""
        # Excel comparison: numbers compared as numbers, strings compared as strings
        # (case-insensitive), booleans > numbers > strings in mixed comparisons
        l, r = left, right
        # Handle None as 0 for numeric comparison, "" for string comparison
        if l is None:
            l = 0
        if r is None:
            r = 0

        # If both are numeric (int/float, but not bool)
        l_num = isinstance(l, (int, float)) and not isinstance(l, bool)
        r_num = isinstance(r, (int, float)) and not isinstance(r, bool)
        if l_num and r_num:
            pass  # compare as numbers
        elif isinstance(l, str) and isinstance(r, str):
            l = l.upper()
            r = r.upper()
        elif isinstance(l, bool) or isinstance(r, bool):
            pass  # compare as-is (Python handles bool vs bool, bool vs int)

        if op == "=":
            return l == r
        if op == "<>":
            return l != r
        if op == ">":
            return l > r
        if op == "<":
            return l < r
        if op == ">=":
            return l >= r
        if op == "<=":
            return l <= r
        raise EngineError(f"Unknown comparison operator: {op!r}")

    @staticmethod
    def _coerce_num(v: Any) -> float:
        if isinstance(v, bool):
            return 1.0 if v else 0.0
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            try:
                return float(v.strip())
            except ValueError:
                raise TypeError(f"Cannot convert {v!r} to number")
        if v is None:
            return 0.0
        raise TypeError(f"Cannot convert {type(v).__name__} to number")

    # ---- dependency graph & recalculation ----

    def _build_dependency_graph(self) -> Tuple[
        Dict[Tuple[str, int, int], Set[Tuple[str, int, int]]],
        Dict[Tuple[str, int, int], Set[Tuple[str, int, int]]],
    ]:
        """
        Build the dependency graph.

        Returns:
            deps:    cell -> set of cells it depends on
            dependents: cell -> set of cells that depend on it
        """
        deps: Dict[Tuple[str, int, int], Set[Tuple[str, int, int]]] = defaultdict(set)
        dependents: Dict[Tuple[str, int, int], Set[Tuple[str, int, int]]] = defaultdict(set)

        for sheet_name, sheet in self.sheets.items():
            for cell in sheet.cells.values():
                if cell.type != CellType.FORMULA:
                    continue
                key = (sheet_name, cell.row, cell.col)
                # Ensure every formula cell is in the deps graph, even with no refs
                deps[key]  # defaultdict creates empty set
                # parse formula to get refs
                try:
                    if cell.formula is None:
                        cell.formula = parse_formula(cell.raw)
                    refs = extract_refs(cell.formula)
                    for ref_sheet, ref_row, ref_col in refs:
                        target_sheet = ref_sheet if ref_sheet else sheet_name
                        dep_key = (target_sheet, ref_row, ref_col)
                        deps[key].add(dep_key)
                        dependents[dep_key].add(key)
                        # also set deps on the cell object
                        cell.deps.add(dep_key)
                except Exception:
                    pass  # parse errors handled at eval time

        return deps, dependents

    def recalculate(self) -> Dict[str, int]:
        """
        Recalculate all formula cells in dependency order using topological sort.

        Returns:
            stats dict with 'evaluated', 'errors', 'cycles' counts
        """
        deps, dependents = self._build_dependency_graph()

        # Topological sort (Kahn's algorithm) over formula cells
        # Only formula cells need ordering; non-formula cells are leaf values.
        formula_keys = set(deps.keys())

        # in-degree: number of unresolved dependencies that are formula cells
        in_degree: Dict[Tuple[str, int, int], int] = {}
        for key in formula_keys:
            in_degree[key] = 0
            for dep in deps[key]:
                if dep in formula_keys:  # only count formula-cell deps
                    in_degree[key] += 1

        queue: deque = deque()
        for key, deg in in_degree.items():
            if deg == 0:
                queue.append(key)

        order: List[Tuple[str, int, int]] = []
        while queue:
            key = queue.popleft()
            order.append(key)
            for dependent in dependents.get(key, set()):
                if dependent in in_degree:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        # Any remaining formula cells are in cycles
        cyclic = [key for key, deg in in_degree.items() if deg > 0]

        # Evaluate in topological order
        evaluated = 0
        errors = 0
        cycles = 0

        for key in order:
            sheet_name, row, col = key
            self._eval_stack.clear()  # reset cycle detection stack
            result = self.evaluate_cell(sheet_name, row, col)
            evaluated += 1
            if isinstance(result, CellError):
                if result.type == ErrorType.CYCLE:
                    cycles += 1
                else:
                    errors += 1

        # Handle cyclic cells
        for key in cyclic:
            sheet_name, row, col = key
            cell = self.sheets[sheet_name].cells.get((row, col))
            if cell is not None:
                cell.value = CellError(ErrorType.CYCLE, f"Circular reference at {format_a1(row, col)}")
                cell.type = CellType.ERROR
                cycles += 1

        return {"evaluated": evaluated, "errors": errors, "cycles": cycles}

    # ---- import/export ----

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the engine state to a dict (JSON-compatible)."""
        result = {"sheets": {}}
        for name, sheet in self.sheets.items():
            cells = []
            for (r, c), cell in sorted(sheet.cells.items()):
                if cell.is_empty():
                    continue
                cells.append({
                    "ref": format_a1(r, c),
                    "raw": cell.raw,
                    "value": _serialize_value(cell.value),
                })
            result["sheets"][name] = cells
        return result

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Load engine state from a dict (as produced by to_dict)."""
        self.sheets.clear()
        for name, cells in data.get("sheets", {}).items():
            sheet = self.add_sheet(name)
            for cell_data in cells:
                ref = cell_data["ref"]
                raw = cell_data["raw"]
                sheet.set_a1(ref, raw)

    def export_csv(self, sheet_name: str) -> str:
        """Export a sheet to CSV."""
        import csv
        import io

        sheet = self.get_sheet(sheet_name)
        if not sheet.cells:
            return ""
        mr, mc, xr, xc = sheet.used_range()
        output = io.StringIO()
        writer = csv.writer(output)
        for r in range(mr, xr + 1):
            row_data = []
            for c in range(mc, xc + 1):
                val = sheet.get(r, c)
                row_data.append(_format_value(val))
            writer.writerow(row_data)
        return output.getvalue()

    def import_csv(self, sheet_name: str, csv_text: str) -> None:
        """Import CSV into a sheet (creates sheet if needed)."""
        import csv
        import io

        if sheet_name not in self.sheets:
            self.add_sheet(sheet_name)
        sheet = self.get_sheet(sheet_name)
        reader = csv.reader(io.StringIO(csv_text))
        for r, row in enumerate(reader):
            for c, val in enumerate(row):
                if val:
                    sheet.set(r, c, val)

    # ---- display ----

    def display(self, sheet_name: str, max_rows: int = 20, max_cols: int = 10) -> str:
        """Display a sheet as an ASCII grid."""
        return self.get_sheet(sheet_name).to_grid(max_rows, max_cols)


def _serialize_value(v: Any) -> Any:
    """Serialize a cell value for JSON."""
    if isinstance(v, CellError):
        return {"error": v.type.value, "message": v.message}
    if isinstance(v, bool):
        return {"type": "bool", "value": v}
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, str):
        return v
    if v is None:
        return None
    return str(v)