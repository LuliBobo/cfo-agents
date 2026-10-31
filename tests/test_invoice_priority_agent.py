import pytest

from conftest import load_script, run_script, write_csv

HEADER = "invoice_id,vendor,amount,due_in_days,discount_terms,critical_vendor"


@pytest.fixture(scope="module")
def prio():
    return load_script("invoice_priority_agent")


def inv(i, due, critical):
    return {"invoice_id": i, "vendor": "v", "amount": "100", "due_in_days": str(due),
            "discount_terms": "", "critical_vendor": critical}


def test_smoke_blog_command():
    r = run_script("invoice_priority_agent.py", "data/open_invoices.csv")
    assert r.returncode == 0, r.stderr
    assert "Loaded 8 open invoice(s)" in r.stdout
    assert "2 of 8 invoice(s) reordered" in r.stdout
    ranked = [l.split()[0] for l in r.stdout.splitlines() if l.startswith("INV-")]
    assert ranked[:3] == ["INV-05", "INV-02", "INV-03"]


def test_critical_vendor_jumps_ahead_of_earlier_due(prio):
    ordered, moved = prio.suggested_order([inv("A", 1, "false"), inv("B", 9, "true"), inv("C", 3, "false")])
    assert [i["invoice_id"] for i in ordered] == ["B", "A", "C"]
    assert moved == {"B"}


def test_without_critical_vendors_order_is_by_due_date(prio):
    ordered, moved = prio.suggested_order([inv("A", 5, "false"), inv("B", 2, "false")])
    assert [i["invoice_id"] for i in ordered] == ["B", "A"]
    assert moved == set()


def test_critical_flag_is_case_and_whitespace_insensitive(prio):
    ordered, _ = prio.suggested_order([inv("A", 1, "false"), inv("B", 9, " TRUE ")])
    assert ordered[0]["invoice_id"] == "B"


def test_critical_already_first_is_not_counted_as_reordered(tmp_path):
    csv_path = write_csv(tmp_path / "i.csv", HEADER, ["A,v,100,1,,true", "B,v,100,5,,false"])
    r = run_script("invoice_priority_agent.py", csv_path)
    assert "0 of 2 invoice(s) reordered" in r.stdout


def test_missing_file_fails_with_filenotfound(tmp_path):
    r = run_script("invoice_priority_agent.py", tmp_path / "nope.csv")
    assert r.returncode != 0
    assert "FileNotFoundError" in r.stderr


def test_no_argument_prints_usage():
    r = run_script("invoice_priority_agent.py")
    assert r.returncode == 1
    assert "Usage:" in r.stdout


def test_header_only_and_zero_byte_file(tmp_path):
    r = run_script("invoice_priority_agent.py", write_csv(tmp_path / "e.csv", HEADER))
    assert r.returncode == 0 and "Loaded 0 open invoice(s)" in r.stdout
    zero = tmp_path / "z.csv"
    zero.write_text("")
    r = run_script("invoice_priority_agent.py", zero)
    assert r.returncode == 0 and "Loaded 0 open invoice(s)" in r.stdout
