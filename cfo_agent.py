"""
CFO Agent — Weekly Financial Report
=====================================
Post #2 of the CFO & AI Series by Boris Dračka
https://borisdracka.com/blog/post-02

Pipeline:
  1. Pull   — read financial data from CSV
  2. Clean  — validate and normalize
  3. KPIs   — calculate financial metrics
  4. Report — generate AI narrative (Gemini)
  5. Deliver — send by email

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

# ── Load environment variables ──────────────────────────────────────────
load_dotenv()

GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")
SENDER_EMAIL    = os.getenv("SENDER_EMAIL", "")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "")
COMPANY_NAME    = os.getenv("COMPANY_NAME", "Your Company")
DATA_FILE       = "data/financial_data.csv"


# ═══════════════════════════════════════════════════════════════
# STEP 1 — PULL DATA
# ═══════════════════════════════════════════════════════════════

def pull_data(filepath: str) -> dict:
    """
    Read financial data from CSV.
    Expected columns: line_item, this_month, last_month
    """
    print("[Step 1] Pulling data from:", filepath)
    data = {}

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Data file not found: {filepath}")

    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = row["line_item"].strip()
            data[key] = {
                "this_month": float(row["this_month"].strip().replace(",", "")),
                "last_month":  float(row["last_month"].strip().replace(",", "")),
            }

    print(f"  ✓ Loaded {len(data)} line items")
    return data


# ═══════════════════════════════════════════════════════════════
# STEP 2 — CLEAN & TRANSFORM
# ═══════════════════════════════════════════════════════════════

REQUIRED_ITEMS = [
    "Revenue",
    "COGS",
    "Operating Expenses",
    "Cash Balance",
    "Accounts Receivable",
]

def clean_data(data: dict) -> dict:
    """
    Validate required fields, ensure no negative values where unexpected.
    """
    print("[Step 2] Cleaning and validating data...")
    issues = []

    for item in REQUIRED_ITEMS:
        if item not in data:
            issues.append(f"Missing required line item: '{item}'")
        elif data[item]["this_month"] < 0:
            issues.append(f"Unexpected negative value for '{item}': {data[item]['this_month']}")

    if issues:
        print("  ⚠ Validation issues:")
        for issue in issues:
            print("    -", issue)
    else:
        print("  ✓ Data clean — no anomalies detected")

    return data


# ═══════════════════════════════════════════════════════════════
# STEP 3 — CALCULATE KPIs
# ═══════════════════════════════════════════════════════════════

def calculate_kpis(data: dict) -> dict:
    """
    Compute standard CFO metrics from the cleaned data.
    """
    print("[Step 3] Calculating KPIs...")

    rev_cur   = data["Revenue"]["this_month"]
    rev_prev  = data["Revenue"]["last_month"]
    cogs_cur  = data["COGS"]["this_month"]
    cogs_prev = data["COGS"]["last_month"]
    opex_cur  = data["Operating Expenses"]["this_month"]
    opex_prev = data["Operating Expenses"]["last_month"]
    cash_cur  = data["Cash Balance"]["this_month"]
    ar_cur    = data["Accounts Receivable"]["this_month"]
    ar_prev   = data["Accounts Receivable"]["last_month"]

    # Gross margin
    gross_profit_cur  = rev_cur  - cogs_cur
    gross_profit_prev = rev_prev - cogs_prev
    gross_margin_cur  = (gross_profit_cur  / rev_cur)  * 100 if rev_cur  > 0 else 0
    gross_margin_prev = (gross_profit_prev / rev_prev) * 100 if rev_prev > 0 else 0

    # Net income
    net_income_cur  = rev_cur  - cogs_cur  - opex_cur
    net_income_prev = rev_prev - cogs_prev - opex_prev

    # Burn rate & runway
    burn_rate = abs(net_income_cur) if net_income_cur < 0 else 0
    runway    = (cash_cur / burn_rate) if burn_rate > 0 else float("inf")

    # Revenue growth MoM
    rev_growth = ((rev_cur - rev_prev) / rev_prev * 100) if rev_prev > 0 else 0

    # DSO — Days Sales Outstanding (AR / Revenue * 30)
    dso = (ar_cur / rev_cur * 30) if rev_cur > 0 else 0

    # Operating leverage
    rev_change = (rev_cur - rev_prev) / rev_prev if rev_prev > 0 else 0
    ni_change  = (net_income_cur - net_income_prev) / abs(net_income_prev) if net_income_prev != 0 else 0
    op_leverage = ni_change / rev_change if rev_change != 0 else None

    kpis = {
        "gross_margin_cur":  gross_margin_cur,
        "gross_margin_prev": gross_margin_prev,
        "gross_profit_cur":  gross_profit_cur,
        "net_income_cur":    net_income_cur,
        "net_income_prev":   net_income_prev,
        "burn_rate":         burn_rate,
        "runway":            runway,
        "rev_growth":        rev_growth,
        "dso":               dso,
        "op_leverage":       op_leverage,
        "rev_cur":           rev_cur,
        "rev_prev":          rev_prev,
        "opex_cur":          opex_cur,
        "opex_prev":         opex_prev,
        "cash_cur":          cash_cur,
        "ar_cur":            ar_cur,
        "ar_prev":           ar_prev,
    }

    print(f"  Gross Margin:      {gross_margin_cur:.1f}% (prev: {gross_margin_prev:.1f}%)")
    print(f"  Net Income:        ${net_income_cur:,.0f}")
    print(f"  Burn Rate:         ${burn_rate:,.0f}/month")
    if runway != float("inf"):
        print(f"  Runway:            {runway:.1f} months")
    else:
        print("  Runway:            ∞ (profitable)")
    print(f"  Revenue Growth:    {rev_growth:+.1f}% MoM")
    print(f"  DSO:               {dso:.0f} days")
    if op_leverage:
        print(f"  Operating Lev.:    {op_leverage:.2f}x")
    print("  ✓ KPIs calculated")

    return kpis


# ═══════════════════════════════════════════════════════════════
# STEP 4 — GENERATE AI REPORT
# ═══════════════════════════════════════════════════════════════

def build_prompt(kpis: dict, company: str) -> str:
    runway_str = (
        f"{kpis['runway']:.1f} months"
        if kpis["runway"] != float("inf")
        else "positive cash flow (no burn)"
    )
    return f"""You are an experienced CFO writing a monthly financial commentary for the board of {company}.

Financial data for this month vs last month:
- Revenue: ${kpis['rev_cur']:,.0f} (vs ${kpis['rev_prev']:,.0f}, {kpis['rev_growth']:+.1f}% MoM)
- Gross Margin: {kpis['gross_margin_cur']:.1f}% (vs {kpis['gross_margin_prev']:.1f}% last month)
- Operating Expenses: ${kpis['opex_cur']:,.0f} (vs ${kpis['opex_prev']:,.0f})
- Net Income: ${kpis['net_income_cur']:,.0f} (vs ${kpis['net_income_prev']:,.0f})
- Monthly Burn Rate: {'$' + f"{kpis['burn_rate']:,.0f}" if kpis['burn_rate'] > 0 else '$0 (profitable)'}
- Cash Runway: {runway_str}
- Cash Balance: ${kpis['cash_cur']:,.0f}
- Days Sales Outstanding: {kpis['dso']:.0f} days
- Accounts Receivable: ${kpis['ar_cur']:,.0f} (vs ${kpis['ar_prev']:,.0f})

Write a professional CFO report with:
1. A 2-sentence executive summary of the month
2. What improved and what deteriorated (with specific numbers)
3. The 2 biggest financial risks to watch next month
4. One concrete action recommendation

Write in a confident, direct CFO voice. Use paragraphs, not bullet points.
Keep it under 350 words. Do not use markdown headers — write as flowing prose."""


def generate_report(kpis: dict, company: str) -> str:
    """
    Call Gemini API and return the generated CFO report text.
    """
    print("[Step 4] Generating AI report...")

    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set. Check your .env file.")

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")

    prompt = build_prompt(kpis, company)
    response = model.generate_content(prompt)
    report_text = response.text

    print("  ✓ Report generated ({} words)".format(len(report_text.split())))
    return report_text


# ═══════════════════════════════════════════════════════════════
# STEP 5 — DELIVER
# ═══════════════════════════════════════════════════════════════

def format_email_body(report_text: str, kpis: dict, company: str) -> str:
    date_str = datetime.date.today().strftime("%B %d, %Y")
    runway_str = (
        f"{kpis['runway']:.1f} months runway"
        if kpis["runway"] != float("inf")
        else "cash-flow positive"
    )
    sep = "─" * 44
    return f"""CFO Report — {company}
Generated: {date_str}

KEY METRICS
{sep}
Revenue:        ${kpis['rev_cur']:>12,.0f}  ({kpis['rev_growth']:+.1f}% MoM)
Gross Margin:   {kpis['gross_margin_cur']:>11.1f}%
Net Income:     ${kpis['net_income_cur']:>12,.0f}
Burn Rate:      ${kpis['burn_rate']:>12,.0f}/month
Runway:         {runway_str}
DSO:            {kpis['dso']:>11.0f} days
{sep}

AI NARRATIVE
{sep}
{report_text}
{sep}

Generated by CFO Agent · github.com/LuliBobo/cfo-agents
Built by Boris Dračka · borisdracka.com
"""


def deliver_report(report_text: str, kpis: dict, company: str) -> None:
    """
    Send the report by email. If credentials are missing, print to terminal.
    """
    print("[Step 5] Delivering report...")
    date_str = datetime.date.today().strftime("%B %Y")
    subject  = f"CFO Report — {company} — {date_str}"
    body     = format_email_body(report_text, kpis, company)

    if not SENDER_EMAIL or not SENDER_PASSWORD or not RECIPIENT_EMAIL:
        print("  ⚠ Email credentials not configured — printing to terminal.")
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
    print("\n" + "═" * 50)
    print("  CFO Agent — Weekly Report")
    print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("═" * 50 + "\n")

    data        = pull_data(DATA_FILE)
    data        = clean_data(data)
    kpis        = calculate_kpis(data)
    report_text = generate_report(kpis, COMPANY_NAME)
    deliver_report(report_text, kpis, COMPANY_NAME)

    print("\n✓ Agent completed successfully.")
    print("═" * 50 + "\n")


if __name__ == "__main__":
    main()
