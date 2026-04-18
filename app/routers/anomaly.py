# app/routers/anomaly.py - COMPLETE FIXED VERSION
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime
import statistics
import logging

from app.database import get_db
from app.auth import get_current_active_user
from app.models import User, EarningsLog, UserRole
from app.schemas_anomaly import AnomalyRequest, AnomalyResponse, AnomalyDetail

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/anomaly", tags=["Anomaly Detection"])

def detect_anomalies(earnings_history: List[Dict[str, Any]]) -> List[AnomalyDetail]:
    """Detect anomalies in earnings data"""
    anomalies = []
    
    if len(earnings_history) < 3:
        return anomalies
    
    # Extract values with safe None handling
    net_earnings = []
    hourly_rates = []
    deductions_percent = []
    
    for e in earnings_history:
        # Net earnings
        net = e.get('net_received')
        if net is not None:
            net_earnings.append(float(net))
        
        # Hourly rates - safe handling
        hourly = e.get('effective_hourly_rate')
        if hourly is not None and float(hourly) > 0:
            hourly_rates.append(float(hourly))
        
        # Deductions percentage
        gross = e.get('gross_earned')
        deductions = e.get('platform_deductions')
        if gross is not None and deductions is not None and float(gross) > 0:
            deductions_percent.append((float(deductions) / float(gross)) * 100)
    
    # Detect sudden income drop (>20%)
    if len(net_earnings) >= 2:
        recent_avg = statistics.mean(net_earnings[-3:]) if len(net_earnings) >= 3 else net_earnings[-1]
        previous_avg = statistics.mean(net_earnings[:-3]) if len(net_earnings) >= 4 else net_earnings[0]
        
        if previous_avg > 0:
            drop_percentage = ((previous_avg - recent_avg) / previous_avg) * 100
            if drop_percentage > 20:
                anomalies.append(AnomalyDetail(
                    type="income_drop",
                    severity="high",
                    description=f"Your income has dropped by {drop_percentage:.1f}% compared to previous period. This could indicate platform changes or reduced work opportunities.",
                    affected_period="last_30_days"
                ))
    
    # Detect unusually high deductions
    if len(deductions_percent) > 1:
        mean_deductions = statistics.mean(deductions_percent)
        std_deductions = statistics.stdev(deductions_percent) if len(deductions_percent) > 1 else 0
        latest_deduction = deductions_percent[-1]
        
        if std_deductions > 0 and latest_deduction > mean_deductions + (2 * std_deductions):
            anomalies.append(AnomalyDetail(
                type="high_deductions",
                severity="medium",
                description=f"Your latest platform deductions ({latest_deduction:.1f}%) are significantly higher than your average ({mean_deductions:.1f}%). Consider reviewing your earnings breakdown.",
                affected_period="current_period"
            ))
    
    # Detect low hourly rate
    if len(hourly_rates) > 1:
        mean_rate = statistics.mean(hourly_rates)
        latest_rate = hourly_rates[-1]
        
        if latest_rate < mean_rate * 0.7:
            anomalies.append(AnomalyDetail(
                type="low_hourly_rate",
                severity="medium",
                description=f"Your effective hourly rate (₨{latest_rate:.2f}) is 30% below your average (₨{mean_rate:.2f}). This might indicate less efficient hours or platform commission changes.",
                affected_period="current_period"
            ))
    
    return anomalies

@router.post("/detect", response_model=AnomalyResponse)
async def detect_earnings_anomalies(
    request: AnomalyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Detect anomalies in worker's earnings history.
    
    Judges can call this endpoint directly with a crafted payload.
    """
    
    # If worker_id provided and caller is advocate/admin, fetch from DB
    if request.worker_id and current_user.role in [UserRole.ADMIN, UserRole.ADVOCATE]:
        earnings = db.query(EarningsLog).filter(
            EarningsLog.worker_id == request.worker_id
        ).order_by(EarningsLog.date).all()
        
        earnings_history = [
            {
                "date": e.date.isoformat(),
                "gross_earned": float(e.gross_earned),
                "platform_deductions": float(e.platform_deductions),
                "net_received": float(e.net_received),
                "effective_hourly_rate": float(e.effective_hourly_rate) if e.effective_hourly_rate else None,
                "hours_worked": float(e.hours_worked)
            }
            for e in earnings
        ]
    elif request.earnings_history:
        # Convert Pydantic models to dict with safe None handling
        earnings_history = []
        for e in request.earnings_history:
            earnings_history.append({
                "date": e.date.isoformat(),
                "gross_earned": float(e.gross_earned),
                "platform_deductions": float(e.platform_deductions),
                "net_received": float(e.net_received),
                "effective_hourly_rate": float(e.effective_hourly_rate) if e.effective_hourly_rate else None,
                "hours_worked": float(e.hours_worked) if e.hours_worked else 0
            })
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No earnings history provided. Provide either earnings_history array or worker_id"
        )
    
    if not earnings_history:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No earnings history provided"
        )
    
    anomalies = detect_anomalies(earnings_history)
    
    if anomalies:
        explanation = "We've detected the following patterns in your earnings:\n\n"
        for a in anomalies:
            explanation += f"• {a.description}\n"
        explanation += "\nRecommendation: Review your recent earnings records and platform commission rates."
    else:
        explanation = "No unusual patterns detected in your earnings history. Your income appears stable."
    
    return AnomalyResponse(
        has_anomalies=len(anomalies) > 0,
        anomalies=anomalies,
        explanation=explanation
    )