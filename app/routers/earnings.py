# app/routers/earnings.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, date
import csv
import io
import logging
import base64

from app.database import get_db
from app.auth import get_current_active_user
from app.models import User, EarningsLog, EarningsScreenshot, VerificationRecord, UserRole
from app.schemas_earnings import (
    EarningsLogCreate, EarningsLogResponse, EarningsLogUpdate,
    VerificationResponse, VerificationUpdate, CSVUploadResponse
)
from app.security import mask_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/earnings", tags=["Earnings"])

# ============================================
# WORKER ENDPOINTS
# ============================================

@router.post("/logs", response_model=EarningsLogResponse, status_code=status.HTTP_201_CREATED)
async def create_earnings_log(
    log_data: EarningsLogCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new earnings log entry"""
    
    if current_user.role not in [UserRole.WORKER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workers can create earnings logs"
        )
    
    # Convert to float for division (fix Decimal/float error)
    net_received_float = float(log_data.net_received)
    hours_worked_float = float(log_data.hours_worked)
    
    # Calculate effective hourly rate
    effective_hourly_rate = net_received_float / hours_worked_float if hours_worked_float > 0 else 0
    
    new_log = EarningsLog(
        worker_id=current_user.id,
        platform=log_data.platform,
        date=datetime.combine(log_data.date, datetime.min.time()),
        hours_worked=log_data.hours_worked,
        gross_earned=log_data.gross_earned,
        platform_deductions=log_data.platform_deductions,
        net_received=log_data.net_received,
        effective_hourly_rate=effective_hourly_rate,
        notes=log_data.notes
    )
    
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    
    logger.info(f"Worker {mask_email(current_user.email)} created earnings log {new_log.id}")
    
    # Return as response model
    return EarningsLogResponse(
        id=new_log.id,
        worker_id=new_log.worker_id,
        platform=new_log.platform,
        date=new_log.date.date(),
        hours_worked=float(new_log.hours_worked),
        gross_earned=float(new_log.gross_earned),
        platform_deductions=float(new_log.platform_deductions),
        net_received=float(new_log.net_received),
        effective_hourly_rate=float(new_log.effective_hourly_rate) if new_log.effective_hourly_rate else None,
        notes=new_log.notes,
        created_at=new_log.created_at,
        verification_status="pending"
    )

@router.get("/logs", response_model=List[EarningsLogResponse])
async def get_earnings_logs(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    platform: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all earnings logs for current worker"""
    
    query = db.query(EarningsLog).filter(EarningsLog.worker_id == current_user.id)
    
    if start_date:
        query = query.filter(EarningsLog.date >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.filter(EarningsLog.date <= datetime.combine(end_date, datetime.min.time()))
    if platform:
        query = query.filter(EarningsLog.platform == platform)
    
    logs = query.order_by(EarningsLog.date.desc()).all()
    
    results = []
    for log in logs:
        verification = db.query(VerificationRecord).filter(VerificationRecord.earnings_log_id == log.id).first()
        results.append(EarningsLogResponse(
            id=log.id,
            worker_id=log.worker_id,
            platform=log.platform,
            date=log.date.date(),
            hours_worked=float(log.hours_worked),
            gross_earned=float(log.gross_earned),
            platform_deductions=float(log.platform_deductions),
            net_received=float(log.net_received),
            effective_hourly_rate=float(log.effective_hourly_rate) if log.effective_hourly_rate else None,
            notes=log.notes,
            created_at=log.created_at,
            verification_status=verification.status if verification else "pending"
        ))
    
    return results

@router.get("/logs/{log_id}", response_model=EarningsLogResponse)
async def get_earnings_log(
    log_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get specific earnings log"""
    
    log = db.query(EarningsLog).filter(
        EarningsLog.id == log_id,
        EarningsLog.worker_id == current_user.id
    ).first()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Earnings log not found"
        )
    
    verification = db.query(VerificationRecord).filter(VerificationRecord.earnings_log_id == log.id).first()
    
    return EarningsLogResponse(
        id=log.id,
        worker_id=log.worker_id,
        platform=log.platform,
        date=log.date.date(),
        hours_worked=float(log.hours_worked),
        gross_earned=float(log.gross_earned),
        platform_deductions=float(log.platform_deductions),
        net_received=float(log.net_received),
        effective_hourly_rate=float(log.effective_hourly_rate) if log.effective_hourly_rate else None,
        notes=log.notes,
        created_at=log.created_at,
        verification_status=verification.status if verification else "pending"
    )

@router.put("/logs/{log_id}", response_model=EarningsLogResponse)
async def update_earnings_log(
    log_id: int,
    log_data: EarningsLogUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update earnings log"""
    
    log = db.query(EarningsLog).filter(
        EarningsLog.id == log_id,
        EarningsLog.worker_id == current_user.id
    ).first()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Earnings log not found"
        )
    
    update_data = log_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(log, field, value)
    
    # Recalculate hourly rate if needed
    if 'net_received' in update_data or 'hours_worked' in update_data:
        net = update_data.get('net_received', log.net_received)
        hours = update_data.get('hours_worked', log.hours_worked)
        log.effective_hourly_rate = float(net) / float(hours) if hours > 0 else 0
    
    db.commit()
    db.refresh(log)
    
    verification = db.query(VerificationRecord).filter(VerificationRecord.earnings_log_id == log.id).first()
    
    return EarningsLogResponse(
        id=log.id,
        worker_id=log.worker_id,
        platform=log.platform,
        date=log.date.date(),
        hours_worked=float(log.hours_worked),
        gross_earned=float(log.gross_earned),
        platform_deductions=float(log.platform_deductions),
        net_received=float(log.net_received),
        effective_hourly_rate=float(log.effective_hourly_rate) if log.effective_hourly_rate else None,
        notes=log.notes,
        created_at=log.created_at,
        verification_status=verification.status if verification else "pending"
    )

@router.delete("/logs/{log_id}")
async def delete_earnings_log(
    log_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete earnings log"""
    
    log = db.query(EarningsLog).filter(
        EarningsLog.id == log_id,
        EarningsLog.worker_id == current_user.id
    ).first()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Earnings log not found"
        )
    
    db.delete(log)
    db.commit()
    
    return {"message": "Earnings log deleted successfully"}

@router.post("/import-csv", response_model=CSVUploadResponse)
async def import_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Import earnings from CSV file"""
    
    if current_user.role not in [UserRole.WORKER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workers can import earnings"
        )
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported"
        )
    
    content = await file.read()
    csv_data = content.decode('utf-8')
    csv_reader = csv.DictReader(io.StringIO(csv_data))
    
    created_count = 0
    errors = []
    
    for row_num, row in enumerate(csv_reader, start=2):
        try:
            log_date = datetime.strptime(row.get('date', ''), '%Y-%m-%d').date()
            hours = float(row.get('hours_worked', 0))
            gross = float(row.get('gross_earned', 0))
            deductions = float(row.get('platform_deductions', 0))
            net = gross - deductions
            
            effective_rate = net / hours if hours > 0 else 0
            
            new_log = EarningsLog(
                worker_id=current_user.id,
                platform=row.get('platform', 'Unknown'),
                date=datetime.combine(log_date, datetime.min.time()),
                hours_worked=hours,
                gross_earned=gross,
                platform_deductions=deductions,
                net_received=net,
                effective_hourly_rate=effective_rate,
                notes=row.get('notes', '')
            )
            db.add(new_log)
            created_count += 1
            
        except Exception as e:
            errors.append({"row": row_num, "error": str(e)})
    
    db.commit()
    
    return CSVUploadResponse(
        created_count=created_count,
        errors=errors,
        message=f"Successfully imported {created_count} records"
    )

# ============================================
# VERIFIER ENDPOINTS
# ============================================

@router.get("/pending-verifications", response_model=List[EarningsLogResponse])
async def get_pending_verifications(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get pending verifications (Verifier only)"""
    
    if current_user.role not in [UserRole.VERIFIER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verifier privileges required"
        )
    
    # Get logs without verification records
    pending_logs = db.query(EarningsLog).outerjoin(
        VerificationRecord, EarningsLog.id == VerificationRecord.earnings_log_id
    ).filter(VerificationRecord.id == None).all()
    
    results = []
    for log in pending_logs:
        results.append(EarningsLogResponse(
            id=log.id,
            worker_id=log.worker_id,
            platform=log.platform,
            date=log.date.date(),
            hours_worked=float(log.hours_worked),
            gross_earned=float(log.gross_earned),
            platform_deductions=float(log.platform_deductions),
            net_received=float(log.net_received),
            effective_hourly_rate=float(log.effective_hourly_rate) if log.effective_hourly_rate else None,
            notes=log.notes,
            created_at=log.created_at,
            verification_status="pending"
        ))
    
    return results

@router.post("/verify/{log_id}", response_model=VerificationResponse)
async def verify_earnings(
    log_id: int,
    verification: VerificationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Verify or dispute an earnings record (Verifier only)"""
    
    if current_user.role not in [UserRole.VERIFIER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verifier privileges required"
        )
    
    log = db.query(EarningsLog).filter(EarningsLog.id == log_id).first()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Earnings log not found"
        )
    
    existing_verification = db.query(VerificationRecord).filter(
        VerificationRecord.earnings_log_id == log_id
    ).first()
    
    if existing_verification:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This record has already been verified"
        )
    
    new_verification = VerificationRecord(
        earnings_log_id=log_id,
        verifier_id=current_user.id,
        status=verification.status,
        verifier_notes=verification.notes
    )
    db.add(new_verification)
    db.commit()
    db.refresh(new_verification)
    
    logger.info(f"Verifier {mask_email(current_user.email)} verified log {log_id} as {verification.status}")
    
    return new_verification

# ============================================
# SCREENSHOT UPLOAD
# ============================================

@router.post("/logs/{log_id}/screenshots")
async def upload_screenshot(
    log_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload screenshot for earnings verification"""
    
    log = db.query(EarningsLog).filter(
        EarningsLog.id == log_id,
        EarningsLog.worker_id == current_user.id
    ).first()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Earnings log not found"
        )
    
    content = await file.read()
    b64_content = base64.b64encode(content).decode('utf-8')
    
    screenshot = EarningsScreenshot(
        earnings_log_id=log_id,
        image_url=f"data:{file.content_type};base64,{b64_content[:100]}..."
    )
    db.add(screenshot)
    db.commit()
    
    return {"message": "Screenshot uploaded successfully", "screenshot_id": screenshot.id}