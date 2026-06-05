"""
Invoice Agent — Overdue AR Monitor & Alert
==========================================
Post #3 of the CFO & AI Series by Boris Dračka
https://borisdracka.com/blog/post-03

This agent automates the single biggest time sink for a solo accountant:
chasing overdue invoices. It runs every Monday, identifies overdue AR,
generates personalized AI reminders for each client, and delivers a
summary report to the accountant — with draft emails ready to send.

Pipeline:
  1. Pull      — read invoice data from CSV
  2. Detect    — identify overdue invoices and classify severity
  3. Prioritize — rank by financial risk (amount × days overdue)
  4. Generate  — Gemini AI writes a personalized reminder for each client
  5. Deliver   — send summary + drafts to the accountant by email

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
    import google.generativeai as genai
except ImportError:
    print("ERROR: google-generativeai not installed. Run: pip install -r requirements.txt")
    exit(1)

# ── Load environment variables ──────────────────────────────────
load_dotenv()

GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")
SENDER_EMAIL    = os.getenv("SENDER_EMAIL", "")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "")
COMPANY_NAME    = os.getenv("COMPANY_NAME", "Your Company")
INVOICE_FILE    = "data/invoices.csv"

# Severity thresholds (days overdue)
CRITICAL_DAYS = 60
WARNING_DAYS  = 30


# ═══════════════════════════════════════════════════════════════
# STEP 1 — PULL DATA
# ═══════════════════════════════════════════════════════════════

def pull_invoices(filepath: str) -> list[dict]:
    """
    Load invoices from CSV.
    Expected columns: invoice_id, client, amount_eur, due_date,
                      contact_email, status
    """
    print("[Step 1] Pulling invoice data from:", filepath)

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Invoice file not found: {filepath}")

    invoices = []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            invoices.append({
                "invoice_id":    row["invoice_id"].strip(),
                "client":        row["client"].strip(),
                "amount_eur":    float(row["amount_eur"].strip().replace(",", "")),
                "due_date":      datetime.date.fromisoformat(row["due_date"].strip()),
                "contact_email": row["contact_email"].strip(),
                "status":        row["status"].strip().lower(),
            })

    print(f"  ✓ Loaded {len(invoices)} invoices")
    return invoices


# ═══════════════════════════════════════════════════════════════
# STEP 2 — DETECT OVERDUE INVOICES
# ═══════════════════════════════════════════════════════════════

def detect_overdue(invoices: list[dict]) -> list[dict]:
    """
    Find all unpaid invoices past their due date.
    Adds: days_overdue, severity ('critical' / 'warning' / 'watch')
    """
    print("[Step 2] Detecting overdue invoices...")
    today    = datetime.date.today()
    overdue  = []

    for inv in invoices:
        if inv["status"] == "paid":
            continue
        days = (today - inv["due_date"]).days
        if days <= 0:
            continue  # not yet overdue

        if days >= CRITICAL_DAYS:
            severity = "critical"
        elif days >= WARNING_DAYS:
            severity = "warning"
        else:
            severity = "watch"

        overdue.append({**inv, "days_overdue": days, "severity": severity})

    print(f"  ✓ Found {len(overdue)} overdue invoices")
    for inv in overdue:
        print(f"    [{inv['severity'].upper():8}] {inv['invoice_id']} — "
              f"{inv['client']} — €{inv['amount_eur']:,.0f} — "
              f"{inv['days_overdue']}d overdue")
    return overdue


# ═══════════════════════════════════════════════════════════════
# STEP 3 — PRIORITIZE BY RISK
# ═══════════════════════════════════════════════════════════════

def prioritize(overdue: list[dict]) -> list[dict]:
    """
    Rank overdue invoices by financial risk score.
    Score = amount × days_overdue  (larger amount + longer delay = higher priority)
    """
    print("[Step 3] Prioritizing by financial risk...")

    for inv in overdue:
        inv["risk_score"] = inv["amount_eur"] * inv["days_overdue"]

    ranked = sorted(overdue, key=lambda x: x["risk_score"], reverse=True)

    print("  ✓ Priority ranking:")
    for i, inv in enumerate(ranked, 1):
        print(f"    #{i} {inv['client']} — risk score: {inv['risk_score']:,.0f}")

    return ranked


# ═══════════════════════════════════════════════════════════════
# STEP 4 — GENERATE AI REMINDER EMAILS
# ═══════════════════════════════════════════════════════════════

def build_reminder_prompt(inv: dict, company: str) -> str:
    tone = {
        "critical": "firm and urgent, making clear this requires immediate resolution",
        "warning":  "professional but direct, expressing concern about the delay",
        "watch":    "polite and friendly, as a gentle first reminder",
    }[inv["severity"]]

    return f"""You are the finance manager of {company}.

Write a professional payment reminder email for the following overdue invoice:
- Invoice number: {inv['invoice_id']}
- Client: {inv['client']}
- Amount: €{inv['amount_eur']:,.2f}
- Original due date: {inv['due_date'].strftime('%B %d, %Y')}
- Days overdue: {inv['days_overdue']} days
- Severity: {inv['severity'].upper()}

The tone should be {tone}.

Write ONLY the email body (no subject line). Include:
1. A brief, polite opening acknowledging the invoice
2. The specific amount and due date
3. A clear request for payment or a response with a payment date
4. Contact information placeholder: [YOUR PHONE / EMAIL]

Keep it under 150 words. Write in English. Do not use markdown formatting."""


def generate_reminders(overdue: list[dict], company: str) -> list[dict]:
    """
    Use Gemini to write a personalized reminder email for each overdue invoice.
    """
    print("[Step 4] Generating AI reminder emails...")

    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set. Check your .env file.")

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")

    for inv in overdue:
        prompt   = build_reminder_prompt(inv, company)
        response = model.generate_content(prompt)
        inv["reminder_email"] = response.text.strip()
        inv["email_subject"]  = (
            f"Payment Reminder — {inv['invoice_id']} — "
            f"€{inv['amount_eur']:,.0f} — {inv['days_overdue']} Days Overdue"
        )
        print(f"  ✓ Generated reminder for {inv['client']}")

    return overdue


# ═══════════════════════════════════════════════════════════════
# STEP 5 — DELIVER SUMMARY TO ACCOUNTANT
# ═══════════════════════════════════════════════════════════════

def format_summary(overdue: list[dict], company: str) -> str:
    today    = datetime.date.today().strftime("%B %d, %Y")
    sep      = "─" * 52
    total_at_risk = sum(inv["amount_eur"] for inv in overdue)

    lines = [
        f"Overdue Invoice Report — {company}",
        f"Generated: {today}",
        "",
        f"SUMMARY",
        sep,
        f"Total overdue invoices:  {len(overdue)}",
        f"Total amount at risk:    €{total_at_risk:,.0f}",
        f"Critical (60d+):         {sum(1 for i in overdue if i['severity']=='critical')}",
        f"Warning  (30-60d):       {sum(1 for i in overdue if i['severity']=='warning')}",
        f"Watch    (<30d):         {sum(1 for i in overdue if i['severity']=='watch')}",
        sep,
        "",
    ]

    for i, inv in enumerate(overdue, 1):
        lines += [
            f"#{i} — {inv['invoice_id']} | {inv['client']}",
            f"    Amount:    €{inv['amount_eur']:,.0f}",
            f"    Due:       {inv['due_date'].strftime('%B %d, %Y')}",
            f"    Overdue:   {inv['days_overdue']} days [{inv['severity'].upper()}]",
            f"    Contact:   {inv['contact_email']}",
            "",
            f"    DRAFT REMINDER EMAIL",
            f"    Subject: {inv['email_subject']}",
            sep,
            inv["reminder_email"],
            sep,
            "",
        ]

    lines += [
        "Generated by Invoice Agent · github.com/LuliBobo/cfo-agents",
        f"Built by Boris Dračka · borisdracka.com",
    ]

    return "\n".join(lines)


def deliver_report(overdue: list[dict], company: str) -> None:
    """
    Email the overdue summary + AI drafts to the accountant.
    Falls back to terminal print if email is not configured.
    """
    print("[Step 5] Delivering report...")
    date_str = datetime.date.today().strftime("%B %Y")
    subject  = f"⚠️ Overdue Invoices — {company} — {date_str} — Action Required"
    body     = format_summary(overdue, company)

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

        print(f"  ✓ Report sent to {RECIPIENT_EMAIL}")

    except Exception as e:
        print(f"  ✗ Email failed: {e}")
        print("  Printing to terminal instead.\n")
        print(body)


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    print("\n" + "═" * 52)
    print("  Invoice Agent — Overdue AR Monitor")
    print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("═" * 52 + "\n")

    invoices = pull_invoices(INVOICE_FILE)
    overdue  = detect_overdue(invoices)

    if not overdue:
        print("\n✓ No overdue invoices found. All clear!")
        print("═" * 52 + "\n")
        return

    ranked  = prioritize(overdue)
    ranked  = generate_reminders(ranked, COMPANY_NAME)
    deliver_report(ranked, COMPANY_NAME)

    print("\n✓ Agent completed successfully.")
    print("═" * 52 + "\n")


if __name__ == "__main__":
    main()
