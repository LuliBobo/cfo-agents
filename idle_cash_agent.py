#!/usr/bin/env python3
"""
Idle Cash Agent — personal, non-commercial prototype
Post #10 companion script — github.com/LuliBobo/cfo-agents

This is a small experiment, not a product. It reads a CSV of account
balances, compares each one against its agreed operating buffer, and
estimates what the excess sitting above that buffer could have earned
if it had been swept into something that pays interest — instead of
finding out at month-end close, if at all.

Not connected to, and not built for, any company or client. It's a
personal experiment in what a routine "is this balance sitting idle"
check would actually need to compute — nothing more. It only reads
and reports; it never moves money or connects to a bank.

Usage:
    python idle_cash_agent.py data/account_balances.csv --threshold 50000 --rate 3.0
"""

import argparse
import csv
import sys
from dataclasses import dataclass, field


@dataclass
class Account:
    account_id: str
    account_name: str
    balance: float
    buffer: float
    alt_rate_pct: float  # per-account alternative rate, from the CSV; falls back to --rate if blank

    excess: float = field(init=False)

    def __post_init__(self):
        self.excess = max(0.0, self.balance - self.buffer)


def load_accounts(csv_path: str, default_rate: float) -> list[Account]:
    accounts = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rate_field = row.get("alt_rate_pct", "").strip()
            rate = float(rate_field) if rate_field else default_rate
            accounts.append(
                Account(
                    account_id=row["account_id"],
                    account_name=row["account_name"],
                    balance=float(row["balance"]),
                    buffer=float(row["buffer"]),
                    alt_rate_pct=rate,
                )
            )
    return accounts


def flag_accounts(accounts: list[Account], threshold: float) -> list[Account]:
    return [a for a in accounts if a.excess >= threshold]


def print_report(accounts: list[Account], threshold: float) -> None:
    flagged = flag_accounts(accounts, threshold)

    print("=" * 64)
    print("  Idle Cash Agent — Balance vs Buffer Check")
    print("=" * 64)
    print(f"\n[Step 1] Loaded {len(accounts)} account balance(s) from CSV")
    print("[Step 2] Comparing each balance to its configured buffer")
    print(f"[Step 3] Flagging anything with more than €{threshold:,.0f} sitting idle above buffer\n")

    for a in flagged:
        flag = "⚠ FLAG"
        print(
            f"{a.account_id:<6} {a.account_name:<20} {a.balance:>10,.0f} "
            f"{a.buffer:>9,.0f} {a.excess:>9,.0f}  {a.alt_rate_pct:>4.2f}%  {flag}"
        )

    print(f"\n[Step 4] {len(flagged)} of {len(accounts)} account(s) flagged")

    if flagged:
        total_excess = sum(a.excess for a in flagged)
        weighted_annual = sum(a.excess * (a.alt_rate_pct / 100) for a in flagged)
        weighted_monthly = weighted_annual / 12
        print(
            f"[Step 5] Estimated forgone interest: ~€{weighted_annual:,.0f}/year "
            f"(~€{weighted_monthly:,.0f}/month)"
        )
        print(f"\nTotal idle excess across flagged accounts: €{total_excess:,.0f}")
        print("\nThis is an illustrative estimate based on sample data, not a measured")
        print("benchmark or advice on what to do with any specific balance.")
    else:
        print("[Step 5] Nothing past the threshold today.")


def main():
    parser = argparse.ArgumentParser(
        description="Idle Cash Agent — flags account balances sitting well above their agreed buffer."
    )
    parser.add_argument(
        "csv_path", nargs="?", default="data/account_balances.csv",
        help="Path to the account balances CSV",
    )
    parser.add_argument(
        "--threshold", type=float, default=50000,
        help="Excess-above-buffer threshold in EUR to flag an account (default: 50000)",
    )
    parser.add_argument(
        "--rate", type=float, default=3.0,
        help="Default alternative annual rate in percent, used when a row doesn't specify its own (default: 3.0)",
    )
    args = parser.parse_args()

    try:
        accounts = load_accounts(args.csv_path, args.rate)
    except FileNotFoundError:
        print(f"Could not find {args.csv_path}", file=sys.stderr)
        sys.exit(1)

    if not accounts:
        print("No accounts found in the CSV.")
        return

    print_report(accounts, args.threshold)


if __name__ == "__main__":
    main()
