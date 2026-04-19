from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime, timedelta
import logging

from app.database import get_db
from app.auth import get_current_active_user
from app.models import User, EarningsLog, Grievance, UserRole, VerificationRecord
from app.security import mask_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/dashboard-summary")
async def get_dashboard_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get summary statistics for advocate dashboard."""
    
    if current_user.role not in [UserRole.ADVOCATE, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Advocate privileges required"
        )
    
    total_workers = db.query(User).filter(User.role == UserRole.WORKER).count()
    
    # FIXED: Use VerificationRecord instead of is_verified
    total_verified_result = db.query(func.sum(EarningsLog.net_received)).join(
        VerificationRecord, EarningsLog.id == VerificationRecord.earnings_log_id
    ).filter(VerificationRecord.status == 'confirmed').scalar()
    total_verified = total_verified_result if total_verified_result else 0
    
    avg_comm_result = db.query(func.avg(EarningsLog.platform_deductions / func.nullif(EarningsLog.gross_earned, 0) * 100)).filter(EarningsLog.gross_earned > 0).scalar()
    avg_comm = avg_comm_result if avg_comm_result else 0
    
    open_grievances = db.query(Grievance).filter(Grievance.status == 'open').count()
    
    week_start = datetime.utcnow() - timedelta(days=7)
    weekly_earnings_result = db.query(func.sum(EarningsLog.net_received)).filter(EarningsLog.created_at >= week_start).scalar()
    weekly_earnings = weekly_earnings_result if weekly_earnings_result else 0
    
    return {
        "total_workers": total_workers,
        "total_verified_earnings": round(float(total_verified), 2),
        "average_commission_rate": round(float(avg_comm), 1),
        "open_grievances": open_grievances,
        "weekly_activity": {
            "total_earnings": round(float(weekly_earnings), 2),
            "period": "last_7_days"
        }
    }

@router.get("/commission-trends")
async def get_commission_trends(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    days: int = Query(90, description="Number of days to look back", ge=7, le=365),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get platform commission rate trends over time."""
    
    if current_user.role not in [UserRole.ADVOCATE, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Advocate privileges required"
        )
    
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)
    
    query = db.query(
        EarningsLog.platform,
        func.date_trunc('week', EarningsLog.date).label('week'),
        func.avg(EarningsLog.platform_deductions / func.nullif(EarningsLog.gross_earned, 0) * 100).label('avg_commission'),
        func.count(EarningsLog.id).label('sample_count')
    ).filter(
        EarningsLog.date >= start_date,
        EarningsLog.date <= end_date,
        EarningsLog.gross_earned > 0
    )
    
    if platform:
        query = query.filter(EarningsLog.platform == platform)
    
    results = query.group_by(
        EarningsLog.platform,
        func.date_trunc('week', EarningsLog.date)
    ).order_by(
        EarningsLog.platform,
        func.date_trunc('week', EarningsLog.date)
    ).all()
    
    trends = {}
    for platform_name, week, avg_commission, sample_count in results:
        if platform_name not in trends:
            trends[platform_name] = []
        trends[platform_name].append({
            "week": week.isoformat() if week else None,
            "avg_commission_percent": float(avg_commission) if avg_commission else 0,
            "sample_count": sample_count
        })
    
    return {
        "platforms": list(trends.keys()),
        "trends": trends,
        "date_range": {"start": start_date.isoformat(), "end": end_date.isoformat(), "days": days}
    }

@router.get("/vulnerable-workers")
async def get_vulnerable_workers(
    threshold_percent: float = Query(20.0, description="Income drop threshold percentage"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get workers whose income dropped more than threshold percent."""
    
    if current_user.role not in [UserRole.ADVOCATE, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Advocate privileges required"
        )
    
    workers = db.query(User).filter(User.role == UserRole.WORKER).all()
    vulnerable_workers = []
    
    for worker in workers:
        earnings = db.query(
            func.date_trunc('month', EarningsLog.date).label('month'),
            func.sum(EarningsLog.net_received).label('total_income')
        ).filter(
            EarningsLog.worker_id == worker.id,
            EarningsLog.date >= datetime.utcnow() - timedelta(days=90)
        ).group_by(
            func.date_trunc('month', EarningsLog.date)
        ).order_by('month').all()
        
        if len(earnings) >= 2:
            recent = float(earnings[-1].total_income) if earnings[-1].total_income else 0
            previous = float(earnings[-2].total_income) if earnings[-2].total_income else 0
            
            if previous > 0:
                drop = ((previous - recent) / previous) * 100
                
                if drop > threshold_percent:
                    vulnerable_workers.append({
                        "worker_id": worker.id,
                        "worker_name": worker.name,
                        "worker_email": mask_email(worker.email),
                        "city_zone": getattr(worker, 'city_zone', 'Unknown'),
                        "previous_month_income": round(previous, 2),
                        "current_month_income": round(recent, 2),
                        "drop_percentage": round(drop, 1),
                        "needs_attention": drop > 30
                    })
    
    vulnerable_workers.sort(key=lambda x: x['drop_percentage'], reverse=True)
    
    return {
        "total_workers_analyzed": len(workers),
        "vulnerable_workers_count": len(vulnerable_workers),
        "threshold_percent": threshold_percent,
        "vulnerable_workers": vulnerable_workers[:50]
    }

@router.get("/worker-dashboard")
async def get_worker_dashboard(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get analytics for worker's own dashboard."""
    
    ninety_days_ago = datetime.utcnow() - timedelta(days=90)
    
    earnings = db.query(EarningsLog).filter(
        EarningsLog.worker_id == current_user.id,
        EarningsLog.date >= ninety_days_ago
    ).order_by(EarningsLog.date).all()
    
    if not earnings:
        return {"has_data": False, "message": "No earnings data available"}
    
    monthly_data = {}
    
    for e in earnings:
        month = e.date.strftime("%Y-%m")
        
        if month not in monthly_data:
            monthly_data[month] = {"net": 0, "hours": 0, "commission": 0, "count": 0}
        monthly_data[month]["net"] += float(e.net_received)
        monthly_data[month]["hours"] += float(e.hours_worked)
        monthly_data[month]["commission"] += float(e.platform_deductions) / float(e.gross_earned) * 100 if e.gross_earned > 0 else 0
        monthly_data[month]["count"] += 1
    
    monthly_trend = []
    for month, data in monthly_data.items():
        monthly_trend.append({
            "month": month,
            "total_earnings": round(data["net"], 2),
            "total_hours": round(data["hours"], 1),
            "avg_commission_rate": round(data["commission"] / data["count"], 1) if data["count"] > 0 else 0,
            "hourly_rate": round(data["net"] / data["hours"], 2) if data["hours"] > 0 else 0
        })
    
    monthly_trend.sort(key=lambda x: x['month'])
    
    return {
        "has_data": True,
        "monthly_trend": monthly_trend,
        "total_earnings_90d": round(sum(float(e.net_received) for e in earnings), 2),
        "total_hours_90d": round(sum(float(e.hours_worked) for e in earnings), 1),
        "average_hourly_rate_90d": round(
            sum(float(e.net_received) for e in earnings) / sum(float(e.hours_worked) for e in earnings), 2
        ) if sum(float(e.hours_worked) for e in earnings) > 0 else 0
    }

@router.get("/top-complaints")
async def get_top_complaints(
    days: int = Query(30, description="Number of days to look back"),
    limit: int = Query(5, description="Number of top complaints to return"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get top complaint categories."""
    
    if current_user.role not in [UserRole.ADVOCATE, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Advocate privileges required"
        )
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    results = db.query(
        Grievance.category,
        func.count(Grievance.id).label('count')
    ).filter(
        Grievance.created_at >= start_date
    ).group_by(
        Grievance.category
    ).order_by(
        func.count(Grievance.id).desc()
    ).limit(limit).all()
    
    complaints = []
    for category, count in results:
        complaints.append({
            "category": category,
            "count": count
        })
    
    return {"period_days": days, "top_complaints": complaints}

@router.get("/median-comparison/{worker_id}")
async def get_median_comparison(
    worker_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Compare a worker's earnings against city-wide median."""
    
    if current_user.id != worker_id and current_user.role not in [UserRole.ADVOCATE, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    worker = db.query(User).filter(User.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    worker_earnings = db.query(EarningsLog).filter(
        EarningsLog.worker_id == worker_id,
        EarningsLog.date >= thirty_days_ago
    ).all()
    
    if not worker_earnings:
        return {"worker_name": worker.name, "has_data": False, "message": "No earnings data in last 30 days"}
    
    total_net = sum(float(e.net_received) for e in worker_earnings)
    total_hours = sum(float(e.hours_worked) for e in worker_earnings)
    worker_hourly_rate = total_net / total_hours if total_hours > 0 else 0
    
    # FIXED: Use VerificationRecord instead of is_verified
    city_median = db.query(
        func.percentile_cont(0.5).within_group(EarningsLog.effective_hourly_rate).label('median_hourly_rate')
    ).join(
        VerificationRecord, EarningsLog.id == VerificationRecord.earnings_log_id
    ).filter(
        VerificationRecord.status == 'confirmed'
    ).first()
    
    median_rate = float(city_median.median_hourly_rate) if city_median and city_median.median_hourly_rate else 0
    
    return {
        "worker_name": worker.name,
        "has_data": True,
        "worker_hourly_rate": round(worker_hourly_rate, 2),
        "city_median_hourly_rate": round(median_rate, 2),
        "comparison": {
            "difference": round(worker_hourly_rate - median_rate, 2),
            "percentage": round(((worker_hourly_rate - median_rate) / median_rate * 100), 1) if median_rate > 0 else 0,
            "is_above_average": worker_hourly_rate > median_rate
        }
    }
