# CFO Agents

AI agents for financial reporting and analysis. Tested as part of the [CFO Unfiltered](https://borisdracka.com) blog series by Boris Dračka.

---

## Agent 01 — Weekly CFO Report

This agent runs every Monday at 7:00 AM, pulls financial data, calculates KPIs, generates an AI narrative report using Google Gemini, and delivers it by email.

**From Post #2:** [An AI CFO Agent Is Not a Chatbot. Here's What It Actually Is.](https://borisdracka.com/blog/post-02)

### What it does

| Step | Action |
|------|--------|
| 1 | **Pull** — reads financial data from a CSV file |
| 2 | **Clean** — validates and normalizes entries |
| 3 | **Calculate KPIs** — gross margin, burn rate, DSO, operating leverage, revenue growth |
| 4 | **Generate report** — Gemini AI writes a CFO-grade narrative |
| 5 | **Deliver** — sends the report by email |

---

## Agent 02 — Invoice Agent

Reads a CSV of invoices, identifies which ones are overdue, ranks them by financial risk (amount × days overdue), and drafts a personalized reminder email per client — ready to review and send. It doesn't send anything on its own.

**From Post #3:** [50 People. €15M Revenue. 1 Accountant. This Is Normal.](https://borisdracka.com/blog/post-03)

### Quick start

```bash
git clone https://github.com/LuliBobo/cfo-agents.git
cd cfo-agents
python invoice_agent.py
```

Uses the same `.env` setup as Agent 01. Edit `data/invoices.csv` with your own invoices (or keep the sample data to test first).

### What it does

| Step | Action |
|------|--------|
| 1 | **Pull** — reads invoice data from a CSV |
| 2 | **Detect** — identifies overdue invoices and classifies severity |
| 3 | **Prioritize** — ranks by financial risk (amount × days overdue) |
| 4 | **Generate** — Gemini AI drafts a personalized reminder per client |
| 5 | **Deliver** — sends a summary report plus draft reminders to the accountant by email |

This is a personal, non-commercial prototype — not connected to, and not built for, any company or client. It's an experiment in what routine AR chasing would actually need to automate, nothing more.

---

## Agent 03 — FX Monitoring Agent

Reads a CSV of open FX-exposed positions (invoices billed in a foreign currency, still unpaid), compares each one's booked exchange rate against a current rate, and flags anything that has drifted past a configurable threshold — instead of waiting for month-end close to find out. No API keys, no scheduling, no infrastructure: it's a single script you run against a CSV.

**From Post #9:** [The FX Loss Nobody Sees Until Month-End](https://borisdracka.com/blog/post-09)

### Quick start

```bash
git clone https://github.com/LuliBobo/cfo-agents.git
cd cfo-agents
python fx_monitor_agent.py data/fx_positions.csv --threshold 2.0
```

Edit `data/fx_positions.csv` with your own open positions (or keep the sample data to test first). `--threshold` is the variance in percent past which a position gets flagged (default: 2.0).

### What it does

| Step | Action |
|------|--------|
| 1 | **Load** — reads open FX positions from a CSV |
| 2 | **Compare** — booked rate vs. a current rate you supply, per position |
| 3 | **Flag** — anything past the variance threshold |
| 4 | **Report** — prints a summary table plus net unrealized FX variance across all open positions |

This is a personal, non-commercial prototype — not connected to, and not built for, any company or client. It's an experiment in what a daily FX check would actually need to compute, nothing more.

---

## Agent 04 — Idle Cash Agent

Reads a CSV of account balances, compares each one against its agreed operating buffer, and estimates what the excess sitting above that buffer could have earned if it had been swept somewhere that pays interest — instead of finding out at month-end close, if at all. Read-only by design: it only reads and reports, it never moves money or connects to a bank.

**From Post #10:** [The Cash That Just Sits There](https://borisdracka.com/blog/post-10)

### Quick start

```bash
git clone https://github.com/LuliBobo/cfo-agents.git
cd cfo-agents
python idle_cash_agent.py data/account_balances.csv --threshold 50000 --rate 3.0
```

Edit `data/account_balances.csv` with your own accounts (or keep the sample data to test first). `--threshold` is the excess-above-buffer amount in EUR past which an account gets flagged (default: 50000); `--rate` is the default alternative annual rate in percent used when a row doesn't specify its own (default: 3.0).

### What it does

| Step | Action |
|------|--------|
| 1 | **Load** — reads account balances from a CSV |
| 2 | **Compare** — balance vs. its configured buffer, per account |
| 3 | **Flag** — anything with more than the threshold sitting idle above buffer |
| 4 | **Estimate** — multiplies the flagged excess by the alternative rate |
| 5 | **Report** — prints the flagged accounts plus the estimated annual and monthly forgone interest |

This is a personal, non-commercial prototype — not connected to, and not built for, any company or client. It's an experiment in what a routine balance-vs-buffer check would actually need to compute, nothing more.

---

## Agent 05 — Invoice Priority Agent

Reads a CSV of open invoices and prints a suggested payment order that isn't just sorted by due date. A critical-vendor flag can move an invoice ahead of an older one; a discount-window field is tracked and displayed alongside it, though this version doesn't yet factor it into the rank — see the code comments.

**From Post #11:** [The Invoice That Gets Paid First Isn't the One That's Due First](https://borisdracka.com/blog/post-11)

### Quick start

```bash
git clone https://github.com/LuliBobo/cfo-agents.git
cd cfo-agents
python invoice_priority_agent.py data/open_invoices.csv
```

Edit `data/open_invoices.csv` with your own open invoices (or keep the sample data to test first).

### What it does

| Step | Action |
|------|--------|
| 1 | **Load** — reads open invoices from a CSV |
| 2 | **Calculate** — days remaining to each invoice's due date |
| 3 | **Check** — discount window and critical-vendor flags per invoice |
| 4 | **Re-rank** — critical-vendor invoices move to the front, in their own due-date order; everyone else keeps due-date order behind them |
| 5 | **Report** — prints the suggested payment order and flags which invoices moved |

This is a personal, non-commercial prototype — not connected to, and not built for, any company or client. It's an experiment in what a payment-priority check would actually need to compute, nothing more.

---

## Agent 06 — Collections Priority Agent

Reads a CSV of open receivables and prints a suggested collections order that isn't just sorted by days overdue. An active credit hold moves a receivable ahead of an older one; reminder history is tracked and displayed, and only changes the rank if you set a threshold. It only reports — it never sends a reminder.

**From Post #12:** [The Collection Reminder That Works Isn't the First One You Send](https://borisdracka.com/blog/post-12)

### Quick start

```bash
git clone https://github.com/LuliBobo/cfo-agents.git
cd cfo-agents
python collections_priority_agent.py data/open_receivables.csv
```

Edit `data/open_receivables.csv` with your own open receivables (or keep the sample data to test first). Optional flags: `--hold-values` (which `credit_hold` values count as an active hold) and `--reminder-threshold N` (also move receivables with N or more reminders sent to the front).

### What it does

| Step | Action |
|------|--------|
| 1 | **Load** — reads open receivables from a CSV |
| 2 | **Rank** — by days overdue |
| 3 | **Check** — credit-hold flag and reminder count per receivable |
| 4 | **Re-rank** — held receivables move to the front, in their own overdue order; everyone else keeps overdue order behind them |
| 5 | **Report** — prints the suggested collections order and flags which receivables moved |

This is a personal, non-commercial prototype — not connected to, and not built for, any company or client. It's an experiment in what a collections-priority check would actually need to compute, nothing more.

---

## Setup (30 minutes)

### Step 1 — Clone the repo

```bash
git clone https://github.com/LuliBobo/cfo-agents.git
cd cfo-agents
```

### Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 3 — Configure your environment

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```
GEMINI_API_KEY=your_key_from_aistudio.google.com
SENDER_EMAIL=your@gmail.com
SENDER_PASSWORD=your_gmail_app_password
RECIPIENT_EMAIL=ceo@yourcompany.com
COMPANY_NAME=Acme SaaS Ltd.
```

**Get your free Gemini API key:** [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

**Gmail App Password guide:** [support.google.com/accounts/answer/185833](https://support.google.com/accounts/answer/185833)

### Step 4 — Add your financial data

Edit `data/financial_data.csv` with your actual numbers (or keep the sample data to test first).

```csv
line_item,this_month,last_month
Revenue,285000,260000
COGS,97000,90000
Operating Expenses,148000,155000
Cash Balance,1240000,1180000
Accounts Receivable,68000,72000
```

### Step 5 — Run it manually first

```bash
python cfo_agent.py
```

You should see KPIs printed in the terminal and receive the report by email.
If email is not configured, the report prints to the terminal — that's fine for testing.

### Step 6 — Automate with GitHub Actions

1. Go to your GitHub repo → **Settings → Secrets and variables → Actions**
2. Add these repository secrets:

| Secret name | Value |
|-------------|-------|
| `GEMINI_API_KEY` | Your Gemini API key |
| `SENDER_EMAIL` | Your Gmail address |
| `SENDER_PASSWORD` | Your Gmail App Password |
| `RECIPIENT_EMAIL` | Who receives the report |
| `COMPANY_NAME` | Your company name |

3. The workflow in `.github/workflows/weekly_report.yml` fires every Monday at 7:00 AM UTC automatically.
4. You can also trigger it manually: **Actions tab → Weekly CFO Report → Run workflow**

---

## File structure

```
cfo-agents/
├── cfo_agent.py                      # Main agent script (Post #2)
├── invoice_agent.py                  # Invoice/AR agent script (Post #3)
├── fx_monitor_agent.py               # FX monitoring agent script (Post #9)
├── idle_cash_agent.py                # Idle cash agent script (Post #10)
├── invoice_priority_agent.py         # Invoice priority agent script (Post #11)
├── requirements.txt                  # Python dependencies
├── .env.example                      # Environment variable template
├── .gitignore
├── data/
│   ├── financial_data.csv            # Monthly P&L data (Agent 01)
│   ├── invoices.csv                  # Sample invoices (Agent 02)
│   ├── fx_positions.csv              # Sample open FX positions (Agent 03)
│   ├── account_balances.csv          # Sample account balances (Agent 04)
│   ├── open_invoices.csv             # Sample open invoices (Agent 05)
│   └── open_receivables.csv          # Sample open receivables (Agent 06)
└── .github/
    └── workflows/
        └── weekly_report.yml         # Weekly automation schedule
```

---

## Follow the series

- Post #2: [An AI CFO Agent Is Not a Chatbot](https://borisdracka.com/blog/post-02)
- Interactive walkthrough: [borisdracka.com/blog/post-02-demo](https://borisdracka.com/blog/post-02-demo)
- Post #3: [50 People. €15M Revenue. 1 Accountant. This Is Normal.](https://borisdracka.com/blog/post-03)
- Interactive walkthrough: [borisdracka.com/blog/post-03-demo](https://borisdracka.com/blog/post-03-demo)
- Interactive walkthrough: [borisdracka.com/blog/post-02-demo](https://borisdracka.com/blog/post-02-demo)
- Post #9: [The FX Loss Nobody Sees Until Month-End](https://borisdracka.com/blog/post-09)
- Interactive walkthrough: [borisdracka.com/blog/post-09-demo](https://borisdracka.com/blog/post-09-demo)
- Post #10: [The Cash That Just Sits There](https://borisdracka.com/blog/post-10)
- Interactive walkthrough: [borisdracka.com/blog/post-10-demo](https://borisdracka.com/blog/post-10-demo)
- Post #11: [The Invoice That Gets Paid First Isn't the One That's Due First](https://borisdracka.com/blog/post-11)
- Interactive walkthrough: [borisdracka.com/blog/post-11-demo](https://borisdracka.com/blog/post-11-demo)
- Newsletter: [borisdracka.beehiiv.com](https://borisdracka.beehiiv.com/subscribe)
- X.com: [@BorisDracka](https://x.com/BorisDracka)

---

© 2026 Boris Dračka · [borisdracka.com](https://borisdracka.com)
