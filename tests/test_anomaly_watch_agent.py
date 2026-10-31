from datetime import date

import pytest

from conftest import load_script, run_script, write_csv

HEADER = "id,date,supplier,amount,account"


@pytest.fixture(scope="module")
def anomaly():
    return load_script("anomaly_watch_agent")


def pay(pid, d, amount, account="ACC-1", supplier="S"):
    return {"id": pid, "date": d, "supplier": supplier, "amount": float(amount), "account": account}


@pytest.fixture
def history():
    # five payments of 100 to the same account, all on Mondays -> median 100, spread floored at 1
    return [pay(f"H{i}", date(2026, 6, 1 + 7 * i), 100) for i in range(5)]


def run_check(anomaly, payment, history, tolerance=3.5, dup_days=5, signals=("amount", "duplicate", "account")):
    return anomaly.check(payment, anomaly.baseline(history), history, tolerance, dup_days, set(signals))


# ---- smoke on the shipped sample data, with the exact numbers the blog shows ----

def test_smoke_blog_default_command():
    r = run_script("anomaly_watch_agent.py", "data/payments.csv")
    assert r.returncode == 0, r.stderr
    assert "Loaded 378 payment(s)" in r.stdout
    assert "1 of 42 payment(s) flagged" in r.stdout
    assert "P0349" in r.stdout and "new account for this supplier" in r.stdout


@pytest.mark.parametrize("tolerance,expected", [("1.5", "9 of 42"), ("60", "0 of 42")])
def test_smoke_blog_tolerance_variants(tolerance, expected):
    r = run_script("anomaly_watch_agent.py", "data/payments.csv", "--tolerance", tolerance, "--signals", "amount")
    assert r.returncode == 0, r.stderr
    assert f"{expected} payment(s) flagged" in r.stdout


# ---- key logic on small synthetic inputs ----

def test_baseline_median_scale_and_accounts(anomaly, history):
    b = anomaly.baseline(history)["S"]
    assert b["median"] == 100 and b["scale"] == 1.0  # floor = 1 % of the median
    assert b["accounts"] == {"ACC-1"} and b["weekday"] == 0


def test_amount_outside_band_is_flagged(anomaly, history):
    reasons = run_check(anomaly, pay("N", date(2026, 8, 3), 110), history)
    assert any(r.startswith("amount 1.1x usual") for r in reasons)


def test_normal_payment_is_not_flagged(anomaly, history):
    assert run_check(anomaly, pay("N", date(2026, 8, 3), 100), history) == []


def test_repeated_amount_within_window(anomaly, history):
    earlier = history + [pay("E", date(2026, 8, 3), 100)]
    p = pay("N", date(2026, 8, 5), 100)
    base = anomaly.baseline(history)
    assert "same amount paid 2d earlier" in anomaly.check(p, base, earlier, 3.5, 5, {"duplicate"})
    assert anomaly.check(p, base, earlier, 3.5, 1, {"duplicate"}) == []  # outside the window


def test_new_account_is_flagged(anomaly, history):
    reasons = run_check(anomaly, pay("N", date(2026, 8, 3), 100, account="ACC-NEW"), history)
    assert "new account for this supplier" in reasons


def test_weekday_alone_never_flags(anomaly, history):
    wednesday = pay("N", date(2026, 8, 5), 100)
    assert run_check(anomaly, wednesday, history) == []
    with_reason = run_check(anomaly, pay("N", date(2026, 8, 5), 100, account="ACC-NEW"), history)
    assert with_reason[-1] == "usual day Mon"


def test_signals_can_be_restricted(anomaly, history):
    p = pay("N", date(2026, 8, 3), 110, account="ACC-NEW")
    assert run_check(anomaly, p, history, signals=("account",)) == ["new account for this supplier"]


def test_unknown_supplier_has_no_baseline_so_no_flags(anomaly, history):
    assert run_check(anomaly, pay("N", date(2026, 8, 3), 999, supplier="Other"), history) == []


def test_week_start_is_monday(anomaly):
    assert anomaly.week_start_of(date(2026, 10, 2)) == date(2026, 9, 28)  # a Friday


def test_cli_flags_outlier_in_synthetic_file(tmp_path):
    rows = [f"H{i},{date(2026, 6, 1 + 7 * i).isoformat()},S,100,ACC-1" for i in range(5)]
    rows.append("N1,2026-07-06,S,500,ACC-1")
    r = run_script("anomaly_watch_agent.py", write_csv(tmp_path / "p.csv", HEADER, rows))
    assert r.returncode == 0, r.stderr
    assert "1 of 1 payment(s) flagged" in r.stdout and "N1" in r.stdout


# ---- missing / empty input ----

def test_missing_file_fails_with_filenotfound(tmp_path):
    r = run_script("anomaly_watch_agent.py", tmp_path / "nope.csv")
    assert r.returncode != 0
    assert "FileNotFoundError" in r.stderr


def test_header_only_file_currently_crashes(tmp_path):
    # Pins current behaviour: max() over zero payments raises ValueError (no friendly message).
    r = run_script("anomaly_watch_agent.py", write_csv(tmp_path / "e.csv", HEADER))
    assert r.returncode != 0
    assert "ValueError" in r.stderr


def test_header_only_file_with_explicit_week_is_handled(tmp_path):
    r = run_script("anomaly_watch_agent.py", write_csv(tmp_path / "e.csv", HEADER), "--week-start", "2026-08-03")
    assert r.returncode == 0
    assert "0 of 0 payment(s) flagged" in r.stdout
