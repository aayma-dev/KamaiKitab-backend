from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional
from datetime import datetime, date, timedelta
import logging
import uuid
from decimal import Decimal
from jinja2 import Environment, FileSystemLoader
import os

from app.database import get_db
from app.auth import get_current_active_user
from app.models import User, EarningsLog, VerificationRecord, UserRole
from app.security import mask_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/certificate", tags=["Certificate"])

# Setup Jinja2 template engine
template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
env = Environment(loader=FileSystemLoader(template_dir))

# Add custom filters for number formatting
def intcomma(value):
    """Format number with commas"""
    if value is None:
        return "0"
    try:
        return f"{float(value):,.2f}".rstrip('0').rstrip('.') if '.' in f"{float(value):,.2f}" else f"{float(value):,.0f}"
    except:
        return str(value)

env.filters['intcomma'] = intcomma

@router.get("/income", response_class=HTMLResponse)
async def generate_income_certificate(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    format: str = Query("html", regex="^(html|pdf)$", description="Output format"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Generate income certificate for worker.
    
    - **start_date**: Start date in YYYY-MM-DD format
    - **end_date**: End date in YYYY-MM-DD format
    - **format**: 'html' for browser view, 'pdf' for download
    
    Only verified earnings are included in the certificate.
    """
    
    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before end date"
        )
    
    # Limit date range to max 1 year
    if (end_date - start_date).days > 365:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date range cannot exceed 365 days"
        )
    
    # Get verified earnings for the worker
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    earnings = db.query(EarningsLog).join(
        VerificationRecord, EarningsLog.id == VerificationRecord.earnings_log_id
    ).filter(
        EarningsLog.worker_id == current_user.id,
        EarningsLog.date >= start_datetime,
        EarningsLog.date <= end_datetime,
        VerificationRecord.status == 'confirmed'
    ).order_by(EarningsLog.date).all()
    
    if not earnings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No verified earnings found in the selected date range"
        )
    
    # Calculate totals
    total_earnings = sum(float(e.net_received) for e in earnings)
    total_hours = sum(float(e.hours_worked) for e in earnings)
    total_gross = sum(float(e.gross_earned) for e in earnings)
    total_deductions = sum(float(e.platform_deductions) for e in earnings)
    avg_hourly_rate = total_earnings / total_hours if total_hours > 0 else 0
    
    # Prepare earnings data for template
    earnings_data = []
    for e in earnings:
        earnings_data.append({
            "date": e.date.strftime("%Y-%m-%d"),
            "platform": e.platform,
            "hours_worked": float(e.hours_worked),
            "gross_earned": float(e.gross_earned),
            "platform_deductions": float(e.platform_deductions),
            "net_received": float(e.net_received)
        })
    
    # Generate certificate ID
    certificate_id = f"KAMAI-{current_user.id}-{uuid.uuid4().hex[:8].upper()}"
    
    # Template context
    context = {
        "worker_name": current_user.name,
        "worker_email": current_user.email,
        "certificate_id": certificate_id,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "generated_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_earnings": total_earnings,
        "total_hours": total_hours,
        "total_gross": total_gross,
        "total_deductions": total_deductions,
        "avg_hourly_rate": avg_hourly_rate,
        "earnings": earnings_data
    }
    
    # Render HTML template
    template = env.get_template("certificate.html")
    html_content = template.render(**context)
    
    if format == "pdf":
        try:
            from weasyprint import HTML
            import tempfile
            
            # Generate PDF
            pdf_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            HTML(string=html_content).write_pdf(pdf_file.name)
            
            return FileResponse(
                pdf_file.name,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=income_certificate_{current_user.id}_{start_date}_{end_date}.pdf"
                }
            )
        except ImportError:
            # Fallback to HTML if weasyprint not installed
            return HTMLResponse(content=html_content, headers={
                "Content-Disposition": f"inline; filename=certificate.html"
            })
    else:
        # Return HTML for print-friendly view
        return HTMLResponse(content=html_content)
