# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets
import logging

from app.database import get_db
from app.models import User, UserSession, TokenBlacklist, AuthProvider, UserRole
from app.schemas import (
    UserCreate, UserLogin, UserResponse, Token, 
    PasswordResetRequest, PasswordResetConfirm
)
from app.security import (
    get_password_hash, verify_password, create_access_token, 
    create_refresh_token, generate_secure_token, mask_email, verify_token
)
from app.auth import get_current_user, get_current_active_user
from app.rate_limiter import signup_limit, login_limit, password_reset_limit
from app.email_utils import send_verification_email, send_password_reset_email
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer()

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@signup_limit()
async def signup(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db)
):
    """Register a new user with email verification"""
    
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        if existing_user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        else:
            if existing_user.verification_token:
                background_tasks.add_task(
                    send_verification_email,
                    existing_user.email,
                    existing_user.name,
                    existing_user.verification_token
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not verified. Verification email resent."
            )
    
    # Create verification token
    verification_token = generate_secure_token()
    verification_expires = datetime.utcnow() + timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS)
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        hashed_password=hashed_password,
        verification_token=verification_token,
        verification_token_expires=verification_expires,
        is_active=True,
        is_verified=False,
        auth_provider=AuthProvider.EMAIL,
        role=UserRole.USER
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Send verification email
    background_tasks.add_task(
        send_verification_email,
        new_user.email,
        new_user.name,
        verification_token
    )
    
    logger.info(f"New user registered: {mask_email(new_user.email)}")
    
    return new_user

@router.get("/verify-email")
async def verify_email(
    token: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Verify user's email address"""
    
    user = db.query(User).filter(
        User.verification_token == token,
        User.verification_token_expires > datetime.utcnow()
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    db.commit()
    
    logger.info(f"User email verified: {mask_email(user.email)}")
    
    return {"message": "Email verified successfully! You can now sign in."}

@router.post("/signin", response_model=Token)
@login_limit()
async def signin(
    login_data: UserLogin,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db)
):
    """Sign in user with email and password"""
    
    user = db.query(User).filter(User.email == login_data.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    if user.is_locked and user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account locked. Try again after {user.locked_until}"
        )
    
    if user.auth_provider == AuthProvider.GOOGLE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account uses Google Sign-In"
        )
    
    if not verify_password(login_data.password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.is_locked = True
            user.locked_until = datetime.utcnow() + timedelta(minutes=30)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    if not user.is_verified:
        if user.verification_token:
            background_tasks.add_task(
                send_verification_email,
                user.email,
                user.name,
                user.verification_token
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. A new verification email has been sent."
        )
    
    # Reset failed attempts
    user.failed_login_attempts = 0
    user.is_locked = False
    user.last_login_at = datetime.utcnow()
    user.last_login_ip = request.client.host
    db.commit()
    
    # Create tokens
    access_token = create_access_token({"sub": user.email, "user_id": user.id})
    refresh_token = create_refresh_token({"sub": user.email, "user_id": user.id})
    
    # Create session
    session = UserSession(
        user_id=user.id,
        session_token=access_token,
        refresh_token=refresh_token,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent", ""),
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(session)
    db.commit()
    
    logger.info(f"User signed in: {mask_email(user.email)}")
    
    return Token(access_token=access_token, refresh_token=refresh_token)

@router.post("/signout")
async def signout(
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Sign out user"""
    
    token = credentials.credentials
    
    # Blacklist token
    blacklisted = TokenBlacklist(
        token=token,
        token_type="access",
        user_id=current_user.id,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    db.add(blacklisted)
    
    # Invalidate session
    session = db.query(UserSession).filter(UserSession.session_token == token).first()
    if session:
        session.is_active = False
    
    db.commit()
    
    logger.info(f"User signed out: {mask_email(current_user.email)}")
    
    return {"message": "Successfully signed out"}

@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Get new access token using refresh token"""
    
    payload = verify_token(refresh_token, token_type="refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user or not user.is_active or not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    session = db.query(UserSession).filter(
        UserSession.refresh_token == refresh_token,
        UserSession.is_active == True
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found"
        )
    
    # Create new tokens
    new_access_token = create_access_token({"sub": user.email, "user_id": user.id})
    new_refresh_token = create_refresh_token({"sub": user.email, "user_id": user.id})
    
    session.session_token = new_access_token
    session.refresh_token = new_refresh_token
    session.last_activity = datetime.utcnow()
    db.commit()
    
    return Token(access_token=new_access_token, refresh_token=new_refresh_token)

@router.post("/forgot-password")
@password_reset_limit()
async def forgot_password(
    request_data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db)
):
    """Send password reset email"""
    
    user = db.query(User).filter(User.email == request_data.email).first()
    
    if user and user.auth_provider == AuthProvider.EMAIL:
        reset_token = generate_secure_token()
        reset_expires = datetime.utcnow() + timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
        
        user.reset_password_token = reset_token
        user.reset_password_token_expires = reset_expires
        db.commit()
        
        background_tasks.add_task(
            send_password_reset_email,
            user.email,
            user.name,
            reset_token
        )
    
    return {"message": "If your email is registered, you will receive a password reset link"}

@router.post("/reset-password")
async def reset_password(
    data: PasswordResetConfirm,
    request: Request,
    db: Session = Depends(get_db)
):
    """Confirm password reset"""
    
    user = db.query(User).filter(
        User.reset_password_token == data.token,
        User.reset_password_token_expires > datetime.utcnow()
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    user.hashed_password = get_password_hash(data.new_password)
    user.reset_password_token = None
    user.reset_password_token_expires = None
    
    # Invalidate all sessions
    db.query(UserSession).filter(UserSession.user_id == user.id).update({"is_active": False})
    db.commit()
    
    logger.info(f"Password reset for user: {mask_email(user.email)}")
    
    return {"message": "Password reset successful"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information"""
    return current_user