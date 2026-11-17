from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from server.core import error_scrub


def _app():
    app = FastAPI()
    error_scrub.install(app)

    @app.get("/boom")
    def boom():
        raise HTTPException(status_code=500, detail="psycopg2 OperationalError host=10.0.0.5 password=x")

    @app.get("/structured")
    def structured():
        raise HTTPException(status_code=500, detail={"error": "sync_failed", "message": "Shopify said no"})

    @app.get("/notfound")
    def notfound():
        raise HTTPException(status_code=404, detail="Company not found")

    @app.get("/upstream")
    def upstream():
        raise HTTPException(status_code=503, detail="AI provider unavailable")

    @app.get("/crash")
    def crash():
        raise RuntimeError("secret internal path /srv/app/x.py")

    return TestClient(app, raise_server_exceptions=False)


def test_production_hides_500_text_and_gives_reference(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    c = _app()
    r = c.get("/boom")
    assert r.status_code == 500
    body = r.json()
    assert "10.0.0.5" not in r.text and "psycopg2" not in r.text
    assert body["detail"].startswith(error_scrub.GENERIC_500)
    assert body["reference"] in body["detail"]


def test_production_unhandled_exception_is_generic(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    r = _app().get("/crash")
    assert r.status_code == 500
    assert "/srv/app" not in r.text
    assert r.json()["detail"].startswith(error_scrub.GENERIC_500)


def test_other_statuses_and_structured_details_unchanged(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    c = _app()
    assert c.get("/notfound").json() == {"detail": "Company not found"}
    assert c.get("/upstream").json() == {"detail": "AI provider unavailable"}
    assert c.get("/structured").json()["detail"]["message"] == "Shopify said no"


def test_development_keeps_real_text(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("NODE_ENV", raising=False)
    r = _app().get("/boom")
    assert "psycopg2" in r.json()["detail"]
