"""Persistent access-token revocation.

Access tokens are stateless JWTs that live for ACCESS_TOKEN_EXPIRE_MINUTES, so
ending a session needs a record the auth dependency can check. Two shapes:

- RevokedAccessToken: one token (by jti), written on logout. Kept until the
  token would have expired anyway.
- UserSessionCutoff: every token a user was issued before ``revoked_before``,
  written on password reset and suspension.

Both tables are created idempotently at boot (see server/main.py), the same
way as the competition-tracking tables, so they work with CREATE_SCHEMA=false.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from server.core.db import Base


class RevokedAccessToken(Base):
    __tablename__ = "revoked_access_tokens"

    jti = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)


class UserSessionCutoff(Base):
    __tablename__ = "user_session_cutoffs"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    revoked_before = Column(DateTime, nullable=False)
