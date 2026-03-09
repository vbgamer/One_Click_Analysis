from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from database import Base
import datetime
import enum

class JobStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    jobs = relationship("Job", back_populates="owner")
    reports = relationship("Report", back_populates="owner")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True) # UUID
    user_id = Column(Integer, ForeignKey("users.id"))
    filename = Column(String)
    status = Column(String, default=JobStatus.UPLOADED) # Start as uploaded
    report_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="jobs")
    report = relationship("Report", back_populates="job", uselist=False)

class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, index=True) # UUID
    job_id = Column(String, ForeignKey("jobs.id"), unique=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    report_html_url = Column(String)
    metadata_json = Column(String, nullable=True) # Store JSON string of metadata
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="reports")
    job = relationship("Job", back_populates="report")
