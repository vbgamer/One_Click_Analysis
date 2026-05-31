from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserBase(BaseModel):
    email: str
    name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class User(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: str
    credits: int
    created_at: datetime

class JobBase(BaseModel):
    pass

class Job(JobBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    filename: str
    status: str
    report_url: Optional[str] = None
    created_at: datetime
    user_id: int

class Report(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    job_id: str
    report_html_url: str
    created_at: datetime

class ChatRequest(BaseModel):
    job_id: str
    message: str

class LayoutItem(BaseModel):
    i: str
    x: int
    y: int
    w: int
    h: int

class CustomReportRequest(BaseModel):
    title: str
    selected_charts: List[str]
    layout: List[LayoutItem] = []
    metadata: Dict[str, Any] = {}

# --- Credit Request Schemas ---
class CreditRequestCreate(BaseModel):
    amount_requested: int = 500
    note: Optional[str] = None

class CreditRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    amount_requested: int
    status: str
    note: Optional[str] = None
    created_at: datetime

# --- Admin Schemas ---
class AdminCreditUpdate(BaseModel):
    credits: int

class AdminCreditAction(BaseModel):
    action: str  # "approve" or "reject"

# ── NEW: AI Intelligence Schemas ─────────────────────────────────────────────

class AIResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    job_id: str
    status: str
    data_quality_score: Optional[float] = None
    confidence_score: Optional[float] = None
    anomaly_count: Optional[int] = None
    recommendation_count: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

class AIResultFull(AIResultOut):
    results_json: Optional[str] = None
    detected_schema_json: Optional[str] = None  # renamed from schema_json to avoid Pydantic shadowing

class AIQueryRequest(BaseModel):
    question: str
    conversation_history: Optional[List[Dict[str, str]]] = None

class AIQueryResponse(BaseModel):
    answer: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    data: Optional[Dict[str, Any]] = None
    visualization: Optional[Dict[str, Any]] = None

class ConversationMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    job_id: str
    role: str
    content: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    created_at: datetime

class SettlementRequest(BaseModel):
    job_id: str

class ForecastRequest(BaseModel):
    job_id: str
    periods: int = 30

class AnomalyRequest(BaseModel):
    job_id: str

class RecommendationRequest(BaseModel):
    job_id: str
