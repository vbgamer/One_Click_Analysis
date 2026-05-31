from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Boolean, Text, Float
from sqlalchemy.orm import relationship
from database import Base
import datetime
import enum

class JobStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"

class CreditRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="user")        # "user" or "admin"
    credits = Column(Integer, default=1000)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    jobs = relationship("Job", back_populates="owner")
    reports = relationship("Report", back_populates="owner")
    credit_requests = relationship("CreditRequest", back_populates="requester")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    filename = Column(String)
    status = Column(String, default=JobStatus.UPLOADED)
    report_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="jobs")
    report = relationship("Report", back_populates="job", uselist=False)
    ai_result = relationship("AIResult", back_populates="job", uselist=False)

class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, index=True)
    job_id = Column(String, ForeignKey("jobs.id"), unique=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    report_html_url = Column(String)
    metadata_json = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="reports")
    job = relationship("Job", back_populates="report")

class CreditRequest(Base):
    __tablename__ = "credit_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount_requested = Column(Integer, default=500)
    status = Column(String, default=CreditRequestStatus.PENDING)
    note = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    requester = relationship("User", back_populates="credit_requests")

# ── NEW: AI Intelligence Results ────────────────────────────────────────────
class AIResult(Base):
    """Stores the full structured AI analysis result for a job."""
    __tablename__ = "ai_results"

    id = Column(String, primary_key=True, index=True)  # UUID
    job_id = Column(String, ForeignKey("jobs.id"), unique=True)
    status = Column(String, default="pending")          # pending / running / done / failed
    results_json = Column(Text, nullable=True)          # Full JSON output of pipeline
    schema_json = Column(String, nullable=True)         # Detected schema
    data_quality_score = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    anomaly_count = Column(Integer, nullable=True)
    recommendation_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    job = relationship("Job", back_populates="ai_result")

# ── NEW: Conversational Message History ─────────────────────────────────────
class ConversationMessage(Base):
    """Stores conversational AI chat history per job."""
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, ForeignKey("jobs.id"))
    role = Column(String)           # "user" or "assistant"
    content = Column(Text)
    intent = Column(String, nullable=True)   # detected query intent
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
