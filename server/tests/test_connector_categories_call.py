"""/connectors/categories must hand list_catalog a real user and db session.

It used to call list_catalog(None, False, False, current_user), which put the
user in the company_id slot and left current_user/db as unresolved Depends()
objects, so the route errored. (Carried over from closed PR #3.)
"""
import asyncio

from server.api import connectors


def test_categories_passes_user_and_db(monkeypatch):
    seen = {}

    async def fake_catalog(**kwargs):
        seen.update(kwargs)
        return [{"id": "a", "category": "accounting"}, {"id": "b", "category": "accounting"},
                {"id": "c", "category": "crm"}]

    monkeypatch.setattr(connectors, "list_catalog", fake_catalog)
    user, db = object(), object()
    out = asyncio.run(connectors.list_categories(current_user=user, db=db))

    assert seen["current_user"] is user
    assert seen["db"] is db
    assert seen["company_id"] is None
    assert sorted((c["name"], c["count"]) for c in out) == [("accounting", 2), ("crm", 1)]
