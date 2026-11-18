"""Goals API: founders can save, edit and delete their own goals, and only theirs."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.api import goals as goals_api
from server.core.db import get_db
from server.core.security import get_current_user
from server.models.company import Company
from server.models.goal import CompanyGoal
from server.models.user import User
from server.models.workspace import WorkspaceMember


@pytest.fixture
def Session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    User.metadata.create_all(
        engine,
        tables=[User.__table__, Company.__table__, CompanyGoal.__table__, WorkspaceMember.__table__],
    )
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
    app.include_router(goals_api.router)

    def _db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    def _user():
        s = Session()
        return s.query(User).filter(User.email == email).one()

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = _user
    return TestClient(app)


def test_create_list_update_delete_round_trip(Session):
    client = _client(Session, "owner@brand.in")
    assert client.get("/companies/1/goals").json() == {"goals": []}

    res = client.post(
        "/companies/1/goals",
        json={"title": "  Hit ₹50L MRR ", "unit": "currency", "target_value": 5_000_000, "deadline": "2027-03-31"},
    )
    assert res.status_code == 201, res.text
    goal = res.json()
    assert goal["title"] == "Hit ₹50L MRR"
    assert goal["status"] == "on_track"
    assert goal["deadline"] == "2027-03-31"

    listed = client.get("/companies/1/goals").json()["goals"]
    assert [g["id"] for g in listed] == [goal["id"]]

    res = client.patch(f"/companies/1/goals/{goal['id']}", json={"current_value": 3_200_000, "status": "at_risk"})
    assert res.status_code == 200, res.text
    assert res.json()["current_value"] == 3_200_000
    assert res.json()["status"] == "at_risk"
    assert res.json()["target_value"] == 5_000_000, "a partial update keeps the other fields"

    assert client.delete(f"/companies/1/goals/{goal['id']}").json() == {"deleted": True}
    assert client.get("/companies/1/goals").json() == {"goals": []}


def test_blank_title_and_bad_status_are_rejected(Session):
    client = _client(Session, "owner@brand.in")
    assert client.post("/companies/1/goals", json={"title": "   "}).status_code == 422
    assert client.post("/companies/1/goals", json={"title": "x", "status": "maybe"}).status_code == 422


def test_cannot_read_or_write_another_companys_goals(Session):
    owner = _client(Session, "owner@brand.in")
    goal = owner.post("/companies/1/goals", json={"title": "Raise seed"}).json()

    other = _client(Session, "other@brand.in")
    assert other.get("/companies/1/goals").status_code in (403, 404)
    assert other.post("/companies/1/goals", json={"title": "x"}).status_code in (403, 404)
    # Goal ids are scoped to the company in the path too.
    assert other.patch(f"/companies/2/goals/{goal['id']}", json={"status": "done"}).status_code == 404
    assert other.delete(f"/companies/2/goals/{goal['id']}").status_code == 404
