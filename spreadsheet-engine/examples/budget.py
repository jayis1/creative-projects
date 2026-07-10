#!/usr/bin/env python3
"""
Example: building a simple financial model with the spreadsheet engine.

This script creates a budget spreadsheet with:
  - Income sources
  - Expense categories
  - Totals using SUM
  - Net income calculation
  - Percentage of income per category
"""

from spreadsheet import Engine


def main():
    engine = Engine()
    sheet = engine.add_sheet("Budget")

    # --- Income ---
    engine.set("Budget", "A1", "Income")
    engine.set("Budget", "B1", "Amount")
    engine.set("Budget", "A2", "Salary")
    engine.set("Budget", "B2", "5000")
    engine.set("Budget", "A3", "Freelance")
    engine.set("Budget", "B3", "1200")
    engine.set("Budget", "A4", "Investment")
    engine.set("Budget", "B4", "300")
    engine.set("Budget", "A5", "Total Income")
    engine.set("Budget", "B5", "=SUM(B2:B4)")

    # --- Expenses ---
    engine.set("Budget", "A7", "Expenses")
    engine.set("Budget", "B7", "Amount")
    engine.set("Budget", "A8", "Rent")
    engine.set("Budget", "B8", "1500")
    engine.set("Budget", "A9", "Food")
    engine.set("Budget", "B9", "600")
    engine.set("Budget", "A10", "Transport")
    engine.set("Budget", "B10", "400")
    engine.set("Budget", "A11", "Entertainment")
    engine.set("Budget", "B11", "200")
    engine.set("Budget", "A12", "Total Expenses")
    engine.set("Budget", "B12", "=SUM(B8:B11)")

    # --- Summary ---
    engine.set("Budget", "A14", "Net Income")
    engine.set("Budget", "B14", "=B5-B12")
    engine.set("Budget", "A15", "Savings Rate")
    engine.set("Budget", "B15", "=IF(B5>0, B14/B5, 0)")
    engine.set("Budget", "A16", "Rent % of Income")
    engine.set("Budget", "B16", "=IF(B5>0, B8/B5, 0)")

    # Recalculate
    stats = engine.recalculate()
    print(f"Recalculation: {stats['evaluated']} cells evaluated\n")

    # Display
    print(engine.display("Budget", max_rows=20, max_cols=20))

    # Show key results
    print(f"\nTotal Income:    {engine.get('Budget', 'B5')}")
    print(f"Total Expenses:  {engine.get('Budget', 'B12')}")
    print(f"Net Income:      {engine.get('Budget', 'B14')}")
    print(f"Savings Rate:    {engine.get('Budget', 'B15'):.1%}")
    print(f"Rent % of Income: {engine.get('Budget', 'B16'):.1%}")


if __name__ == "__main__":
    main()