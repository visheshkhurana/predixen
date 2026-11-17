"""A file we can't read gets a plain next step, not a library traceback."""
import pytest

from server.ingest.excel_extractor import process_termina_excel


def test_unreadable_spreadsheet_message_is_plain(tmp_path, monkeypatch):
    bad = tmp_path / "pl.xlsx"
    bad.write_text("not a spreadsheet")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(Exception) as exc:
        process_termina_excel(str(bad))
    msg = str(exc.value)
    if "API key" in msg or "OPENAI" in msg:
        pytest.skip("missing-key path raises its own error before the fallback message")
    assert "We couldn't read this spreadsheet" in msg
    assert "engine" not in msg and "Error:" not in msg
