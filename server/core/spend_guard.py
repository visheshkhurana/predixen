"""Per-user and per-company burst limits for AI, simulation, and Truth Scan.

Public beta turns plan caps off, so this in-process window is the spend guard.
It does not read an environment variable and it does not fail open. A rejected
call does not take a slot.

Write routes (POST, PUT, PATCH, DELETE): SPEND_BURST_PER_MINUTE for the user
and, separately, the same number for the company.

Read routes (GET on simulation and Truth Scan): READ_BURST_PER_MINUTE, again
per user and per company, in a different bucket so polling cannot eat the
spend budget.

The company bucket is charged only when this user may access that company
(owner, active workspace member, or platform admin). A stranger who will get
403 or 404 does not consume the other company's budget. Their own user bucket
still counts, so they cannot multiply spend by rotating company ids.

Routes with no company id are per-user only. Public survival-sim has no
account, so the same ceilings are keyed by client IP.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from typing import Optional
from urllib.parse import parse_qs

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Modest burst. The number is the cap, not an environment variable, so a
# one-line change reverts it the same way BETA_ALL_FREE reverts the plan grant.
SPEND_BURST_PER_MINUTE = 20
READ_BURST_PER_MINUTE = 60
SPEND_WINDOW_SECONDS = 60.0
# The middleware reads a JSON body only to find a company id. Anything larger
# is refused. File uploads are not buffered here.
MAX_BUFFERED_BODY_BYTES = 1024 * 1024

_HITS: dict[str, list[float]] = {}
_LOCK = threading.Lock()

_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

_AI_EXACT = {
    "/llm/chat",
    "/llm/quick-chat",
    "/llm/smart-chat",
    "/llm/web-search",
    "/ingest/financials",
    "/ingest/onboarding/extract-deck",
    "/imports/excel",
    "/imports/pdf",
}

_COMPANY_AI = re.compile(r"^/companies/\d+/(?:chat|quick-chat)$")
_COMPANY_LLM = re.compile(
    r"^/companies/\d+/(?:"
    r"ai-graphics/generate|"
    r"board-export/generate(?:-graphic)?|"
    r"doc-generator/generate|"
    r"fundraising/one-pager|"
    r"strategic-diagnosis|"
    r"smart-alerts/(?:evaluate|weekly-briefing)|"
    r"competitors/\d+/scan|"
    r"datasets/termina-(?:pdf|excel)"
    r")$"
)
_DECISION_GENERATE = re.compile(r"^/simulation/(\d+)/decisions/generate$")
_COMPANY_SIM = re.compile(
    r"^/companies/\d+/(?:"
    r"simulate|simulate-multi|simulate-enhanced|simulate-scenarios-enhanced|"
    r"sensitivity-analysis|recommendations|decision/compare|default-scenarios|"
    r"simulation(?:/.*)?"
    r")$"
)
_SCENARIO_SIM = re.compile(
    r"^/scenarios/\d+/(?:simulate|counter-moves|simulation/latest|timeseries)$"
)
_TRUTH_COMPANY = re.compile(r"^/companies/\d+/truth(?:/|$)")
_COMPANY_ID = re.compile(r"/companies/(\d+)(?:/|$)")
_COPILOT_COMPANY = re.compile(r"^/simulation-copilot/(?:prompt|narrative)/(\d+)$")
_MACRO_COMPANY = re.compile(r"^/simulator/(?:macros|recommendations/company)/(\d+)$")
_SCENARIO_ID = re.compile(r"^(?:/scenarios|/simulator/scenarios|/simulations/versions)/(\d+)(?:/|$)")
_ASSUMPTION_ID = re.compile(
    r"^/simulator/(?:sensitivity|recommendations|optimise/constrained)/(\d+)$"
)
_UPLOAD_ID = re.compile(r"^/truth-scan/uploads/([^/]+)")
_DOMAIN_SIM = {"/simulation/scenarios", "/simulation/runs", "/simulation/history"}
# JSON bodies the middleware may read, capped at MAX_BUFFERED_BODY_BYTES.
# Multipart uploads stay on the per-user bucket and are not buffered here.
_JSON_BODY_PATHS = {
    "/truth-scan/from-import-session",
    "/truth-scan/from-dataset",
    "/truth-scan/from-manual-baseline",
    "/simulations/run",
    "/simulations/sensitivity",
    "/simulations/versions",
}
_BODY_COMPANY_PATHS = _JSON_BODY_PATHS | {
    "/ingest/financials",
    "/imports/excel",
    "/imports/pdf",
}
_BODY_SCENARIO_PATHS = {
    "/simulations/run",
    "/simulations/sensitivity",
    "/simulations/versions",
}
_LOOKUP_TABLES = {
    "scenarios": ("scenarios", "id", "int"),
    "assumption_sets": ("assumption_sets", "id", "int"),
    "truth_scan_uploads": ("truth_scan_uploads", "id", "str"),
}


def normalize_path(path: str) -> str:
    """Path FastAPI sees, with one leading /api removed.

    Express strips /api before proxying. Direct callers still send it. Both
    forms share these buckets.
    """
    text_path = (path or "").split("?", 1)[0]
    if len(text_path) > 1:
        text_path = text_path.rstrip("/")
    if text_path == "/api":
        return "/"
    if text_path.startswith("/api/"):
        text_path = text_path[4:]
    return text_path or "/"


def _under(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix + "/")


def _is_llm_write(verb: str, path: str) -> bool:
    """LLM routes opened with the beta grant. GET strategic-diagnosis can spend."""
    matched = bool(
        _COMPANY_LLM.match(path)
        or _DECISION_GENERATE.match(path)
    )
    if not matched:
        return False
    if verb in _WRITE_METHODS:
        return True
    return verb == "GET" and path.endswith("/strategic-diagnosis")


def classify_spend(method: str, path: str) -> Optional[str]:
    """'write', 'read', or None when this request is not a guarded route."""
    verb = (method or "").upper()
    if verb in {"OPTIONS", "HEAD"}:
        return None
    norm = normalize_path(path)
    if _is_llm_write(verb, norm) or (
        verb in _WRITE_METHODS and (norm in _AI_EXACT or _COMPANY_AI.match(norm))
    ):
        return "write"
    if _is_simulation(norm) or _is_truth(norm):
        if verb in _WRITE_METHODS:
            return "write"
        if verb == "GET":
            return "read"
    return None


def _is_simulation(path: str) -> bool:
    if path in _DOMAIN_SIM or path == "/explain-simulation":
        return True
    if _COMPANY_SIM.match(path) or _SCENARIO_SIM.match(path):
        return True
    for prefix in (
        "/simulation/v2",
        "/simulation-copilot",
        "/simulations",
        "/simulator",
        "/survival-sim",
    ):
        if _under(path, prefix):
            return True
    return False


def _is_truth(path: str) -> bool:
    if _TRUTH_COMPANY.match(path):
        return True
    return _under(path, "/truth-scan")


def is_anonymous_spend(path: str) -> bool:
    """Public survival simulator. No user and no company."""
    return _under(normalize_path(path), "/survival-sim")


def needs_body(method: str, path: str) -> bool:
    if (method or "").upper() not in _WRITE_METHODS:
        return False
    norm = normalize_path(path)
    return norm in _JSON_BODY_PATHS


def limit_for(kind: str) -> int:
    if kind == "write":
        return SPEND_BURST_PER_MINUTE
    return READ_BURST_PER_MINUTE


def company_id_from_path(path: str) -> Optional[int]:
    norm = normalize_path(path)
    for pattern in (_COMPANY_ID, _COPILOT_COMPANY, _MACRO_COMPANY):
        match = pattern.search(norm)
        if match:
            return int(match.group(1))
    return None


def company_id_from_query(query_string: str) -> Optional[int]:
    parsed = parse_qs(query_string or "", keep_blank_values=False)
    for key in ("company_id", "companyId"):
        values = parsed.get(key) or []
        if not values:
            continue
        try:
            return int(values[0])
        except (TypeError, ValueError):
            return None
    return None


def company_id_from_body(path: str, body: bytes, content_type: str) -> Optional[int]:
    norm = normalize_path(path)
    if norm not in _BODY_COMPANY_PATHS or not body:
        return None
    kind = (content_type or "").lower()
    if "application/json" in kind or kind == "":
        try:
            payload = json.loads(body)
        except (ValueError, UnicodeError):
            payload = None
        if isinstance(payload, dict):
            for key in ("company_id", "companyId"):
                if key in payload and payload[key] is not None:
                    try:
                        return int(payload[key])
                    except (TypeError, ValueError):
                        return None
        if "application/json" in kind:
            return None
    text_body = body.decode("utf-8", errors="ignore")
    multipart = re.search(
        r'name=["\'](?:companyId|company_id)["\'][^\r\n]*\r?\n\r?\n(\d+)',
        text_body,
    )
    if multipart:
        return int(multipart.group(1))
    form = re.search(r"(?:^|&)(?:companyId|company_id)=(\d+)(?:&|$)", text_body)
    if form:
        return int(form.group(1))
    return None


def lookup_target(method: str, path: str, body: Optional[bytes], content_type: str) -> Optional[tuple[str, str]]:
    """(table kind, resource id) when the company id is not on the request."""
    norm = normalize_path(path)
    decision = _DECISION_GENERATE.match(norm)
    if decision:
        return ("simulation_runs", decision.group(1))
    scenario = _SCENARIO_ID.search(norm)
    if scenario:
        return ("scenarios", scenario.group(1))
    assumption = _ASSUMPTION_ID.search(norm)
    if assumption and "/results" not in norm:
        return ("assumption_sets", assumption.group(1))
    upload = _UPLOAD_ID.search(norm)
    if upload:
        return ("truth_scan_uploads", upload.group(1))
    if (method or "").upper() in _WRITE_METHODS and norm in _BODY_SCENARIO_PATHS and body:
        try:
            payload = json.loads(body)
        except (ValueError, UnicodeError):
            payload = None
        if isinstance(payload, dict) and payload.get("scenario_id") is not None:
            return ("scenarios", str(payload["scenario_id"]))
    return None


def _engine():
    from server.core.db import engine
    return engine


def lookup_company_id(kind: str, resource_id: str) -> Optional[int]:
    if kind == "simulation_runs":
        statement = text(
            "SELECT s.company_id FROM simulation_runs r "
            "JOIN scenarios s ON s.id = r.scenario_id WHERE r.id = :id"
        )
        id_type = "int"
    else:
        spec = _LOOKUP_TABLES.get(kind)
        if spec is None:
            return None
        table, id_column, id_type = spec
        statement = text(f"SELECT company_id FROM {table} WHERE {id_column} = :id")
    try:
        value = int(resource_id) if id_type == "int" else str(resource_id)
    except (TypeError, ValueError):
        return None
    try:
        engine = _engine()
        with engine.connect() as conn:
            row = conn.execute(statement, {"id": value}).fetchone()
        if row is None or row[0] is None:
            return None
        return int(row[0])
    except Exception:
        logger.warning("spend guard company lookup failed for %s", kind, exc_info=True)
        return None


def user_may_charge_company(user_id: int, company_id: int) -> bool:
    """True when this user is allowed to spend against the company bucket.

    A failed lookup returns False. The user bucket still applies. The company
    bucket is left alone so a database error cannot bill a stranger's traffic
    to someone else's company.
    """
    if user_id == -1:
        return True
    try:
        engine = _engine()
        with engine.connect() as conn:
            owned = conn.execute(
                text("SELECT 1 FROM companies WHERE id = :cid AND user_id = :uid"),
                {"cid": company_id, "uid": user_id},
            ).first()
            if owned:
                return True
            member = conn.execute(
                text(
                    "SELECT 1 FROM workspace_members "
                    "WHERE company_id = :cid AND user_id = :uid AND status = 'active'"
                ),
                {"cid": company_id, "uid": user_id},
            ).first()
            if member:
                return True
            from server.core.config import settings

            admin_email = (settings.ADMIN_MASTER_EMAIL or "").lower().strip()
            if admin_email:
                admin = conn.execute(
                    text(
                        "SELECT 1 FROM users WHERE id = :uid "
                        "AND lower(email) = :email AND is_email_verified = :verified"
                    ),
                    {"uid": user_id, "email": admin_email, "verified": True},
                ).first()
                if admin:
                    return True
        return False
    except Exception:
        logger.warning("spend guard membership check failed", exc_info=True)
        return False


def user_id_from_request(request: Request) -> Optional[int]:
    from server.core.security import AUTH_COOKIE_NAME, decode_token

    token = None
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    try:
        return int(payload.get("sub"))
    except (TypeError, ValueError):
        return None


def spend_burst_limited(
    keys: list[str],
    *,
    limit: int,
    window: float = SPEND_WINDOW_SECONDS,
    now: Optional[float] = None,
    store: Optional[dict] = None,
) -> tuple[bool, int, Optional[str]]:
    """True when any key is over the window. A rejected call does not count.

    Every key is checked before any key is incremented, under one lock.
    """
    if not keys:
        return False, 0, None
    bucket = _HITS if store is None else store
    stamp = time.monotonic() if now is None else float(now)
    with _LOCK:
        # Drop idle keys. /survival-sim is keyed per IP, and those keys would
        # otherwise stay in this process forever.
        stale = [
            key
            for key, hits in bucket.items()
            if not hits or stamp - hits[-1] >= window
        ]
        for key in stale:
            del bucket[key]
        trimmed = {
            key: [seen for seen in bucket.get(key, []) if stamp - seen < window]
            for key in keys
        }
        blocked_key = None
        retry = 0
        for key in keys:
            hits = trimmed[key]
            if len(hits) >= limit:
                blocked_key = key
                retry = 1
                if hits:
                    retry = max(1, int(window - (stamp - min(hits))) + 1)
                break
        if blocked_key is not None:
            for key, hits in trimmed.items():
                if hits or key in bucket:
                    bucket[key] = hits
            return True, retry, blocked_key
        for key, hits in trimmed.items():
            hits.append(stamp)
            bucket[key] = hits
        return False, 0, None


def reset_spend_buckets() -> None:
    with _LOCK:
        _HITS.clear()


def _client_key(request: Request) -> str:
    from server.middleware.rate_limiter import client_ip, socket_host

    return client_ip(request.headers, socket_host(request)) or "unknown"


def _dimension(blocked_key: Optional[str]) -> str:
    if not blocked_key:
        return "user"
    return blocked_key.split(":", 1)[0]


class SpendGuardMiddleware:
    """ASGI middleware. Verifies the token before any body is read.

    Unauthenticated callers are rejected without buffering. A verified caller
    whose JSON body is over MAX_BUFFERED_BODY_BYTES gets 413. File uploads are
    not read here.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        method = scope.get("method", "GET")
        path = scope.get("path", "")
        kind = classify_spend(method, path)
        if kind is None:
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        try:
            user_id = user_id_from_request(request)
        except Exception:
            logger.exception("spend guard token verification failed")
            user_id = None
        anonymous = is_anonymous_spend(path)
        if user_id is None and not anonymous:
            await _unauthorized()(scope, receive, send)
            return

        body = None
        receive_for_app = receive
        if needs_body(method, path):
            declared = _content_length(scope)
            if declared is not None and declared > MAX_BUFFERED_BODY_BYTES:
                await _payload_too_large()(scope, receive, send)
                return
            body, receive_for_app, too_large = await _buffer_body(
                receive, MAX_BUFFERED_BODY_BYTES
            )
            if too_large:
                await _payload_too_large()(scope, receive_for_app, send)
                return

        try:
            blocked, retry_after, limit, dimension = _decide(
                scope, method, path, kind, body, user_id
            )
        except Exception:
            logger.exception("spend guard failed closed")
            response = _too_many(SPEND_BURST_PER_MINUTE, 60, "user")
            await response(scope, receive_for_app, send)
            return

        if blocked:
            response = _too_many(limit, retry_after, dimension)
            await response(scope, receive_for_app, send)
            return
        await self.app(scope, receive_for_app, send)


def _decide(scope, method: str, path: str, kind: str, body: Optional[bytes], user_id: Optional[int]):
    request = Request(scope)
    company_id = company_id_from_path(path)
    if company_id is None:
        company_id = company_id_from_query(scope.get("query_string", b"").decode("latin-1"))
    content_type = request.headers.get("content-type", "")
    if company_id is None and body is not None:
        company_id = company_id_from_body(path, body, content_type)
    if company_id is None:
        target = lookup_target(method, path, body, content_type)
        if target is not None:
            company_id = lookup_company_id(target[0], target[1])

    keys = []
    if user_id is not None:
        keys.append(f"user:{user_id}:{kind}")
    else:
        keys.append(f"ip:{_client_key(request)}:{kind}")
    if company_id is not None and user_id is not None and user_may_charge_company(user_id, company_id):
        keys.append(f"company:{company_id}:{kind}")

    limit = limit_for(kind)
    blocked, retry_after, blocked_key = spend_burst_limited(keys, limit=limit)
    return blocked, retry_after, limit, _dimension(blocked_key)


def _content_length(scope) -> Optional[int]:
    for name, value in scope.get("headers") or []:
        if name.lower() == b"content-length":
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
    return None


def _unauthorized() -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"detail": "Not authenticated"},
        headers={"WWW-Authenticate": "Bearer"},
    )


def _payload_too_large() -> JSONResponse:
    return JSONResponse(
        status_code=413,
        content={"detail": "Request body exceeds 1 MB."},
    )


def _too_many(limit: int, retry_after: int, dimension: str) -> JSONResponse:
    retry = max(1, int(retry_after))
    return JSONResponse(
        status_code=429,
        content={
            "detail": f"Rate limit exceeded. Maximum {limit} requests per minute.",
            "retry_after": retry,
            "dimension": dimension,
        },
        headers={"Retry-After": str(retry)},
    )


async def _buffer_body(receive, limit: int):
    chunks = []
    other = None
    total = 0
    too_large = False
    while True:
        message = await receive()
        if message["type"] != "http.request":
            other = message
            break
        piece = message.get("body", b"") or b""
        if total + len(piece) > limit:
            too_large = True
            break
        total += len(piece)
        chunks.append(piece)
        if not message.get("more_body", False):
            break
    body = b"".join(chunks)
    state = {"phase": 0, "other": other}

    async def replay():
        if state["phase"] == 0:
            state["phase"] = 1
            if state["other"] is not None and not body:
                return state["other"]
            return {"type": "http.request", "body": body, "more_body": False}
        if state["other"] is not None:
            queued = state["other"]
            state["other"] = None
            return queued
        return await receive()

    return body, replay, too_large
