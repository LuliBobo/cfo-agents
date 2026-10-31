import datetime

import pytest

from conftest import load_script, write_csv

HEADER = "date,description,amount_eur,type"
TODAY = "2026-06-16"


@pytest.fixture
def ceo(freeze_date):
    module = load_script("ceo_dashboard_agent")
    freeze_date(module, TODAY)
    return module


def tx(day, desc, amount):
    return {"date": datetime.date.fromisoformat(day), "description": desc,
            "amount_eur": float(amount), "type": "inflow" if amount > 0 else "outflow"}


def test_smoke_main_on_sample_data(ceo, repo_cwd, offline, fake_gemini, capsys):
    offline(ceo)
    calls = fake_gemini(ceo, "Plan ahead.")
    ceo.main()
    out = capsys.readouterr().out
    assert "10 upcoming transactions loaded" in out
    assert "7-day forward cash view" in out
    assert "THE 3 NUMBERS YOU NEED" in out and "Plan ahead." in out
    assert "Agent completed successfully" in out
    assert len(calls) == 1


def test_forward_view_totals_and_payroll(ceo):
    txs = [tx("2026-06-17", "Client payment", 10000), tx("2026-06-18", "Payroll run", -20000),
           tx("2026-06-19", "Rent", -5000), tx("2026-07-30", "Outside window", -999)]
    view = ceo.assemble_forward_view(txs, 100000)
    assert view["total_inflows"] == 10000 and view["total_outflows"] == 25000
    assert view["payroll_amount"] == 20000
    assert view["projected_eow"] == 85000
    assert view["payroll_covered"] is True
    assert len(view["days"]) == 7 and view["days"][-1]["balance"] == 85000


def test_payroll_not_covered_when_balance_too_low(ceo):
    view = ceo.assemble_forward_view([tx("2026-06-18", "Payroll run", -20000)], 5000)
    assert view["projected_eow"] == -15000
    assert view["payroll_covered"] is False


def test_analyze_answers_the_three_questions(ceo):
    view = ceo.assemble_forward_view(
        [tx("2026-06-17", "Client payment", 10000), tx("2026-06-18", "Payroll run", -20000)], 100000)
    a = ceo.analyze(view)
    assert a["q1_current_balance"] == "€100,000"
    assert a["q2_expected_inflows"] == "€10,000 expected (1 invoices)"
    assert "Payroll €20,000" in a["q3_outflows_status"] and "COVERED" in a["q3_outflows_status"]
    assert a["projected_eow"] == "€90,000"


def test_only_future_transactions_are_loaded(ceo, tmp_path):
    path = write_csv(tmp_path / "c.csv", HEADER, ["2026-06-15,old,-1,outflow", "2026-06-16,today,1,inflow"])
    assert [t["description"] for t in ceo.pull_transactions(str(path))] == ["today"]


def test_missing_input_file_raises(ceo, tmp_path):
    with pytest.raises(FileNotFoundError):
        ceo.pull_transactions(str(tmp_path / "nope.csv"))


def test_empty_input_file(ceo, tmp_path):
    txs = ceo.pull_transactions(str(write_csv(tmp_path / "e.csv", HEADER)))
    assert txs == []
    view = ceo.assemble_forward_view(txs, 1000)
    assert view["projected_eow"] == 1000 and view["payroll_covered"] is True
    assert ceo.analyze(view)["q2_expected_inflows"] == "€0 expected (0 invoices)"


def test_generate_briefing_requires_api_key(ceo, monkeypatch):
    monkeypatch.setattr(ceo, "GEMINI_API_KEY", "")
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        ceo.generate_briefing({}, {}, "Acme")
