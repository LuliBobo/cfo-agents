import pytest

from conftest import load_script, run_script, write_csv

HEADER = "account_id,account_name,balance,buffer,alt_rate_pct"


@pytest.fixture(scope="module")
def idle():
    return load_script("idle_cash_agent")


def test_smoke_blog_command():
    r = run_script("idle_cash_agent.py", "data/account_balances.csv", "--threshold", "50000", "--rate", "3.0")
    assert r.returncode == 0, r.stderr
    assert "Loaded 6 account balance(s)" in r.stdout
    assert "2 of 6 account(s) flagged" in r.stdout
    assert "~€8,100/year (~€675/month)" in r.stdout
    assert "€270,000" in r.stdout


def test_excess_never_negative(idle):
    assert idle.Account("a", "n", 10, 50, 3.0).excess == 0.0
    assert idle.Account("a", "n", 150, 50, 3.0).excess == 100.0


def test_blank_rate_falls_back_to_default(idle, tmp_path):
    csv_path = write_csv(tmp_path / "a.csv", HEADER, ["A1,One,200000,100000,", "A2,Two,200000,100000,5.0"])
    one, two = idle.load_accounts(str(csv_path), default_rate=2.5)
    assert one.alt_rate_pct == 2.5 and two.alt_rate_pct == 5.0


def test_interest_estimate_uses_each_accounts_rate(tmp_path):
    csv_path = write_csv(tmp_path / "a.csv", HEADER, ["A1,One,200000,100000,4.0", "A2,Two,160000,100000,2.0"])
    r = run_script("idle_cash_agent.py", csv_path, "--threshold", "50000")
    # 100000*4% + 60000*2% = 5200 per year, ~433 per month
    assert "~€5,200/year (~€433/month)" in r.stdout


def test_threshold_boundary_and_nothing_flagged(idle, tmp_path):
    accounts = [idle.Account("a", "n", 150, 100, 3.0)]  # excess exactly 50
    assert idle.flag_accounts(accounts, 50) == accounts
    assert idle.flag_accounts(accounts, 51) == []
    csv_path = write_csv(tmp_path / "a.csv", HEADER, ["A1,One,100,100,3.0"])
    r = run_script("idle_cash_agent.py", csv_path)
    assert "0 of 1 account(s) flagged" in r.stdout
    assert "Nothing past the threshold today." in r.stdout


def test_missing_file_exits_1_with_message(tmp_path):
    r = run_script("idle_cash_agent.py", tmp_path / "nope.csv")
    assert r.returncode == 1
    assert "Could not find" in r.stderr


def test_header_only_and_zero_byte_file(tmp_path):
    r = run_script("idle_cash_agent.py", write_csv(tmp_path / "e.csv", HEADER))
    assert r.returncode == 0 and "No accounts found" in r.stdout
    zero = tmp_path / "z.csv"
    zero.write_text("")
    r = run_script("idle_cash_agent.py", zero)
    assert r.returncode == 0 and "No accounts found" in r.stdout
