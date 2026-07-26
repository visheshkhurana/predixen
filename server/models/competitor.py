"""Competition-tracking models: competitors a founder watches, and the signals
(news / blog posts / social mentions) collected about them."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from datetime import datetime

from server.core.db import Base


class Competitor(Base):
    """A competitor a founder wants to keep an eye on."""
    __tablename__ = "competitors"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)

    name = Column(String, nullable=False)
    website = Column(String, nullable=True)
    blog_url = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    x_handle = Column(String, nullable=True)          # handle ("@acme") or full URL
    other_links = Column(JSON, nullable=True)          # [{"label": str, "url": str}]

    description = Column(Text, nullable=True)           # what they do
    notes = Column(Text, nullable=True)                 # founder's own notes

    last_scanned_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CompetitorSignal(Base):
    """A single tracked update about a competitor (news article, blog post,
    social mention, etc.), gathered via web search."""
    __tablename__ = "competitor_signals"

    id = Column(Integer, primary_key=True, index=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)

    source_type = Column(String, nullable=False, default="web")  # news | blog | linkedin | x | web
    title = Column(String, nullable=True)
    url = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    sentiment = Column(String, nullable=True)           # positive | neutral | negative
    impact = Column(Text, nullable=True)                 # short "why this matters to you"
    published_at = Column(DateTime, nullable=True)       # best-effort article date

    created_at = Column(DateTime, default=datetime.utcnow)
