# app/schemas_earnings.py
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

class EarningsLogCreate(BaseModel):
    platform: str = Field(..., min_length=1, max_length=100)
    date: date
    hours_worked: float = Field(..., gt=0, le=24)
    gross_earned: Decimal = Field(..., ge=0)
    platform_deductions: Decimal = Field(..., ge=0)
    net_received: Decimal = Field(..., ge=0)
    notes: Optional[str] = None
    
    @field_validator('net_received')
    @classmethod
    def validate_net(cls, v: Decimal, info) -> Decimal:
        gross = info.data.get('gross_earned', 0)
        deductions = info.data.get('platform_deductions', 0)
        if gross and deductions:
            expected = gross - deductions
            if abs(v - expected) > Decimal('0.01'):
                raise ValueError('Net received should equal gross earned minus platform deductions')
        return v

class EarningsLogUpdate(BaseModel):
    platform: Optional[str] = None
    date: Optional['date'] = None
    hours_worked: Optional[float] = None
    gross_earned: Optional[Decimal] = None
    platform_deductions: Optional[Decimal] = None
    net_received: Optional[Decimal] = None
    notes: Optional[str] = None

class EarningsLogResponse(BaseModel):
    id: int
    worker_id: int
    platform: str
    date: date
    hours_worked: float
    gross_earned: Decimal
    platform_deductions: Decimal
    net_received: Decimal
    effective_hourly_rate: Optional[Decimal]
    notes: Optional[str]
    created_at: datetime
    verification_status: Optional[str] = None
    
    class Config:
        from_attributes = True

class VerificationResponse(BaseModel):
    id: int
    earnings_log_id: int
    verifier_id: int
    status: str
    verifier_notes: Optional[str]
    verified_at: datetime
    
    class Config:
        from_attributes = True

class VerificationUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|confirmed|discrepancy|unverifiable)$")
    notes: Optional[str] = None

class CSVUploadResponse(BaseModel):
    created_count: int
    errors: List[dict]
    message: str