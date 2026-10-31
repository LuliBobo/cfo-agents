import pytest

from conftest import load_script, write_csv

HEADER = "date,description,amount_eur,type"
TODAY = "2026-06-16"  # first date in data/cashflow_data.csv


@pytest.fixture
def cash(freeze_date):
    module = load_script("cashflow_agent")
    freeze_date(module, TODAY)
    return module


def test_smoke_main_on_sample_data(cash, repo_cwd, offline, fake_gemini, capsys):
    offline(cash)
    calls = fake_gemini(cash, "Cash is fine.")
    cash.main()
    out = capsys.readouterr().out
    assert "Loaded 10 upcoming transactions" in out
    assert "Projection built for 14 days" in out
    assert "No alerts" in out
    assert "Cash is fine." in out
    assert "Agent completed successfully" in out
    assert len(calls) == 1


def test_projection_on_sample_data(cash, repo_cwd):
    tx = cash.pull_transactions("data/cashflow_data.csv")
    proj = cash.build_projection(tx, 62400)
    assert len(proj) == 14
    closing = {d["date"].isoformat(): d["closing"] for d in proj}
    assert closing["2026-06-16"] == 74900
    assert closing["2026-06-19"] == 30800   # the low point of the window
    assert closing["2026-06-29"] == 45000   # nothing after 2026-06-24


def test_only_future_transactions_are_loaded(cash, tmp_path):
    path = write_csv(tmp_path / "c.csv", HEADER, [
        "2026-06-15,yesterday,-100,outflow", "2026-06-16,today,100,inflow", "2026-06-20,later,50,inflow"])
    assert [t["description"] for t in cash.pull_transactions(str(path))] == ["today", "later"]


def test_alert_levels(cash):
    proj = [{"date": d, "closing": c} for d, c in
            [("2026-06-16", 50000), ("2026-06-17", 15000), ("2026-06-18", -10)]]
    alerts = cash.detect_alerts(proj, 20000)
    assert [(a["date"], a["level"]) for a in alerts] == [("2026-06-17", "WARNING"), ("2026-06-18", "CRITICAL")]


def test_no_alerts_when_always_above_threshold(cash):
    assert cash.detect_alerts([{"date": "d", "closing": 20000}], 20000) == []  # equal to threshold is fine


def test_missing_input_file_raises(cash, tmp_path):
    with pytest.raises(FileNotFoundError):
        cash.pull_transactions(str(tmp_path / "nope.csv"))


def test_empty_input_file_gives_flat_projection(cash, tmp_path):
    tx = cash.pull_transactions(str(write_csv(tmp_path / "e.csv", HEADER)))
    assert tx == []
    proj = cash.build_projection(tx, 1000)
    assert {d["closing"] for d in proj} == {1000}


def test_generate_briefing_requires_api_key(cash, monkeypatch):
    monkeypatch.setattr(cash, "GEMINI_API_KEY", "")
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        cash.generate_briefing([], [], 0, "Acme")
