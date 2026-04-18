# app/schemas_anomaly.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date

class EarningsRecord(BaseModel):
    date: date
    gross_earned: float
    platform_deductions: float
    net_received: float
    effective_hourly_rate: Optional[float] = None
    hours_worked: Optional[float] = None

class AnomalyRequest(BaseModel):
    earnings_history: Optional[List[EarningsRecord]] = None
    worker_id: Optional[int] = None

class AnomalyDetail(BaseModel):
    type: str
    severity: str
    description: str
    affected_period: str

class AnomalyResponse(BaseModel):
    has_anomalies: bool
    anomalies: List[AnomalyDetail]
    explanation: str