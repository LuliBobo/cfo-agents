# CFO Agents

AI agents for financial reporting and analysis. Built as part of the [CFO Unfiltered](https://borisdracka.com) blog series by Boris Dračka.

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
├── cfo_agent.py                      # Main agent script
├── requirements.txt                  # Python dependencies
├── .env.example                      # Environment variable template
├── .gitignore
├── data/
│   └── financial_data.csv            # Your monthly P&L data
└── .github/
    └── workflows/
        └── weekly_report.yml         # Weekly automation schedule
```

---

## Follow the series

- Post #2: [An AI CFO Agent Is Not a Chatbot](https://borisdracka.com/blog/post-02)
- Interactive walkthrough: [borisdracka.com/blog/post-02-demo](https://borisdracka.com/blog/post-02-demo)
- Newsletter: [borisdracka.beehiiv.com](https://borisdracka.beehiiv.com/subscribe)
- X.com: [@BorisDracka](https://x.com/BorisDracka)

---

© 2026 Boris Dračka · [borisdracka.com](https://borisdracka.com)
