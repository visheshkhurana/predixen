from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from server.core.db import Base


class Conversation(Base):
    """Enhanced conversation model for cross-session memory and shortcuts."""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=True)
    last_scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=True)
    context_metadata = Column(JSON, nullable=True, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    company = relationship("Company", back_populates="conversations")
    user = relationship("User", back_populates="conversations")
    messages = relationship("ConversationMessage", back_populates="conversation", order_by="ConversationMessage.created_at")
    recommendations = relationship("ConversationRecommendation", back_populates="conversation")


class ConversationMessage(Base):
    """Individual message in a conversation with rich metadata."""
    __tablename__ = "conversation_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    intent_type = Column(String, nullable=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=True)
    simulation_id = Column(Integer, nullable=True)
    chart_data = Column(JSON, nullable=True)
    message_metadata = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    conversation = relationship("Conversation", back_populates="messages")


class ConversationRecommendation(Base):
    """Recommendations generated during conversations with feedback tracking."""
    __tablename__ = "conversation_recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    message_id = Column(Integer, ForeignKey("conversation_messages.id"), nullable=True)
    recommendation_type = Column(String, nullable=False)
    recommendation_text = Column(Text, nullable=False)
    priority = Column(Integer, default=0)
    context_data = Column(JSON, nullable=True)
    feedback = Column(String, nullable=True)
    feedback_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    conversation = relationship("Conversation", back_populates="recommendations")
