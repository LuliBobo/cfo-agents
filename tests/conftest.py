"""Shared helpers for the cfo-agents test suite.

Nothing here touches the network: the Gemini client and SMTP are always
replaced by fakes, and all scripts are run against sample or synthetic CSVs.
"""
import datetime
import importlib.util
import os
import subprocess
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# Variables that would make a script talk to Gemini / Gmail if a developer has them set.
_SECRET_VARS = ("GEMINI_API_KEY", "SENDER_EMAIL", "SENDER_PASSWORD", "RECIPIENT_EMAIL")


def run_script(name, *args, cwd=ROOT):
    """Run a root-level script exactly as the README/blog does: `python <name> <args>`."""
    env = {k: v for k, v in os.environ.items() if k not in _SECRET_VARS}
    return subprocess.run(
        [sys.executable, str(ROOT / name), *map(str, args)],
        cwd=str(cwd), env=env, capture_output=True, text=True, timeout=60,
    )


def load_script(name):
    """Import a root-level script as a module (its main() is guarded by __name__)."""
    path = ROOT / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"cfo_test_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_csv(path, header, rows=()):
    lines = [header, *rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def repo_cwd(monkeypatch):
    """Scripts with a hard-coded relative data path expect to run from the repo root."""
    monkeypatch.chdir(ROOT)
    return ROOT


@pytest.fixture
def freeze_date(monkeypatch):
    """freeze_date(module, "YYYY-MM-DD"): make `datetime.date.today()` inside a script fixed."""
    def _freeze(module, iso):
        fixed = datetime.date.fromisoformat(iso)

        class FakeDate(datetime.date):
            @classmethod
            def today(cls):
                return cls(fixed.year, fixed.month, fixed.day)

        shim = types.SimpleNamespace(
            date=FakeDate, datetime=datetime.datetime, timedelta=datetime.timedelta,
        )
        monkeypatch.setattr(module, "datetime", shim)
    return _freeze


@pytest.fixture
def offline(monkeypatch):
    """offline(module): blank credentials and make any SMTP use a test failure."""
    class NoSMTP:
        def __init__(self, *a, **k):
            raise AssertionError("SMTP must not be used in tests")

    def _offline(module):
        for var in ("GEMINI_API_KEY", "SENDER_EMAIL", "SENDER_PASSWORD", "RECIPIENT_EMAIL"):
            monkeypatch.setattr(module, var, "")
        monkeypatch.setattr(module.smtplib, "SMTP_SSL", NoSMTP)
    return _offline


@pytest.fixture
def fake_gemini(monkeypatch):
    """fake_gemini(module, text): replace the genai client so no API call can happen."""
    def _fake(module, text="FAKE AI TEXT"):
        calls = []

        class Models:
            def generate_content(self, model, contents):
                calls.append(contents)
                return types.SimpleNamespace(text=text)

        class Client:
            def __init__(self, api_key=None):
                self.models = Models()

        monkeypatch.setattr(module, "genai", types.SimpleNamespace(Client=Client))
        monkeypatch.setattr(module, "GEMINI_API_KEY", "test-key")
        return calls
    return _fake
