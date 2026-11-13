"""Recipient lists for the ops-only update scripts (send_update_v*.py etc.).

Addresses are never committed. They come from, in order:

1. ``RECIPIENTS`` env var: comma-separated entries, each ``email`` or
   ``Name <email>``.
2. ``RECIPIENTS_FILE`` env var, or ``server/email/recipients.local.txt``
   (gitignored). One entry per line: ``email[,name[,id]]``; blank lines and
   ``#`` comments are ignored.

Each entry becomes ``{"email", "name", "id"}``, the shape the scripts expect.
If nothing is configured an empty list is returned and a hint is printed to
stderr, so the scripts import cleanly and simply send nothing.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_FILE = Path(__file__).with_name("recipients.local.txt")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_NAMED_RE = re.compile(r"^\s*(?P<name>[^<]*?)\s*<(?P<email>[^>]+)>\s*$")


def _make(email: str, name: Optional[str] = None, rid: Optional[str] = None,
          default_name: str = "there") -> Dict[str, str]:
    email = email.strip()
    if not _EMAIL_RE.match(email):
        raise ValueError(f"invalid recipient email: {email!r}")
    local = email.split("@", 1)[0]
    return {
        "email": email,
        "name": (name or "").strip() or default_name,
        "id": (rid or "").strip() or re.sub(r"[^A-Za-z0-9]+", "_", local).strip("_").lower(),
    }


def _parse_env(value: str, default_name: str) -> List[Dict[str, str]]:
    out = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        m = _NAMED_RE.match(part)
        if m:
            out.append(_make(m.group("email"), m.group("name"), default_name=default_name))
        else:
            out.append(_make(part, default_name=default_name))
    return out


def _parse_file(path: Path, default_name: str) -> List[Dict[str, str]]:
    out = []
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        fields = [f.strip() for f in line.split(",")]
        out.append(_make(fields[0], fields[1] if len(fields) > 1 else None,
                         fields[2] if len(fields) > 2 else None, default_name=default_name))
    return out


def load_recipients(default_name: str = "there") -> List[Dict[str, str]]:
    env_value = os.environ.get("RECIPIENTS", "").strip()
    if env_value:
        return _parse_env(env_value, default_name)
    path = Path(os.environ.get("RECIPIENTS_FILE") or DEFAULT_FILE)
    if path.is_file():
        return _parse_file(path, default_name)
    print(
        f"[recipients] no recipients configured: set RECIPIENTS or create {path}",
        file=sys.stderr,
    )
    return []


def load_recipient_emails() -> List[str]:
    return [r["email"] for r in load_recipients()]
