from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from server.core.db import Base


class SimulationAccuracy(Base):
    __tablename__ = "simulation_accuracy"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    simulation_run_id = Column(Integer, ForeignKey("simulation_runs.id"), nullable=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=True, index=True)
    prediction_month = Column(Integer, nullable=False)
    predicted_revenue = Column(Float, nullable=True)
    actual_revenue = Column(Float, nullable=True)
    predicted_burn = Column(Float, nullable=True)
    actual_burn = Column(Float, nullable=True)
    predicted_cash = Column(Float, nullable=True)
    actual_cash = Column(Float, nullable=True)
    predicted_churn = Column(Float, nullable=True)
    actual_churn = Column(Float, nullable=True)
    variance_pct_json = Column(JSONB, nullable=True)
    accuracy_score = Column(Float, nullable=True)
    computed_at = Column(DateTime, default=datetime.utcnow)


class CalibrationBias(Base):
    __tablename__ = "calibration_biases"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    metric = Column(String(50), nullable=False)
    bias_pct = Column(Float, nullable=False, default=0.0)
    sample_count = Column(Integer, default=0)
    confidence = Column(String(20), default="low")
    is_active = Column(Integer, default=1)
    applied_at = Column(DateTime, nullable=True)
    computed_at = Column(DateTime, default=datetime.utcnow)
