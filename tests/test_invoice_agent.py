import datetime

import pytest

from conftest import load_script, write_csv

HEADER = "invoice_id,client,amount_eur,due_date,contact_email,status"
TODAY = "2026-06-01"


@pytest.fixture
def inv_mod(freeze_date):
    module = load_script("invoice_agent")
    freeze_date(module, TODAY)
    return module


def due(days_ago):
    return (datetime.date.fromisoformat(TODAY) - datetime.timedelta(days=days_ago)).isoformat()


def csv_rows(*specs):
    return [f"I{n},Client{n},{amount},{due(days)},c{n}@example.com,{status}"
            for n, (amount, days, status) in enumerate(specs, start=1)]


def test_smoke_main_on_sample_data(inv_mod, repo_cwd, offline, fake_gemini, capsys):
    offline(inv_mod)
    calls = fake_gemini(inv_mod, "Dear client, please pay.")
    inv_mod.main()
    out = capsys.readouterr().out
    assert "Loaded 8 invoices" in out
    assert "Found 7 overdue invoices" in out  # INV-008 (due 2026-06-02) is not yet overdue on 2026-06-01
    assert "Agent completed successfully" in out
    assert "Dear client, please pay." in out
    assert len(calls) == 7


def test_severity_thresholds_and_exclusions(inv_mod, tmp_path):
    path = write_csv(tmp_path / "i.csv", HEADER, csv_rows(
        (100, 10, "unpaid"), (100, 30, "unpaid"), (100, 60, "unpaid"),
        (100, 90, "paid"),      # paid -> ignored
        (100, 0, "unpaid"),     # due today -> not overdue
        (100, -5, "unpaid"),    # due in the future
    ))
    overdue = inv_mod.detect_overdue(inv_mod.pull_invoices(str(path)))
    assert [(i["days_overdue"], i["severity"]) for i in overdue] == [
        (10, "watch"), (30, "warning"), (60, "critical")]


def test_prioritize_ranks_by_amount_times_days(inv_mod):
    overdue = [
        {"invoice_id": "SMALL_OLD", "client": "a", "amount_eur": 100, "days_overdue": 100},   # 10 000
        {"invoice_id": "BIG_NEW", "client": "b", "amount_eur": 5000, "days_overdue": 5},      # 25 000
        {"invoice_id": "MID", "client": "c", "amount_eur": 1000, "days_overdue": 20},         # 20 000
    ]
    ranked = inv_mod.prioritize(overdue)
    assert [i["invoice_id"] for i in ranked] == ["BIG_NEW", "MID", "SMALL_OLD"]
    assert ranked[0]["risk_score"] == 25000


def test_no_overdue_invoices_exits_cleanly(inv_mod, tmp_path, monkeypatch, capsys):
    path = write_csv(tmp_path / "i.csv", HEADER, csv_rows((100, 0, "unpaid"), (100, 5, "paid")))
    monkeypatch.setattr(inv_mod, "INVOICE_FILE", str(path))
    inv_mod.main()
    assert "No overdue invoices found" in capsys.readouterr().out


def test_missing_input_file_raises(inv_mod, tmp_path):
    with pytest.raises(FileNotFoundError):
        inv_mod.pull_invoices(str(tmp_path / "nope.csv"))


def test_empty_input_file(inv_mod, tmp_path, monkeypatch, capsys):
    path = write_csv(tmp_path / "e.csv", HEADER)
    assert inv_mod.pull_invoices(str(path)) == []
    monkeypatch.setattr(inv_mod, "INVOICE_FILE", str(path))
    inv_mod.main()
    assert "No overdue invoices found" in capsys.readouterr().out


def test_generate_reminders_requires_api_key(inv_mod, monkeypatch):
    monkeypatch.setattr(inv_mod, "GEMINI_API_KEY", "")
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        inv_mod.generate_reminders([{"x": 1}], "Acme")


def test_reminder_subject_and_text(inv_mod, fake_gemini):
    fake_gemini(inv_mod, "  body  ")
    item = {"invoice_id": "I1", "client": "C", "amount_eur": 1500.0, "days_overdue": 45,
            "severity": "warning", "due_date": datetime.date(2026, 4, 17)}
    out = inv_mod.generate_reminders([item], "Acme")[0]
    assert out["reminder_email"] == "body"
    assert out["email_subject"] == "Payment Reminder — I1 — €1,500 — 45 Days Overdue"
