#!/usr/bin/env python3
"""
Example: building a simple financial model with the spreadsheet engine.

This script creates a budget spreadsheet with:
  - Income sources
  - Expense categories
  - Totals using SUM
  - Net income calculation
  - Percentage of income per category
  - Named ranges for clarity
  - VLOOKUP for category descriptions
  - Formula auditing
"""

from spreadsheet import Engine


def main():
    engine = Engine()
    sheet = engine.add_sheet("Budget")

    # --- Income ---
    engine.set("Budget", "A1", "Income")
    engine.set("Budget", "B1", "Amount")
    engine.set("Budget", "C1", "Description")
    engine.set("Budget", "A2", "Salary")
    engine.set("Budget", "B2", "5000")
    engine.set("Budget", "C2", "Monthly salary")
    engine.set("Budget", "A3", "Freelance")
    engine.set("Budget", "B3", "1200")
    engine.set("Budget", "C3", "Side projects")
    engine.set("Budget", "A4", "Investment")
    engine.set("Budget", "B4", "300")
    engine.set("Budget", "C4", "Dividends")
    engine.set("Budget", "A5", "Total Income")
    engine.set("Budget", "B5", "=SUM(B2:B4)")

    # --- Expenses ---
    engine.set("Budget", "A7", "Expenses")
    engine.set("Budget", "B7", "Amount")
    engine.set("Budget", "C7", "Description")
    engine.set("Budget", "A8", "Rent")
    engine.set("Budget", "B8", "1500")
    engine.set("Budget", "C8", "Apartment")
    engine.set("Budget", "A9", "Food")
    engine.set("Budget", "B9", "600")
    engine.set("Budget", "C9", "Groceries & dining")
    engine.set("Budget", "A10", "Transport")
    engine.set("Budget", "B10", "400")
    engine.set("Budget", "C10", "Gas & transit")
    engine.set("Budget", "A11", "Entertainment")
    engine.set("Budget", "B11", "200")
    engine.set("Budget", "C11", "Streaming & outings")
    engine.set("Budget", "A12", "Total Expenses")
    engine.set("Budget", "B12", "=SUM(B8:B11)")

    # --- Summary with enhanced formulas ---
    engine.set("Budget", "A14", "Net Income")
    engine.set("Budget", "B14", "=B5-B12")
    engine.set("Budget", "A15", "Savings Rate")
    engine.set("Budget", "B15", "=IF(B5>0, B14/B5, 0)")
    engine.set("Budget", "A16", "Rent % of Income")
    engine.set("Budget", "B16", "=IFERROR(B8/B5, 0)")
    engine.set("Budget", "A17", "Status")
    engine.set("Budget", "B17", '=IF(B14>0, "Surplus", "Deficit")')
    engine.set("Budget", "A18", "Avg Expense")
    engine.set("Budget", "B18", "=AVERAGE(B8:B11)")
    engine.set("Budget", "A19", "Max Expense")
    engine.set("Budget", "B19", "=MAX(B8:B11)")
    engine.set("Budget", "A20", "Min Expense")
    engine.set("Budget", "B20", "=MIN(B8:B11)")

    # --- Define named ranges ---
    engine.define_name("TotalIncome", "Budget", "B5")
    engine.define_name("TotalExpenses", "Budget", "B12")

    # Recalculate
    stats = engine.recalculate()
    print(f"Recalculation: {stats['evaluated']} cells evaluated\n")

    # Display
    print(engine.display("Budget", max_rows=25, max_cols=25))

    # Show key results
    print(f"\n--- Summary ---")
    print(f"Total Income:    {engine.get('Budget', 'B5')}")
    print(f"Total Expenses:  {engine.get('Budget', 'B12')}")
    print(f"Net Income:      {engine.get('Budget', 'B14')}")
    print(f"Savings Rate:    {engine.get('Budget', 'B15'):.1%}")
    print(f"Rent % of Income: {engine.get('Budget', 'B16'):.1%}")
    print(f"Status:          {engine.get('Budget', 'B17')}")
    print(f"Avg Expense:     {engine.get('Budget', 'B18')}")
    print(f"Max Expense:     {engine.get('Budget', 'B19')}")

    # Formula auditing
    print(f"\n--- Formula Audit: B14 (Net Income) ---")
    audit = engine.audit_cell("Budget", "B14")
    print(f"Formula: {audit['raw']}")
    print(f"Value:   {audit['value']}")
    print(f"Precedents: {[p['ref'] for p in audit['precedents']]}")
    print(f"Dependents: {[d['ref'] for d in audit['dependents']]}")

    # Named ranges
    print(f"\n--- Named Ranges ---")
    for name, nr in engine.list_names().items():
        print(f"  {name}: {nr}")

    # Incremental recalculation demo
    print(f"\n--- Incremental Recalculation Demo ---")
    print(f"Changing B2 (Salary) from 5000 to 6000...")
    engine.set("Budget", "B2", "6000")
    stats = engine.recalculate_affected([("Budget", 1, 1)])
    print(f"  Recalculated {stats['evaluated']} cells (not all)")
    print(f"  New Total Income: {engine.get('Budget', 'B5')}")
    print(f"  New Net Income:   {engine.get('Budget', 'B14')}")


if __name__ == "__main__":
    main()