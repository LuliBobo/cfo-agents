import pytest

from conftest import ROOT, load_script, write_csv

HEADER = "line_item,this_month,last_month"


@pytest.fixture
def cfo():
    return load_script("cfo_agent")


SYNTH = [
    "Revenue,1000,800", "COGS,400,400", "Operating Expenses,800,500",
    "Cash Balance,3000,3000", "Accounts Receivable,100,50",
]


def test_smoke_main_on_sample_data(cfo, repo_cwd, offline, fake_gemini, capsys):
    offline(cfo)
    calls = fake_gemini(cfo, "Narrative text")
    cfo.main()
    out = capsys.readouterr().out
    assert "Loaded 6 line items" in out
    assert "Data clean" in out
    assert "Email credentials not configured" in out and "Narrative text" in out
    assert "Agent completed successfully" in out
    assert len(calls) == 1 and "Revenue: $285,000" in calls[0]


def test_kpis_on_synthetic_data(cfo, tmp_path):
    data = cfo.pull_data(str(write_csv(tmp_path / "f.csv", HEADER, SYNTH)))
    k = cfo.calculate_kpis(data)
    assert k["gross_margin_cur"] == pytest.approx(60.0)
    assert k["net_income_cur"] == -200 and k["net_income_prev"] == -100
    assert k["burn_rate"] == 200 and k["runway"] == pytest.approx(15.0)
    assert k["rev_growth"] == pytest.approx(25.0)
    assert k["dso"] == pytest.approx(3.0)
    assert k["op_leverage"] == pytest.approx(-4.0)


def test_profitable_company_has_no_burn_and_infinite_runway(cfo, tmp_path):
    rows = ["Revenue,1000,1000", "COGS,100,100", "Operating Expenses,100,100",
            "Cash Balance,500,500", "Accounts Receivable,0,0"]
    k = cfo.calculate_kpis(cfo.pull_data(str(write_csv(tmp_path / "f.csv", HEADER, rows))))
    assert k["burn_rate"] == 0 and k["runway"] == float("inf")
    assert k["op_leverage"] is None  # revenue did not change


def test_clean_data_reports_missing_and_negative_items(cfo, capsys):
    cfo.clean_data({"Revenue": {"this_month": -5.0, "last_month": 1.0}})
    out = capsys.readouterr().out
    assert "Missing required line item: 'COGS'" in out
    assert "Unexpected negative value for 'Revenue'" in out


def test_missing_input_file_raises(cfo, tmp_path):
    with pytest.raises(FileNotFoundError):
        cfo.pull_data(str(tmp_path / "nope.csv"))


def test_empty_input_file(cfo, tmp_path, capsys):
    data = cfo.pull_data(str(write_csv(tmp_path / "e.csv", HEADER)))
    assert data == {}
    cfo.clean_data(data)
    assert "Missing required line item: 'Revenue'" in capsys.readouterr().out
    # Pins current behaviour: validation only warns, so KPI calculation then fails with a bare KeyError.
    with pytest.raises(KeyError):
        cfo.calculate_kpis(data)


def test_generate_report_requires_api_key(cfo, monkeypatch):
    monkeypatch.setattr(cfo, "GEMINI_API_KEY", "")
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        cfo.generate_report({}, "Acme")


def test_email_is_sent_only_when_credentials_exist(cfo, monkeypatch, capsys):
    sent = []

    class FakeSMTP:
        def __init__(self, host, port): sent.append((host, port))
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def login(self, user, pw): sent.append(("login", user))
        def sendmail(self, frm, to, msg): sent.append(("sendmail", to))

    monkeypatch.setattr(cfo.smtplib, "SMTP_SSL", FakeSMTP)
    kpis = {"rev_cur": 1, "rev_growth": 0, "gross_margin_cur": 0, "net_income_cur": 0,
            "burn_rate": 0, "runway": float("inf"), "dso": 0}
    for var, val in (("SENDER_EMAIL", "a@example.com"), ("SENDER_PASSWORD", "x"), ("RECIPIENT_EMAIL", "b@example.com")):
        monkeypatch.setattr(cfo, var, val)
    cfo.deliver_report("text", kpis, "Acme")
    assert ("sendmail", "b@example.com") in sent
    sent.clear()
    monkeypatch.setattr(cfo, "SENDER_PASSWORD", "")
    cfo.deliver_report("text", kpis, "Acme")
    assert sent == []
    assert "printing to terminal" in capsys.readouterr().out
