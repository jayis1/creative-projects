#!/usr/bin/env python3
"""
Example: Financial modeling with the spreadsheet engine.

Demonstrates the extended financial functions (PMT, PV, FV, NPV, IRR)
and date functions for a loan amortization and investment analysis scenario.
"""

from spreadsheet import Engine


def main():
    engine = Engine()
    sheet = engine.add_sheet("Loan")

    # --- Loan parameters ---
    engine.set("Loan", "A1", "Loan Amount")
    engine.set("Loan", "B1", "250000")
    engine.set("Loan", "A2", "Annual Rate")
    engine.set("Loan", "B2", "0.055")
    engine.set("Loan", "A3", "Years")
    engine.set("Loan", "B3", "30")
    engine.set("Loan", "A4", "Payments/Year")
    engine.set("Loan", "B4", "12")

    # --- Calculated values ---
    engine.set("Loan", "A6", "Monthly Rate")
    engine.set("Loan", "B6", "=B2/B4")
    engine.set("Loan", "A7", "Total Periods")
    engine.set("Loan", "B7", "=B3*B4")
    engine.set("Loan", "A8", "Monthly Payment")
    engine.set("Loan", "B8", "=PMT(B6, B7, B1)")

    # --- Future value after 10 years ---
    engine.set("Loan", "A10", "FV after 10yr")
    engine.set("Loan", "B10", "=FV(B6, B4*10, B8, -B1)")

    # --- Present value of payment stream ---
    engine.set("Loan", "A11", "PV of payments")
    engine.set("Loan", "B11", "=PV(B6, B7, B8)")

    # --- Investment analysis ---
    inv = engine.add_sheet("Investment")
    engine.set("Investment", "A1", "Year")
    engine.set("Investment", "B1", "Cash Flow")
    engine.set("Investment", "A2", "0")
    engine.set("Investment", "B2", "-100000")
    engine.set("Investment", "A3", "1")
    engine.set("Investment", "B3", "25000")
    engine.set("Investment", "A4", "2")
    engine.set("Investment", "B4", "30000")
    engine.set("Investment", "A5", "3")
    engine.set("Investment", "B5", "35000")
    engine.set("Investment", "A6", "4")
    engine.set("Investment", "B6", "40000")
    engine.set("Investment", "A7", "5")
    engine.set("Investment", "B7", "45000")

    engine.set("Investment", "A9", "NPV @ 8%")
    engine.set("Investment", "B9", "=NPV(0.08, B3:B7) + B2")
    engine.set("Investment", "A10", "IRR")
    engine.set("Investment", "B10", "=IRR(B2:B7)")

    # --- Straight-line depreciation ---
    dep = engine.add_sheet("Depreciation")
    engine.set("Depreciation", "A1", "Asset Cost")
    engine.set("Depreciation", "B1", "50000")
    engine.set("Depreciation", "A2", "Salvage Value")
    engine.set("Depreciation", "B2", "5000")
    engine.set("Depreciation", "A3", "Useful Life")
    engine.set("Depreciation", "B3", "5")
    engine.set("Depreciation", "A4", "Annual Depreciation")
    engine.set("Depreciation", "B4", "=SLN(B1, B2, B3)")

    # --- Date functions ---
    dates = engine.add_sheet("Dates")
    engine.set("Dates", "A1", "Today")
    engine.set("Dates", "B1", "=TODAY()")
    engine.set("Dates", "A2", "Year")
    engine.set("Dates", "B2", "=YEAR(B1)")
    engine.set("Dates", "A3", "Month")
    engine.set("Dates", "B3", "=MONTH(B1)")
    engine.set("Dates", "A4", "Day")
    engine.set("Dates", "B4", "=DAY(B1)")
    engine.set("Dates", "A5", "Weekday")
    engine.set("Dates", "B5", "=WEEKDAY(B1)")

    # Recalculate
    stats = engine.recalculate()
    print(f"Recalculation: {stats['evaluated']} cells, {stats['errors']} errors\n")

    # Display results
    print("=== Loan Summary ===")
    print(f"  Loan Amount:     ${engine.get('Loan', 'B1'):,.0f}")
    print(f"  Monthly Payment: ${-engine.get('Loan', 'B8'):,.2f}")
    print(f"  Total Interest:  ${(-engine.get('Loan', 'B8') * engine.get('Loan', 'B7')) - engine.get('Loan', 'B1'):,.0f}")
    print(f"  FV after 10yr:   ${engine.get('Loan', 'B10'):,.2f}")

    print("\n=== Investment Analysis ===")
    print(f"  NPV @ 8%:  ${engine.get('Investment', 'B9'):,.2f}")
    irr = engine.get('Investment', 'B10')
    print(f"  IRR:       {irr:.2%}")

    print("\n=== Depreciation ===")
    print(f"  Annual Dep: ${engine.get('Depreciation', 'B4'):,.2f}/year")

    print("\n=== Dates ===")
    today_serial = engine.get('Dates', 'B1')
    print(f"  Today serial: {today_serial}")
    print(f"  Year:  {engine.get('Dates', 'B2'):.0f}")
    print(f"  Month: {engine.get('Dates', 'B3'):.0f}")
    print(f"  Day:   {engine.get('Dates', 'B4'):.0f}")
    print(f"  Weekday (1=Sun..7=Sat): {engine.get('Dates', 'B5'):.0f}")

    # Display the loan sheet
    print("\n=== Loan Sheet ===")
    print(engine.display("Loan", max_rows=15, max_cols=10))


if __name__ == "__main__":
    main()