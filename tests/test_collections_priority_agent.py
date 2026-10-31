import pytest

from conftest import load_script, run_script, write_csv

HEADER = "customer_id,customer,amount,days_overdue,reminders_sent,credit_hold"


@pytest.fixture(scope="module")
def coll():
    return load_script("collections_priority_agent")


def rec(cid, overdue, reminders=0, hold="false"):
    return {"customer_id": cid, "customer": "c", "amount": "100", "days_overdue": str(overdue),
            "reminders_sent": str(reminders), "credit_hold": hold}


def ids(rows):
    return [r["customer_id"] for r in rows]


def test_smoke_blog_command():
    r = run_script("collections_priority_agent.py", "data/open_receivables.csv")
    assert r.returncode == 0, r.stderr
    assert "Loaded 8 open receivable(s)" in r.stdout
    assert "2 of 8 receivable(s) reordered" in r.stdout
    order = [l.split()[0] for l in r.stdout.splitlines() if l.startswith("CUST-")]
    assert order[:3] == ["CUST-05", "CUST-03", "CUST-04"]


def test_credit_hold_moves_ahead_of_older_balance(coll):
    ordered, flagged = coll.suggested_order(
        [rec("OLD", 90), rec("HELD", 10, hold="true"), rec("MID", 40)], {"true", "yes", "1"}, None)
    assert ids(ordered) == ["HELD", "OLD", "MID"]
    assert flagged == {"HELD"}


def test_reminders_only_change_rank_with_threshold(coll):
    data = [rec("OLD", 90, 0), rec("NUDGED", 10, 3)]
    default, _ = coll.suggested_order(data, {"true"}, None)
    with_threshold, flagged = coll.suggested_order(data, {"true"}, 3)
    assert ids(default) == ["OLD", "NUDGED"]
    assert ids(with_threshold) == ["NUDGED", "OLD"] and flagged == {"NUDGED"}


def test_custom_hold_values_via_cli(tmp_path):
    csv_path = write_csv(tmp_path / "r.csv", HEADER, ["A,a,100,90,0,no", "B,b,100,10,0,STOP"])
    plain = run_script("collections_priority_agent.py", csv_path)
    custom = run_script("collections_priority_agent.py", csv_path, "--hold-values", "stop")
    assert "0 of 2 receivable(s) reordered" in plain.stdout
    assert "1 of 2 receivable(s) reordered" in custom.stdout


def test_missing_file_fails_with_filenotfound(tmp_path):
    r = run_script("collections_priority_agent.py", tmp_path / "nope.csv")
    assert r.returncode != 0
    assert "FileNotFoundError" in r.stderr


def test_header_only_and_zero_byte_file(tmp_path):
    r = run_script("collections_priority_agent.py", write_csv(tmp_path / "e.csv", HEADER))
    assert r.returncode == 0 and "Loaded 0 open receivable(s)" in r.stdout
    zero = tmp_path / "z.csv"
    zero.write_text("")
    r = run_script("collections_priority_agent.py", zero)
    assert r.returncode == 0 and "Loaded 0 open receivable(s)" in r.stdout
