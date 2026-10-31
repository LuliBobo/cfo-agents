import pytest

from conftest import DATA, load_script, run_script, write_csv

HEADER = "position_id,client,currency_pair,amount_foreign,booked_rate,current_rate,invoice_date"


@pytest.fixture(scope="module")
def fx():
    return load_script("fx_monitor_agent")


def test_smoke_blog_command():
    r = run_script("fx_monitor_agent.py", "data/fx_positions.csv", "--threshold", "2.0")
    assert r.returncode == 0, r.stderr
    assert "Loaded 6 open position(s)" in r.stdout
    assert "2 of 6 position(s) flagged" in r.stdout
    assert "FX-01" in r.stdout and "FX-05" in r.stdout
    assert "-4,622.49" in r.stdout


def test_position_variance(fx):
    # 1100 USD booked at 1.10 -> 1000 EUR; at 1.00 it is worth 1100 EUR: +100 EUR, +10 %
    p = fx.Position("X", "c", "EUR/USD", 1100.0, 1.10, 1.00, "2026-01-01")
    assert p.eur_booked == pytest.approx(1000.0)
    assert p.variance_eur == pytest.approx(100.0)
    assert p.variance_pct == pytest.approx(10.0)


def test_flags_both_directions_and_boundary(fx):
    up = fx.Position("UP", "c", "EUR/USD", 1100.0, 1.10, 1.00, "d")      # +10 %
    down = fx.Position("DN", "c", "EUR/USD", 1000.0, 1.00, 1.10, "d")    # about -9.1 %
    flat = fx.Position("FL", "c", "EUR/USD", 1000.0, 1.00, 1.001, "d")   # about -0.1 %
    flagged = fx.flag_positions([up, down, flat], 2.0)
    assert [p.position_id for p in flagged] == ["UP", "DN"]
    # a position exactly on the threshold is flagged (>=)
    assert fx.flag_positions([up], 10.0) == [up]


def test_load_positions_from_synthetic_csv(fx, tmp_path):
    csv_path = write_csv(tmp_path / "p.csv", HEADER, ["A,Client,EUR/USD,1000,1.0,1.0,2026-01-01"])
    positions = fx.load_positions(str(csv_path))
    assert len(positions) == 1 and positions[0].variance_eur == 0


def test_missing_file_exits_1_with_message(tmp_path):
    r = run_script("fx_monitor_agent.py", tmp_path / "nope.csv")
    assert r.returncode == 1
    assert "Could not find" in r.stderr


def test_header_only_file(tmp_path):
    r = run_script("fx_monitor_agent.py", write_csv(tmp_path / "e.csv", HEADER))
    assert r.returncode == 0
    assert "No open positions found" in r.stdout


def test_zero_byte_file(tmp_path):
    empty = tmp_path / "e.csv"
    empty.write_text("")
    r = run_script("fx_monitor_agent.py", empty)
    assert r.returncode == 0
    assert "No open positions found" in r.stdout
