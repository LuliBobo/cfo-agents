#!/usr/bin/env python3
"""
Collections Priority Agent

Reads a CSV of open receivables and prints a suggested collections order
that isn't just sorted by days overdue. An active credit hold moves a
receivable ahead of an older one. Reminder history is tracked and
displayed; it only changes the rank if you set --reminder-threshold.

Read-only: it reports a suggested order and never sends a reminder.
Nothing here connects to a real customer list, a CRM, or a bank.
Sample data only.
"""

import argparse
import csv

DEFAULT_HOLD_VALUES = "true,yes,1"


def load_receivables(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def has_hold(rec, hold_values):
    return rec["credit_hold"].strip().lower() in hold_values


def suggested_order(receivables, hold_values, reminder_threshold):
    def priority(rec):
        if has_hold(rec, hold_values):
            return True
        return reminder_threshold is not None and int(rec["reminders_sent"]) >= reminder_threshold

    flagged = [r for r in receivables if priority(r)]
    rest = [r for r in receivables if not priority(r)]

    flagged.sort(key=lambda r: -int(r["days_overdue"]))
    rest.sort(key=lambda r: -int(r["days_overdue"]))

    return flagged + rest, {r["customer_id"] for r in flagged}


def main():
    parser = argparse.ArgumentParser(description="Suggest a collections order for open receivables.")
    parser.add_argument("csv_path", help="path to a CSV of open receivables")
    parser.add_argument(
        "--hold-values",
        default=DEFAULT_HOLD_VALUES,
        help=f"comma-separated credit_hold values that count as an active hold (default: {DEFAULT_HOLD_VALUES})",
    )
    parser.add_argument(
        "--reminder-threshold",
        type=int,
        default=None,
        help="if set, receivables with at least this many reminders sent also move to the front",
    )
    args = parser.parse_args()

    hold_values = {v.strip().lower() for v in args.hold_values.split(",")}
    receivables = load_receivables(args.csv_path)

    print("=" * 64)
    print("  Collections Priority Agent — Suggested Chase Order")
    print("=" * 64)
    print()
    print(f"[Step 1] Loaded {len(receivables)} open receivable(s) from CSV")
    print("[Step 2] Ranked by days overdue")
    print("[Step 3] Checking for credit-hold flags and reminder history")
    print()

    ordered, flagged_ids = suggested_order(receivables, hold_values, args.reminder_threshold)
    overdue_order_ids = [
        r["customer_id"] for r in sorted(receivables, key=lambda r: -int(r["days_overdue"]))
    ]

    moved = 0
    for rank, rec in enumerate(ordered, start=1):
        flag = ""
        if rec["customer_id"] in flagged_ids:
            overdue_rank = overdue_order_ids.index(rec["customer_id"]) + 1
            if overdue_rank != rank:
                flag = f"  ⚠ REORDERED → #{rank}"
                moved += 1
        amount = f"{int(rec['amount']):,}"
        hold_tag = "  HOLD" if has_hold(rec, hold_values) else ""
        print(
            f"{rec['customer_id']:<9}{rec['customer']:<24}{amount:>6}  "
            f"{rec['days_overdue']}d overdue{hold_tag}{flag}"
        )

    print()
    print(f"[Step 4] {moved} of {len(receivables)} receivable(s) reordered ahead of an older balance")
    print("[Step 5] Suggested collections order printed above")


if __name__ == "__main__":
    main()
