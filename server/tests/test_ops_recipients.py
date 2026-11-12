"""Ops newsletter scripts load recipients from env / a gitignored file, never source."""
import re
from pathlib import Path

import pytest

from server.email import recipients as rc

EMAIL_DIR = Path(__file__).resolve().parents[1] / "email"


def test_env_var_takes_precedence(monkeypatch, tmp_path):
    f = tmp_path / "r.txt"
    f.write_text("file@example.com\n")
    monkeypatch.setenv("RECIPIENTS_FILE", str(f))
    monkeypatch.setenv("RECIPIENTS", "a@example.com, Bee <b.b@example.com>")
    got = rc.load_recipients()
    assert [r["email"] for r in got] == ["a@example.com", "b.b@example.com"]
    assert got[1]["name"] == "Bee"
    assert got[1]["id"] == "b_b"


def test_file_format(monkeypatch, tmp_path):
    f = tmp_path / "r.txt"
    f.write_text("# comment\n\nx@example.com,Xavier,xav_1\ny@example.com  # trailing\n")
    monkeypatch.delenv("RECIPIENTS", raising=False)
    monkeypatch.setenv("RECIPIENTS_FILE", str(f))
    got = rc.load_recipients(default_name="Team")
    assert got == [
        {"email": "x@example.com", "name": "Xavier", "id": "xav_1"},
        {"email": "y@example.com", "name": "Team", "id": "y"},
    ]


def test_unconfigured_returns_empty(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("RECIPIENTS", raising=False)
    monkeypatch.setenv("RECIPIENTS_FILE", str(tmp_path / "missing.txt"))
    assert rc.load_recipients() == []
    assert "no recipients configured" in capsys.readouterr().err


def test_invalid_email_rejected(monkeypatch):
    monkeypatch.setenv("RECIPIENTS", "not-an-email")
    with pytest.raises(ValueError):
        rc.load_recipients()


def test_update_scripts_have_no_hardcoded_recipients():
    scripts = sorted(EMAIL_DIR.glob("send_update_v*.py"))
    assert scripts
    email_re = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
    for path in scripts:
        text = path.read_text()
        assert "load_recipients()" in text, path.name
        # Only sender identities remain; no recipient dict literals.
        assert '{"email": "' not in text, path.name
        for addr in email_re.findall(text):
            assert addr.split("@")[1] in {"founderconsole.ai", "runora.xyz", "runoraai.com"}, (path.name, addr)


def test_recipients_local_file_is_gitignored():
    gitignore = (EMAIL_DIR.parents[1] / ".gitignore").read_text()
    assert "server/email/recipients.local.txt" in gitignore
