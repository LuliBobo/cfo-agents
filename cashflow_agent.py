"""
Cash Flow Alert Agent — Daily Cash Position Monitor
====================================================
Post #4 of the CFO & AI Series by Boris Dračka
https://borisdracka.com/blog/post-04

The problem this agent solves:
  A company with €2M revenue can look healthy on Monday and miss payroll
  on Friday — because nobody was watching the daily cash position.
  This agent watches it every morning so you don't have to.

Pipeline:
  1. Pull      — read current bank balance + scheduled transactions from CSV
  2. Project   — build a 14-day cash flow projection day by day
  3. Detect    — flag any day where projected balance drops below threshold
  4. Generate  — Gemini AI writes a clear daily cash briefing with alerts
  5. Deliver   — send to CEO/CFO by email every morning at 7:00 AM

Setup: see README.md
"""

import os
import csv
import smtplib
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

try:
    from google import genai
except ImportError:
    print("ERROR: google-genai not installed. Run: pip3 install -r requirements.txt")
    exit(1)

# ── Load environment variables ──────────────────────────────────
load_dotenv()

GEMINI_API_KEY      = os.getenv("GEMINI_API_KEY", "")
SENDER_EMAIL        = os.getenv("SENDER_EMAIL", "")
SENDER_PASSWORD     = os.getenv("SENDER_PASSWORD", "")
RECIPIENT_EMAIL     = os.getenv("RECIPIENT_EMAIL", "")
COMPANY_NAME        = os.getenv("COMPANY_NAME", "Your Company")
CURRENT_BALANCE     = float(os.getenv("CURRENT_BALANCE", "62400"))   # today's bank balance
ALERT_THRESHOLD     = float(os.getenv("ALERT_THRESHOLD", "20000"))   # warn if projected below this
CASHFLOW_FILE       = "data/cashflow_data.csv"
PROJECTION_DAYS     = 14


# ═══════════════════════════════════════════════════════════════
# STEP 1 — PULL DATA
# ═══════════════════════════════════════════════════════════════

def pull_transactions(filepath: str) -> list[dict]:
    """
    Load scheduled inflows and outflows from CSV.
    Expected columns: date, description, amount_eur, type (inflow/outflow)
    """
    print("[Step 1] Pulling transaction data from:", filepath)

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Cash flow file not found: {filepath}")

    transactions = []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            transactions.append({
                "date":        datetime.date.fromisoformat(row["date"].strip()),
                "description": row["description"].strip(),
                "amount_eur":  float(row["amount_eur"].strip().replace(",", "")),
                "type":        row["type"].strip().lower(),
            })

    # Only keep future transactions
    today  = datetime.date.today()
    future = [t for t in transactions if t["date"] >= today]
    future.sort(key=lambda x: x["date"])

    print(f"  ✓ Loaded {len(future)} upcoming transactions")
    return future


# ═══════════════════════════════════════════════════════════════
# STEP 2 — BUILD 14-DAY PROJECTION
# ═══════════════════════════════════════════════════════════════

def build_projection(transactions: list[dict], opening_balance: float) -> list[dict]:
    """
    Calculate projected daily closing balance for the next PROJECTION_DAYS days.
    Returns a list of daily snapshots.
    """
    print("[Step 2] Building cash flow projection...")
    today      = datetime.date.today()
    projection = []
    balance    = opening_balance

    for day_offset in range(PROJECTION_DAYS):
        date      = today + datetime.timedelta(days=day_offset)
        day_txns  = [t for t in transactions if t["date"] == date]
        day_in    = sum(t["amount_eur"] for t in day_txns if t["amount_eur"] > 0)
        day_out   = sum(abs(t["amount_eur"]) for t in day_txns if t["amount_eur"] < 0)
        balance  += day_in - day_out

        projection.append({
            "date":          date,
            "inflows":       day_in,
            "outflows":      day_out,
            "closing":       balance,
            "transactions":  day_txns,
        })

    print(f"  ✓ Projection built for {PROJECTION_DAYS} days")
    return projection


# ═══════════════════════════════════════════════════════════════
# STEP 3 — DETECT ALERTS
# ═══════════════════════════════════════════════════════════════

def detect_alerts(projection: list[dict], threshold: float) -> list[dict]:
    """
    Flag any day where projected balance drops below the alert threshold.
    Also flag the lowest balance day and any negative balance days.
    """
    print("[Step 3] Scanning for cash alerts...")
    alerts = []

    for day in projection:
        if day["closing"] < 0:
            alerts.append({
                "date":    day["date"],
                "balance": day["closing"],
                "level":   "CRITICAL",
                "message": f"Projected NEGATIVE balance: €{day['closing']:,.0f}",
            })
        elif day["closing"] < threshold:
            alerts.append({
                "date":    day["date"],
                "balance": day["closing"],
                "level":   "WARNING",
                "message": f"Projected balance €{day['closing']:,.0f} — below threshold €{threshold:,.0f}",
            })

    if alerts:
        print(f"  ⚠ {len(alerts)} alert(s) detected:")
        for a in alerts:
            print(f"    [{a['level']}] {a['date']} — {a['message']}")
    else:
        print("  ✓ No alerts — cash position healthy for next 14 days")

    return alerts


# ═══════════════════════════════════════════════════════════════
# STEP 4 — GENERATE AI BRIEFING
# ═══════════════════════════════════════════════════════════════

def build_briefing_prompt(projection: list[dict], alerts: list[dict],
                           opening: float, company: str) -> str:
    today_str    = datetime.date.today().strftime("%B %d, %Y")
    low_balance  = min(d["closing"] for d in projection)
    low_date     = next(d["date"] for d in projection if d["closing"] == low_balance)
    end_balance  = projection[-1]["closing"]
    total_in     = sum(d["inflows"] for d in projection)
    total_out    = sum(d["outflows"] for d in projection)

    alert_text = ""
    if alerts:
        alert_text = "\n⚠ ALERTS:\n" + "\n".join(
            f"  - {a['date'].strftime('%a %b %d')}: [{a['level']}] {a['message']}"
            for a in alerts
        )
    else:
        alert_text = "\n✓ No alerts — cash position healthy for the full projection window."

    return f"""You are the CFO of {company}, writing a daily cash flow briefing for the CEO.

Date: {today_str}
Current bank balance: €{opening:,.0f}
14-day projection window:
  - Total expected inflows: €{total_in:,.0f}
  - Total expected outflows: €{total_out:,.0f}
  - Lowest projected balance: €{low_balance:,.0f} on {low_date.strftime('%A, %B %d')}
  - Balance at end of window: €{end_balance:,.0f}
{alert_text}

Write a short, direct daily cash briefing (max 180 words) with:
1. One-sentence status summary (healthy / warning / critical)
2. The key cash movements this week to be aware of
3. If there are alerts: what action is needed and by when
4. If no alerts: one forward-looking observation about the cash position

Write in a confident, direct CFO voice. No markdown. Use plain paragraphs."""


def generate_briefing(projection: list[dict], alerts: list[dict],
                       opening: float, company: str) -> str:
    print("[Step 4] Generating AI cash briefing...")

    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY is not set.\n"
            "  → Get your free key at: https://aistudio.google.com/apikey\n"
            "  → Then add it to your .env file: GEMINI_API_KEY=your_key_here"
        )

    client   = genai.Client(api_key=GEMINI_API_KEY)
    prompt   = build_briefing_prompt(projection, alerts, opening, company)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    briefing = response.text.strip()
    print(f"  ✓ Briefing generated ({len(briefing.split())} words)")
    return briefing


# ═══════════════════════════════════════════════════════════════
# STEP 5 — DELIVER
# ═══════════════════════════════════════════════════════════════

def format_report(projection: list[dict], alerts: list[dict],
                  briefing: str, opening: float, company: str) -> str:
    today_str = datetime.date.today().strftime("%B %d, %Y")
    sep       = "─" * 52
    status    = "⚠ ACTION REQUIRED" if alerts else "✓ ALL CLEAR"

    lines = [
        f"Daily Cash Briefing — {company}",
        f"Date: {today_str}  |  Status: {status}",
        "",
        f"CURRENT POSITION",
        sep,
        f"Bank balance today:    €{opening:,.0f}",
        f"Alert threshold:       €{ALERT_THRESHOLD:,.0f}",
        sep,
        "",
    ]

    if alerts:
        lines += [f"ALERTS ({len(alerts)} item(s))", sep]
        for a in alerts:
            lines.append(f"  [{a['level']}] {a['date'].strftime('%a %b %d')} — {a['message']}")
        lines += [sep, ""]

    lines += [f"14-DAY PROJECTION", sep]
    for day in projection:
        has_txns  = bool(day["transactions"])
        marker    = "⚠" if day["closing"] < ALERT_THRESHOLD else " "
        lines.append(
            f"{marker} {day['date'].strftime('%a %b %d')}  "
            f"In: €{day['inflows']:>8,.0f}  "
            f"Out: €{day['outflows']:>8,.0f}  "
            f"Balance: €{day['closing']:>10,.0f}"
        )
        for t in day["transactions"]:
            sign = "+" if t["amount_eur"] > 0 else ""
            lines.append(f"    → {t['description']}: {sign}€{t['amount_eur']:,.0f}")
    lines += [sep, ""]

    lines += [f"AI BRIEFING", sep, briefing, sep, ""]
    lines += [
        f"Generated by Cash Flow Agent · github.com/LuliBobo/cfo-agents",
        f"Built by Boris Dračka · borisdracka.com",
    ]

    return "\n".join(lines)


def deliver_report(projection: list[dict], alerts: list[dict],
                   briefing: str, opening: float, company: str) -> None:
    print("[Step 5] Delivering daily briefing...")
    today_str  = datetime.date.today().strftime("%B %d, %Y")
    status_str = "⚠ ACTION REQUIRED" if alerts else "✓ All Clear"
    subject    = f"Cash Briefing — {company} — {today_str} — {status_str}"
    body       = format_report(projection, alerts, briefing, opening, company)

    if not SENDER_EMAIL or not SENDER_PASSWORD or not RECIPIENT_EMAIL:
        print("  ⚠ Email not configured — printing to terminal.")
        print("\n" + "═" * 60)
        print(body)
        print("═" * 60)
        return

    try:
        msg = MIMEMultipart()
        msg["From"]    = SENDER_EMAIL
        msg["To"]      = RECIPIENT_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())

        print(f"  ✓ Briefing sent to {RECIPIENT_EMAIL}")
    except Exception as e:
        print(f"  ✗ Email failed: {e}")
        print("  Printing to terminal instead.\n")
        print(body)


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    print("\n" + "═" * 52)
    print("  Cash Flow Agent — Daily Monitor")
    print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("═" * 52 + "\n")

    transactions = pull_transactions(CASHFLOW_FILE)
    projection   = build_projection(transactions, CURRENT_BALANCE)
    alerts       = detect_alerts(projection, ALERT_THRESHOLD)
    briefing     = generate_briefing(projection, alerts, CURRENT_BALANCE, COMPANY_NAME)
    deliver_report(projection, alerts, briefing, CURRENT_BALANCE, COMPANY_NAME)

    print("\n✓ Agent completed successfully.")
    print("═" * 52 + "\n")


if __name__ == "__main__":
    main()
