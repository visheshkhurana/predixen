from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from datetime import datetime
from server.core.db import Base
import enum


class TeamMemberType(str, enum.Enum):
    FULL_TIME = "full_time"
    CONTRACTOR = "contractor"
    INTERN = "intern"


class TeamMemberStatus(str, enum.Enum):
    ACTIVE = "active"
    INTERVIEWING = "interviewing"
    OFFER_SENT = "offer_sent"
    ONBOARDING = "onboarding"
    OFFBOARDED = "offboarded"


class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    role = Column(String, nullable=False)
    type = Column(String, nullable=False, default=TeamMemberType.FULL_TIME.value)
    department = Column(String, nullable=False, default="Engineering")
    status = Column(String, nullable=False, default=TeamMemberStatus.ACTIVE.value)
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)
    salary_range = Column(Text, nullable=True)
    skills = Column(JSON, nullable=True, default=list)
    github_url = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
