# Consistency report: scripts / CSVs / README vs. blog

Scope: read-only comparison of this repo (`main` at `a8c7237`) with the blog repo
`LuliBobo/lulibobo.github.io` (default branch, commit `011c524`): `blog/post-XX.html`,
`blog/post-XX-demo.html`, the `sk/blog/` counterparts and `agents.html`.

**Not verified:** https://borisdracka.com/ itself. The sandbox proxy answered `403` for that host, so the
live site was not fetched. Everything below refers to the blog repo's source files, which I assume is
what the site serves. Nothing was changed in the blog repo.

Status legend: **OK** = matches; **missing** = something that should exist does not; **mismatch** = both
exist but disagree.

## Summary table

| Post | Blog page with run instructions | Script (repo root) | CSV (`data/`) | README section | Status |
|------|--------------------------------|--------------------|---------------|----------------|--------|
| #2 Weekly CFO Report | `post-02-demo` (repo link only, no run command) | `cfo_agent.py` OK | `financial_data.csv` OK | Agent 01 OK | OK |
| #3 Invoice Agent | `post-03-demo`, section "Build it yourself" | `invoice_agent.py` OK | `invoices.csv` OK | Agent 02 OK | OK (see note 4) |
| #4 Cash Flow Alert | none (post-04 has no repo link or command) | `cashflow_agent.py` exists, docstring says Post #4 | `cashflow_data.csv` exists | **missing** | **missing** (see note 5) |
| #5 CEO Dashboard | none (post-05 has no repo link or command) | `ceo_dashboard_agent.py` exists, docstring says Post #5 | reuses `cashflow_data.csv` | **missing** | **missing** (see note 5) |
| #9 FX Monitoring | `post-09-demo`, "Try it yourself" | `fx_monitor_agent.py` OK | `fx_positions.csv` OK | Agent 03 OK | OK (see note 1) |
| #10 Idle Cash | `post-10-demo`, "Try it yourself" | `idle_cash_agent.py` OK | `account_balances.csv` OK | Agent 04 OK | OK (see note 2) |
| #11 Invoice Priority | `post-11-demo`, "Try it yourself" | `invoice_priority_agent.py` OK | `open_invoices.csv` OK | Agent 05 OK | **mismatch** (see note 3) |
| #12 Collections Priority | `post-12-demo`, "Try it yourself" | `collections_priority_agent.py` OK | `open_receivables.csv` OK | Agent 06 OK | OK |
| #16 Anomaly Watch | `post-16-demo`, "Try it yourself" | `anomaly_watch_agent.py` OK | `payments.csv` OK | Agent 07 OK | OK |

Posts 1, 6, 7, 8, 13, 14, 15 and 17 do not mention the repo, a script or a CSV (checked with grep for
`cfo-agents`, `.py`, `.csv`); nothing to compare.

Agent numbering: README Agent 01-07 and the blog's `agents.html` ("Seven small agents", 01-07) use the same
numbering and the same post mapping. Agent 02 is present in the README now. `cashflow_agent.py` and
`ceo_dashboard_agent.py` have no agent number in either place.

## Blog command vs. what actually runs

Each command was run from the repo root with `python`, exactly as written in the blog.
The English and Slovak pages contain identical commands in all six demos.

| Command in blog | Result |
|-----------------|--------|
| `python invoice_agent.py` (post-03-demo) | Runs steps 1-3, then stops at step 4 with `ValueError: GEMINI_API_KEY is not set` unless `.env` is filled in. The blog does tell the reader to do that in its step 3. Not run with a real key. |
| `python fx_monitor_agent.py data/fx_positions.csv --threshold 2.0` | OK: 6 positions, 2 flagged, net `-4,622.49`, same figures as the blog |
| `python3 fx_monitor_agent.py` (post-09-demo, tech card) | OK, the CSV path defaults to `data/fx_positions.csv` |
| `python idle_cash_agent.py data/account_balances.csv --threshold 50000 --rate 3.0` | OK: 2 of 6 flagged, `~EUR 8,100/year (~EUR 675/month)`, same as the blog |
| `python invoice_priority_agent.py data/open_invoices.csv` | OK: 2 of 8 reordered, same as the blog |
| `python collections_priority_agent.py data/open_receivables.csv` | OK: output identical to the blog |
| `python anomaly_watch_agent.py data/payments.csv` | OK: 378 / 336 / 42, `P0349`, identical to the blog |
| `... --tolerance 1.5 --signals amount` / `--tolerance 60 --signals amount` | OK: 9 of 42 / 0 of 42 flagged, as the blog says (also covered by tests) |

The README commands for Agents 02-07 are identical to the blog commands.

## Findings

### Mismatches

1. **Sample output is abridged in post-09-demo and post-11-demo.** The numbers match, but the scripts print
   all rows (blog shows only the flagged ones) and the last FX line reads
   `Net unrealized FX variance across all open positions: EUR -4,622.49`, while the blog shows
   `Net unrealized FX variance: EUR -4,622.49` (with a typographic minus). Cosmetic. Also, in the real FX
   output the client name `Xi Manufacturing` runs into the pair column (`Xi ManufacturingEUR/USD`); the
   column width is 16, the name is 16 characters.
2. **Idle cash: "more than" vs. `>=`.** The script prints "more than EUR 50,000 sitting idle" and the README
   says "excess-above-buffer amount past which an account gets flagged", but the code flags
   `excess >= threshold`. An account with an excess of exactly the threshold is flagged. The boundary is
   pinned in `tests/test_idle_cash_agent.py`.
3. **post-11-demo claims options the script does not have.** The card "Configurable signals" says "Which
   flags count as 'critical' and the discount threshold are command-line arguments, not hardcoded." In
   `invoice_priority_agent.py` the only argument is the CSV path; there is no flag for either. The README
   is accurate here (it says the discount window is displayed but not used for the rank). Either the blog
   text or the script needs to change.
4. **post-03-demo, static "Step 2 & 3 output" panel:** it shows `EUR 104,900` total at risk and
   `2 Warning`. The sample `data/invoices.csv` sums to `EUR 103,100` and, on the date the panel's own
   terminal block shows (2026-06-05), has 1 warning invoice (INV-002, 46 days). The terminal block says
   INV-003 is 81 days overdue (true on 2026-06-04) and INV-007 97 days (true on 2026-06-05). I cannot tell
   whether the panel is meant as an illustration.

### Missing

5. **README has no section for `cashflow_agent.py` (Post #4) or `ceo_dashboard_agent.py` (Post #5).** Both
   scripts, their workflows (`daily_cashflow.yml`, `ceo_briefing.yml`) and `data/cashflow_data.csv` exist, and
   the docstrings point to blog posts 04 and 05, but neither the README, `agents.html`, nor posts 04/05
   mention them as runnable agents.
6. **README "File structure" block is out of date.** Missing: `collections_priority_agent.py`,
   `anomaly_watch_agent.py`, `cashflow_agent.py`, `ceo_dashboard_agent.py`, `data/cashflow_data.csv`, and the
   workflows `overdue_check.yml`, `daily_cashflow.yml`, `ceo_briefing.yml` (only `weekly_report.yml` is
   listed).
7. **README "Follow the series" list** lacks Posts #12 and #16 (and #4, #5) and their walkthrough pages
   (`post-12-demo`, `post-16-demo` exist), and `post-02-demo` is listed twice.
8. **README Step 4** shows a `financial_data.csv` excerpt without the `Payroll` row that the real file has
   (the script does not use it).

Also checked and fine: the `agents.html` links to `.../blob/main/<script>.py` all point to files that exist.

### Not checked

- The live site (see above), including whether `https://borisdracka.com/blog/post-NN` (links used in the
  README) resolve.
- Slovak pages beyond the commands/URLs (text translation accuracy is out of scope).
- Real Gemini and SMTP behaviour (`cfo_agent.py`, `invoice_agent.py`, `cashflow_agent.py`,
  `ceo_dashboard_agent.py`): tests use a fake client and a blocked SMTP, so the post-03 command was not
  run end to end.

## Suggested README fixes (not applied)

- Add the missing scripts, data file and workflows to the File structure block.
- Add Posts #12 and #16 (and #4, #5 if they are public agents) to "Follow the series" and drop the duplicate
  `post-02-demo` line.
- Decide whether Agents 04/05 in the blog numbering (cash flow, CEO dashboard) get numbers or are
  documented as extras.
- Add the `Payroll` row to the Step 4 CSV excerpt.
