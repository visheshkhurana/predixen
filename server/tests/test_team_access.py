"""Invited teammates can open the company; viewers can read but not change it."""
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.core import company_access as ca


@pytest.fixture
def world():
    import server.models  # noqa: F401
    from server.models.company import Company
    from server.models.user import User
    from server.models.workspace import WorkspaceMember
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    User.metadata.create_all(engine, tables=[User.__table__, Company.__table__, WorkspaceMember.__table__])
    db = sessionmaker(bind=engine)()
    users = {}
    for name in ("owner", "editor", "viewer", "pending", "stranger"):
        u = User(email=f"{name}@example.com", password_hash="x", display_name=name)
        db.add(u)
        db.flush()
        users[name] = u
    company = Company(name="Masala Box", user_id=users["owner"].id)
    other = Company(name="Stranger Co", user_id=users["stranger"].id)
    db.add_all([company, other])
    db.flush()
    db.add_all([
        WorkspaceMember(company_id=company.id, user_id=users["editor"].id, role="editor", status="active"),
        WorkspaceMember(company_id=company.id, user_id=users["viewer"].id, role="viewer", status="active"),
        WorkspaceMember(company_id=company.id, user_id=users["pending"].id, role="editor", status="pending"),
    ])
    db.commit()
    yield db, users, company, other, Company
    db.close()
    engine.dispose()


def _as_request(method, path):
    return ca._REQUEST.set((method, path))


def _visible(db, Company, user):
    return {c.name for c in db.query(Company).filter(ca.company_access_clause(user)).all()}


def test_members_see_the_company_and_strangers_do_not(world):
    db, users, company, other, Company = world
    t = _as_request("GET", f"/companies")
    try:
        assert _visible(db, Company, users["owner"]) == {"Masala Box"}
        assert _visible(db, Company, users["editor"]) == {"Masala Box"}
        assert _visible(db, Company, users["viewer"]) == {"Masala Box"}
        assert _visible(db, Company, users["pending"]) == set()
        assert _visible(db, Company, users["stranger"]) == {"Stranger Co"}
    finally:
        ca._REQUEST.reset(t)


def test_viewer_is_read_only_in_both_checks(world):
    db, users, company, _other, Company = world
    t = _as_request("POST", f"/companies/{company.id}/financials")
    try:
        assert _visible(db, Company, users["viewer"]) == set()
        assert _visible(db, Company, users["editor"]) == {"Masala Box"}
        with pytest.raises(HTTPException) as e:
            ca.get_user_company(db, company.id, users["viewer"])
        assert e.value.status_code == 403
        assert "view-only" in e.value.detail
        assert ca.get_user_company(db, company.id, users["editor"]).id == company.id
        assert ca.get_user_company(db, company.id, users["owner"]).id == company.id
    finally:
        ca._REQUEST.reset(t)


def test_viewer_can_read_ask_copilot_and_export(world):
    db, users, company, _other, Company = world
    for method, path in (
        ("GET", f"/companies/{company.id}/metrics"),
        ("POST", f"/companies/{company.id}/chat"),
        ("POST", f"/api/companies/{company.id}/quick-chat"),
        ("POST", "/export/pdf"),
        ("POST", f"/companies/{company.id}/board-export/pdf"),
    ):
        t = _as_request(method, path)
        try:
            assert ca.get_user_company(db, company.id, users["viewer"]).id == company.id, path
            assert _visible(db, Company, users["viewer"]) == {"Masala Box"}, path
        finally:
            ca._REQUEST.reset(t)


def test_stranger_and_pending_member_are_refused(world):
    db, users, company, _other, _Company = world
    for name in ("stranger", "pending"):
        with pytest.raises(HTTPException) as e:
            ca.get_user_company(db, company.id, users[name])
        assert e.value.status_code == 403


def test_no_request_context_behaves_like_a_read(world):
    db, users, company, _other, _Company = world
    assert ca._REQUEST.get() is None
    assert ca.get_user_company(db, company.id, users["viewer"]).id == company.id
