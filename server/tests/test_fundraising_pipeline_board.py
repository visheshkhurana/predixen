"""The Fundraising page's pipeline board is the company's own data, never a canned list."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import server.models  # noqa: F401  (registers every mapper)
from server.api import fundraising as fundraising_api
from server.core.db import get_db
from server.core.security import get_current_user
from server.models.company import Company
from server.models.fundraising import FundraisingRound, Investor, InvestorPipeline, RoundTerms
from server.models.user import User
from server.models.workspace import WorkspaceMember


@pytest.fixture
def Session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    User.metadata.create_all(engine, tables=[
        User.__table__, Company.__table__, WorkspaceMember.__table__, FundraisingRound.__table__,
        RoundTerms.__table__, Investor.__table__, InvestorPipeline.__table__,
    ])
    S = sessionmaker(bind=engine)
    db = S()
    owner = User(email="owner@brand.in", is_active=True)
    other = User(email="other@brand.in", is_active=True)
    db.add_all([owner, other])
    db.flush()
    db.add(Company(id=1, name="Brand", user_id=owner.id, currency="INR"))
    db.add(Company(id=2, name="Other", user_id=other.id, currency="USD"))
    db.commit()
    db.close()
    return S


def _client(Session, email):
    app = FastAPI()
    app.include_router(fundraising_api.router)

    def _db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    def _user():
        return Session().query(User).filter(User.email == email).one()

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = _user
    return TestClient(app)


def test_new_company_has_an_empty_board(Session):
    body = _client(Session, "owner@brand.in").get("/companies/1/fundraising/pipeline").json()
    assert body["entries"] == []


def test_add_move_and_delete(Session):
    client = _client(Session, "owner@brand.in")
    res = client.post("/companies/1/fundraising/pipeline", json={
        "firm": "  Blume Ventures ", "partner": "A Partner", "check_size": "₹4Cr", "warm_intro": True,
    })
    assert res.status_code == 200, res.text
    entry = res.json()
    assert entry["firm"] == "Blume Ventures" and entry["stage"] == "sourced" and entry["warm_intro"] is True

    db = Session()
    rounds = db.query(FundraisingRound).all()
    assert len(rounds) == 1 and rounds[0].status == "active", "a round is created for the first investor"
    db.close()

    client.post("/companies/1/fundraising/pipeline", json={"firm": "Second", "stage": "dd"})
    db = Session()
    assert db.query(FundraisingRound).count() == 1, "later investors reuse the current round"
    db.close()

    moved = client.patch(f"/companies/1/fundraising/pipeline-board/{entry['id']}", json={"stage": "term_sheet"})
    assert moved.status_code == 200 and moved.json()["stage"] == "term_sheet"

    stages = [e["stage"] for e in client.get("/companies/1/fundraising/pipeline").json()["entries"]]
    assert sorted(stages) == ["dd", "term_sheet"]

    assert client.delete(f"/companies/1/fundraising/pipeline-board/{entry['id']}").status_code == 200
    assert len(client.get("/companies/1/fundraising/pipeline").json()["entries"]) == 1


def test_validation(Session):
    client = _client(Session, "owner@brand.in")
    assert client.post("/companies/1/fundraising/pipeline", json={"firm": "  "}).status_code == 422
    assert client.post("/companies/1/fundraising/pipeline", json={"firm": "X", "stage": "won"}).status_code == 422
    assert client.patch("/companies/1/fundraising/pipeline-board/not-a-uuid", json={"stage": "dd"}).status_code == 404


def test_other_companies_entries_are_invisible(Session):
    owner = _client(Session, "owner@brand.in")
    entry = owner.post("/companies/1/fundraising/pipeline", json={"firm": "Mine"}).json()
    other = _client(Session, "other@brand.in")
    assert other.get("/companies/1/fundraising/pipeline").status_code == 403
    assert other.patch(f"/companies/2/fundraising/pipeline-board/{entry['id']}", json={"stage": "dd"}).status_code == 404
    assert other.delete(f"/companies/2/fundraising/pipeline-board/{entry['id']}").status_code == 404
