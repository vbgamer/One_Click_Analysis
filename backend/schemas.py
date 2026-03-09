
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
import enum

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
    username: str # Use email as username
    password: str

class User(UserBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class JobBase(BaseModel):
    pass

class Job(JobBase):
    id: str
    filename: str
    status: str
    report_url: Optional[str]
    created_at: datetime
    user_id: int

    class Config:
        orm_mode = True

class Report(BaseModel):
    id: str
    job_id: str
    report_html_url: str
    created_at: datetime

    class Config:
        orm_mode = True

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


