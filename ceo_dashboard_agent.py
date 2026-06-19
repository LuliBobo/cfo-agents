"""
CEO Dashboard Agent — Real-Time Forward Cash Briefing
======================================================
Post #5 of the CFO & AI Series by Boris Dračka
https://borisdracka.com/blog/post-05

The problem this agent solves:
  CEO calls Friday at 4pm needing a forward cash projection.
  The accountant hasn't closed the month.
  Neither person is wrong — the system is wrong.

  This agent answers the CEO's 3 planning questions automatically,
  every Friday at 3:00 PM — before the call happens.

The 3 CEO questions (from Post #5 gap table):
  1. What is our current bank balance?
  2. What inflows are expected this week/next week?
  3. What outflows are scheduled? Will we have enough for payroll?

Pipeline:
  1. Pull      — read bank balance, AR (invoices due), AP (bills due), payroll schedule
  2. Assemble  — build a 7-day forward cash position view
  3. Analyze   — answer the 3 CEO questions with hard numbers
  4. Generate  — Gemini AI writes a concise CEO planning briefing
  5. Deliver   — email to CEO every Friday at 3:00 PM

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

GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "")
SENDER_EMAIL      = os.getenv("SENDER_EMAIL", "")
SENDER_PASSWORD   = os.getenv("SENDER_PASSWORD", "")
RECIPIENT_EMAIL   = os.getenv("RECIPIENT_EMAIL", "")
COMPANY_NAME      = os.getenv("COMPANY_NAME", "Your Company")
CURRENT_BALANCE   = float(os.getenv("CURRENT_BALANCE", "46400"))
PAYROLL_THRESHOLD = float(os.getenv("PAYROLL_THRESHOLD", "25000"))
CASHFLOW_FILE     = "data/cashflow_data.csv"   # reuse from Post #4 agent


# ═══════════════════════════════════════════════════════════════
# STEP 1 — PULL DATA
# ═══════════════════════════════════════════════════════════════

def pull_transactions(filepath: str) -> list[dict]:
    """
    Load upcoming transactions from CSV.
    Reuses the same cashflow_data.csv format from the Cash Flow Agent.
    """
    print("[Step 1] Pulling transaction data...")

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

    today  = datetime.date.today()
    future = [t for t in transactions if t["date"] >= today]
    future.sort(key=lambda x: x["date"])
    print(f"  ✓ {len(future)} upcoming transactions loaded")
    return future


# ═══════════════════════════════════════════════════════════════
# STEP 2 — ASSEMBLE 7-DAY FORWARD VIEW
# ═══════════════════════════════════════════════════════════════

def assemble_forward_view(transactions: list[dict], balance: float) -> dict:
    """
    Build a 7-day forward cash position view.
    Returns structured data answering the CEO's 3 planning questions.
    """
    print("[Step 2] Assembling 7-day forward cash view...")

    today       = datetime.date.today()
    week_end    = today + datetime.timedelta(days=7)
    week_txns   = [t for t in transactions if today <= t["date"] <= week_end]

    inflows     = [t for t in week_txns if t["amount_eur"] > 0]
    outflows    = [t for t in week_txns if t["amount_eur"] < 0]
    payroll     = [t for t in outflows if "payroll" in t["description"].lower()]

    total_in    = sum(t["amount_eur"] for t in inflows)
    total_out   = sum(abs(t["amount_eur"]) for t in outflows)
    projected   = balance + total_in - total_out
    payroll_amt = sum(abs(t["amount_eur"]) for t in payroll)

    # Day-by-day for the 7-day window
    days = []
    running = balance
    for offset in range(7):
        date     = today + datetime.timedelta(days=offset)
        day_txns = [t for t in week_txns if t["date"] == date]
        day_in   = sum(t["amount_eur"] for t in day_txns if t["amount_eur"] > 0)
        day_out  = sum(abs(t["amount_eur"]) for t in day_txns if t["amount_eur"] < 0)
        running += day_in - day_out
        days.append({"date": date, "inflows": day_in, "outflows": day_out, "balance": running})

    view = {
        "current_balance":  balance,
        "total_inflows":    total_in,
        "total_outflows":   total_out,
        "projected_eow":    projected,
        "payroll_amount":   payroll_amt,
        "payroll_covered":  projected >= payroll_amt,
        "inflow_items":     inflows,
        "outflow_items":    outflows,
        "days":             days,
        "window_start":     today,
        "window_end":       week_end,
    }

    print(f"  ✓ 7-day view assembled")
    return view


# ═══════════════════════════════════════════════════════════════
# STEP 3 — ANALYZE — ANSWER THE 3 CEO QUESTIONS
# ═══════════════════════════════════════════════════════════════

def analyze(view: dict) -> dict:
    """
    Answer the 3 CEO questions from Post #5 with hard numbers.
    Returns a structured analysis.
    """
    print("[Step 3] Analyzing CEO planning questions...")

    q1 = f"€{view['current_balance']:,.0f}"
    q2 = f"€{view['total_inflows']:,.0f} expected ({len(view['inflow_items'])} invoices)"
    q3_status = "✓ COVERED" if view["payroll_covered"] else "⚠ AT RISK"
    q3 = f"€{view['total_outflows']:,.0f} scheduled — Payroll €{view['payroll_amount']:,.0f} — {q3_status}"

    low_day   = min(view["days"], key=lambda d: d["balance"])
    risk_flag = low_day["balance"] < view["payroll_amount"]

    analysis = {
        "q1_current_balance": q1,
        "q2_expected_inflows": q2,
        "q3_outflows_status": q3,
        "projected_eow": f"€{view['projected_eow']:,.0f}",
        "lowest_day": low_day,
        "risk_flag": risk_flag,
        "payroll_covered": view["payroll_covered"],
    }

    print(f"  Q1: Current balance    → {q1}")
    print(f"  Q2: Expected inflows   → {q2}")
    print(f"  Q3: Outflows/payroll   → {q3}")
    return analysis


# ═══════════════════════════════════════════════════════════════
# STEP 4 — GENERATE CEO BRIEFING
# ═══════════════════════════════════════════════════════════════

def build_ceo_prompt(view: dict, analysis: dict, company: str) -> str:
    today_str = datetime.date.today().strftime("%A, %B %d, %Y")

    inflow_list = "\n".join(
        f"  - {t['description']}: +€{t['amount_eur']:,.0f} on {t['date'].strftime('%a %b %d')}"
        for t in view["inflow_items"]
    ) or "  None expected this week"

    outflow_list = "\n".join(
        f"  - {t['description']}: €{abs(t['amount_eur']):,.0f} on {t['date'].strftime('%a %b %d')}"
        for t in view["outflow_items"]
    ) or "  None scheduled this week"

    return f"""You are the CFO of {company}, preparing a Friday planning briefing for the CEO.
The CEO needs to know if there's enough financial capacity to make decisions next week.
This is NOT an accounting report. This is a planning answer.

Date: {today_str}
Current bank balance: €{view['current_balance']:,.0f}
Projected balance end of next week: €{view['projected_eow']:,.0f}

Expected inflows this week:
{inflow_list}

Scheduled outflows this week:
{outflow_list}

Payroll covered: {"YES" if view['payroll_covered'] else "NO — ACTION REQUIRED"}

Write a concise CEO planning briefing (max 160 words):
1. One-sentence status (can we make the hire / do we have runway?)
2. The 3 numbers the CEO needs: current balance, expected inflows, key outflows
3. The bottom line: what the projected position looks like end of next week
4. If payroll is at risk: say so directly and what needs to happen
5. One forward-looking observation for the board call

Write in direct, confident language. No jargon. No hedging. No markdown."""


def generate_briefing(view: dict, analysis: dict, company: str) -> str:
    print("[Step 4] Generating CEO planning briefing...")

    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY is not set.\n"
            "  → Get your free key at: https://aistudio.google.com/apikey\n"
            "  → Then add it to your .env file: GEMINI_API_KEY=your_key_here"
        )

    client   = genai.Client(api_key=GEMINI_API_KEY)
    prompt   = build_ceo_prompt(view, analysis, company)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    briefing = response.text.strip()
    print(f"  ✓ CEO briefing generated ({len(briefing.split())} words)")
    return briefing


# ═══════════════════════════════════════════════════════════════
# STEP 5 — DELIVER TO CEO
# ═══════════════════════════════════════════════════════════════

def format_report(view: dict, analysis: dict, briefing: str, company: str) -> str:
    today_str = datetime.date.today().strftime("%B %d, %Y")
    sep       = "─" * 52
    status    = "⚠ PAYROLL AT RISK" if not view["payroll_covered"] else "✓ POSITION HEALTHY"

    lines = [
        f"CEO Cash Briefing — {company}",
        f"Date: {today_str}  |  Status: {status}",
        "",
        f"THE 3 NUMBERS YOU NEED",
        sep,
        f"Q1. Current balance:       {analysis['q1_current_balance']}",
        f"Q2. Expected inflows:      {analysis['q2_expected_inflows']}",
        f"Q3. Outflows/payroll:      {analysis['q3_outflows_status']}",
        f"    Projected end of week: {analysis['projected_eow']}",
        sep,
        "",
        f"7-DAY DETAIL",
        sep,
    ]

    for day in view["days"]:
        marker = "⚠" if day["balance"] < PAYROLL_THRESHOLD else " "
        lines.append(
            f"{marker} {day['date'].strftime('%a %b %d')}  "
            f"In: €{day['inflows']:>8,.0f}  "
            f"Out: €{day['outflows']:>8,.0f}  "
            f"Balance: €{day['balance']:>10,.0f}"
        )

    lines += [sep, "", f"CEO BRIEFING", sep, briefing, sep, ""]
    lines += [
        f"Generated by CEO Dashboard Agent · github.com/LuliBobo/cfo-agents",
        f"Built by Boris Dračka · borisdracka.com",
    ]
    return "\n".join(lines)


def deliver(view: dict, analysis: dict, briefing: str, company: str) -> None:
    print("[Step 5] Delivering CEO briefing...")
    today_str  = datetime.date.today().strftime("%B %d, %Y")
    status_str = "⚠ PAYROLL AT RISK" if not view["payroll_covered"] else "✓ All Clear"
    subject    = f"CEO Cash Briefing — {company} — {today_str} — {status_str}"
    body       = format_report(view, analysis, briefing, company)

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

        print(f"  ✓ CEO briefing sent to {RECIPIENT_EMAIL}")
    except Exception as e:
        print(f"  ✗ Email failed: {e}")
        print("  Printing to terminal instead.\n")
        print(body)


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    print("\n" + "═" * 52)
    print("  CEO Dashboard Agent — Weekly Planning Briefing")
    print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("═" * 52 + "\n")

    transactions = pull_transactions(CASHFLOW_FILE)
    view         = assemble_forward_view(transactions, CURRENT_BALANCE)
    analysis     = analyze(view)
    briefing     = generate_briefing(view, analysis, COMPANY_NAME)
    deliver(view, analysis, briefing, COMPANY_NAME)

    print("\n✓ Agent completed successfully.")
    print("═" * 52 + "\n")


if __name__ == "__main__":
    main()
