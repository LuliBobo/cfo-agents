#!/usr/bin/env python3
"""
FX Monitoring Agent — personal, non-commercial prototype
Post #9 companion script — github.com/LuliBobo/cfo-agents

This is a small experiment, not a product. It reads a CSV of open
FX-exposed positions (invoices billed in a foreign currency, still
unpaid), compares each one's booked exchange rate against a current
rate you supply, and flags anything that has drifted past a
configurable threshold — instead of waiting for month-end close to
find out.

Not connected to, and not built for, any company or client. It's a
personal experiment in what a daily FX check would actually need to
compute — nothing more.

Usage:
    python fx_monitor_agent.py data/fx_positions.csv --threshold 2.0
"""

import argparse
import csv
import sys
from dataclasses import dataclass, field
from datetime import date


@dataclass
class Position:
    position_id: str
    client: str
    currency_pair: str          # e.g. "EUR/USD" — 1 EUR = rate USD
    amount_foreign: float       # invoice amount in the foreign currency (e.g. USD)
    booked_rate: float          # EUR/USD rate on the day the invoice was issued
    current_rate: float         # EUR/USD rate as of today (or a supplied "as-of" rate)
    invoice_date: str

    eur_booked: float = field(init=False)
    eur_current: float = field(init=False)
    variance_eur: float = field(init=False)
    variance_pct: float = field(init=False)

    def __post_init__(self):
        self.eur_booked = self.amount_foreign / self.booked_rate
        self.eur_current = self.amount_foreign / self.current_rate
        self.variance_eur = self.eur_current - self.eur_booked
        self.variance_pct = (self.variance_eur / self.eur_booked) * 100


def load_positions(csv_path: str) -> list[Position]:
    positions = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            positions.append(
                Position(
                    position_id=row["position_id"],
                    client=row["client"],
                    currency_pair=row["currency_pair"],
                    amount_foreign=float(row["amount_foreign"]),
                    booked_rate=float(row["booked_rate"]),
                    current_rate=float(row["current_rate"]),
                    invoice_date=row["invoice_date"],
                )
            )
    return positions


def flag_positions(positions: list[Position], threshold_pct: float) -> list[Position]:
    return [p for p in positions if abs(p.variance_pct) >= threshold_pct]


def print_report(positions: list[Position], threshold_pct: float) -> None:
    positions_sorted = sorted(positions, key=lambda p: abs(p.variance_pct), reverse=True)
    flagged = flag_positions(positions, threshold_pct)
    total_variance = sum(p.variance_eur for p in positions)

    print("=" * 64)
    print("  FX Monitoring Agent — Open Position Check")
    print(f"  {date.today().isoformat()}")
    print("=" * 64)
    print(f"\n[Step 1] Loaded {len(positions)} open position(s) from CSV")
    print(f"[Step 2] Comparing booked rate vs current rate for each position")
    print(f"[Step 3] Flagging anything past ±{threshold_pct}% variance\n")

    header = f"{'ID':<8}{'Client':<16}{'Pair':<10}{'Booked':>9}{'Current':>9}{'Variance €':>13}{'Variance %':>12}  Flag"
    print(header)
    print("-" * len(header))
    for p in positions_sorted:
        flag = "⚠ FLAG" if abs(p.variance_pct) >= threshold_pct else ""
        print(
            f"{p.position_id:<8}{p.client:<16}{p.currency_pair:<10}"
            f"{p.booked_rate:>9.4f}{p.current_rate:>9.4f}"
            f"{p.variance_eur:>+13,.2f}{p.variance_pct:>+11.2f}%  {flag}"
        )

    print("-" * len(header))
    print(f"\n[Step 4] {len(flagged)} of {len(positions)} position(s) flagged")
    print(f"[Step 5] Net unrealized FX variance across all open positions: €{total_variance:+,.2f}")

    if flagged:
        print("\nFlagged positions — worth a look before they settle:")
        for p in flagged:
            direction = "loss" if p.variance_eur < 0 else "gain"
            print(
                f"  - {p.position_id} ({p.client}): {p.currency_pair} moved "
                f"{p.variance_pct:+.2f}% since booking — an unrealized {direction} "
                f"of €{abs(p.variance_eur):,.2f} if it settled today"
            )
    else:
        print("\nNothing past the threshold today.")


def main():
    parser = argparse.ArgumentParser(description="FX Monitoring Agent — flags open positions drifting past a rate threshold.")
    parser.add_argument("csv_path", nargs="?", default="data/fx_positions.csv", help="Path to the FX positions CSV")
    parser.add_argument("--threshold", type=float, default=2.0, help="Variance threshold in percent (default: 2.0)")
    args = parser.parse_args()

    try:
        positions = load_positions(args.csv_path)
    except FileNotFoundError:
        print(f"Could not find {args.csv_path}", file=sys.stderr)
        sys.exit(1)

    if not positions:
        print("No open positions found in the CSV.")
        return

    print_report(positions, args.threshold)


if __name__ == "__main__":
    main()
