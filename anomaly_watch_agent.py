#!/usr/bin/env python3
"""
Anomaly Watch Agent

Reads a CSV of payments and checks the latest week against each supplier's
own history. A payment is flagged when its amount sits outside that supplier's
usual band, when it repeats an earlier payment to the same supplier, or when it
goes to an account that supplier hasn't used before. An unusual weekday is
shown as context but never flags a payment on its own.

Read-only: it reports what looks unusual and why. It never blocks, holds or
sends anything. Nothing here connects to a real supplier list, a bank, or an
ERP system. Sample data only.
"""

import argparse
import csv
import statistics
from collections import Counter, defaultdict
from datetime import date, timedelta

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
ALL_SIGNALS = ("amount", "duplicate", "account")


def load_payments(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["date"] = date.fromisoformat(r["date"])
        r["amount"] = float(r["amount"])
    return rows


def week_start_of(d):
    return d - timedelta(days=d.weekday())


def baseline(history):
    """Per supplier: median amount, scale (robust spread), usual weekday, known accounts."""
    by_supplier = defaultdict(list)
    for r in history:
        by_supplier[r["supplier"]].append(r)
    out = {}
    for supplier, rows in by_supplier.items():
        amounts = [r["amount"] for r in rows]
        med = statistics.median(amounts)
        mad = statistics.median([abs(a - med) for a in amounts])
        scale = max(1.4826 * mad, 0.01 * med)  # floor keeps fixed-amount suppliers from dividing by zero
        weekday = Counter(r["date"].weekday() for r in rows).most_common(1)[0][0]
        out[supplier] = {"median": med, "scale": scale, "weekday": weekday,
                         "accounts": {r["account"] for r in rows}}
    return out


def check(payment, base, earlier, tolerance, dup_days, signals):
    reasons = []
    b = base.get(payment["supplier"])
    if b is None:
        return reasons
    z = abs(payment["amount"] - b["median"]) / b["scale"]
    if "amount" in signals and z > tolerance:
        ratio = payment["amount"] / b["median"]
        reasons.append(f"amount {ratio:.1f}x usual ({b['median']:,.0f} +/- {b['scale']:,.0f})")
    if "duplicate" in signals:
        for e in earlier:
            if (e["supplier"] == payment["supplier"] and e["amount"] == payment["amount"]
                    and 0 < (payment["date"] - e["date"]).days <= dup_days):
                reasons.append(f"same amount paid {(payment['date'] - e['date']).days}d earlier")
                break
    if "account" in signals and payment["account"] not in b["accounts"]:
        reasons.append("new account for this supplier")
    if reasons and payment["date"].weekday() != b["weekday"]:
        reasons.append(f"usual day {WEEKDAYS[b['weekday']]}")
    return reasons


def main():
    ap = argparse.ArgumentParser(description="Flag payments that don't look like a supplier's own history.")
    ap.add_argument("csv_path", help="path to a CSV of payments")
    ap.add_argument("--week-start", help="Monday of the week to check, YYYY-MM-DD (default: the latest week in the file)")
    ap.add_argument("--tolerance", type=float, default=3.5, help="how many robust spreads from the usual amount counts as unusual (default 3.5)")
    ap.add_argument("--dup-days", type=int, default=5, help="window for repeated amounts, in days (default 5)")
    ap.add_argument("--signals", default=",".join(ALL_SIGNALS),
                    help="comma-separated signals to use: amount, duplicate, account (default: all)")
    args = ap.parse_args()

    signals = {s.strip() for s in args.signals.split(",")}
    payments = load_payments(args.csv_path)
    ws = date.fromisoformat(args.week_start) if args.week_start else week_start_of(max(p["date"] for p in payments))
    we = ws + timedelta(days=7)
    history = [p for p in payments if p["date"] < ws]
    this_week = sorted((p for p in payments if ws <= p["date"] < we), key=lambda p: (p["date"], p["id"]))
    base = baseline(history)

    print("=" * 64)
    print("  Anomaly Watch Agent — Unusual Payment Check")
    print("=" * 64)
    print()
    print(f"[Step 1] Loaded {len(payments)} payment(s) from CSV")
    print(f"[Step 2] Built a baseline per supplier from {len(history)} payment(s) before {ws.isoformat()}")
    print(f"[Step 3] Checking {len(this_week)} payment(s) in the week of {ws.isoformat()} against each supplier's own history")
    print()

    flagged = 0
    earlier_all = list(history)
    for p in this_week:
        reasons = check(p, base, earlier_all, args.tolerance, args.dup_days, signals)
        earlier_all.append(p)
        if reasons:
            flagged += 1
            print(f"{p['id']}  {p['date'].isoformat()} {WEEKDAYS[p['date'].weekday()]}  "
                  f"{p['supplier']:<24}{int(p['amount']):>7,}  ⚠ " + " · ".join(reasons))

    print()
    print(f"[Step 4] {flagged} of {len(this_week)} payment(s) flagged")
    print("[Step 5] Nothing is blocked or sent — a person looks at each flag")


if __name__ == "__main__":
    main()
