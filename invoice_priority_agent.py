#!/usr/bin/env python3
"""
Invoice Priority Agent

Reads a CSV of open invoices and prints a suggested payment order that
isn't just sorted by due date. Two signals can move an invoice ahead of
an older one: a flagged critical vendor, or an active early-payment
discount window (tracked and displayed, though in this version only the
critical-vendor flag changes the rank -- see README).

Nothing here connects to a real vendor list, a bank, or an ERP system.
Sample data only.
"""

import csv
import sys


def load_invoices(path):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def suggested_order(invoices):
    critical = [i for i in invoices if i["critical_vendor"].strip().lower() == "true"]
    rest = [i for i in invoices if i not in critical]

    critical.sort(key=lambda i: int(i["due_in_days"]))
    rest.sort(key=lambda i: int(i["due_in_days"]))

    return critical + rest, {i["invoice_id"] for i in critical}


def main():
    if len(sys.argv) != 2:
        print("Usage: python invoice_priority_agent.py <path-to-csv>")
        sys.exit(1)

    path = sys.argv[1]
    invoices = load_invoices(path)

    print("=" * 64)
    print("  Invoice Priority Agent -- Suggested Payment Order")
    print("=" * 64)
    print()
    print(f"[Step 1] Loaded {len(invoices)} open invoice(s) from CSV")
    print("[Step 2] Calculated days-to-due for each invoice")
    print("[Step 3] Checking for discount windows and critical-vendor flags")
    print()

    ordered, reordered_ids = suggested_order(invoices)
    due_order_ids = [i["invoice_id"] for i in sorted(invoices, key=lambda i: int(i["due_in_days"]))]

    moved = 0
    for rank, inv in enumerate(ordered, start=1):
        flag = ""
        if inv["invoice_id"] in reordered_ids:
            due_rank = due_order_ids.index(inv["invoice_id"]) + 1
            if due_rank != rank:
                flag = f"  ⚠ REORDERED -> #{rank}"
                moved += 1
        amount = f"{int(inv['amount']):,}"
        critical_tag = "  CRITICAL" if inv["critical_vendor"].strip().lower() == "true" else ""
        print(f"{inv['invoice_id']:<8}{inv['vendor']:<24}{amount:>8}  due in {inv['due_in_days']}d{critical_tag}{flag}")

    print()
    print(f"[Step 4] {moved} of {len(invoices)} invoice(s) reordered ahead of an older invoice")
    print("[Step 5] Suggested payment order printed above -- due-date order alone would have missed both")


if __name__ == "__main__":
    main()
