# app/routers/google_auth.py - COMPLETE WORKING CODE
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets
import string
import logging
import httpx

from app.database import get_db
from app.models import User, UserSession, AuthProvider, UserRole
from app.security import get_password_hash, create_access_token, create_refresh_token, mask_email
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth/google", tags=["Google Auth"])

def generate_random_password() -> str:
    """Generate a secure random password for Google OAuth users"""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(32))

@router.get("/login")
async def google_login(request: Request):
    """Redirect to Google login page"""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to .env"
        )
    
    # Build Google OAuth URL
    from urllib.parse import urlencode
    
    params = {
        'client_id': settings.GOOGLE_CLIENT_ID,
        'redirect_uri': settings.GOOGLE_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'openid email profile',
        'access_type': 'offline',
        'prompt': 'consent'
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    
    return {
        "auth_url": auth_url,
        "message": "Click the link to login with Google",
        "redirect_uri": settings.GOOGLE_REDIRECT_URI
    }

@router.get("/callback")
async def google_callback(
    code: str = None,
    error: str = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Handle Google OAuth callback"""
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google OAuth error: {error}"
        )
    
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code missing"
        )
    
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth not configured"
        )
    
    # Exchange code for tokens
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        'client_id': settings.GOOGLE_CLIENT_ID,
        'client_secret': settings.GOOGLE_CLIENT_SECRET,
        'code': code,
        'redirect_uri': settings.GOOGLE_REDIRECT_URI,
        'grant_type': 'authorization_code'
    }
    
    async with httpx.AsyncClient() as client:
        # Get tokens
        token_response = await client.post(token_url, data=token_data)
        if token_response.status_code != 200:
            logger.error(f"Token exchange failed: {token_response.text}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange code for tokens"
            )
        
        tokens = token_response.json()
        access_token = tokens.get('access_token')
        
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No access token received"
            )
        
        # Get user info
        userinfo_response = await client.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        if userinfo_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info"
            )
        
        user_info = userinfo_response.json()
        email = user_info.get('email')
        name = user_info.get('name', email.split('@')[0] if email else "Google User")
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided by Google"
            )
        
        # Check if user exists
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # Create new user with Google auth
            random_password = generate_random_password()
            hashed_password = get_password_hash(random_password)
            
            user = User(
                name=name,
                email=email,
                hashed_password=hashed_password,
                is_active=True,
                is_verified=True,  # Google verified the email
                auth_provider=AuthProvider.GOOGLE,
                role=UserRole.USER
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            logger.info(f"New user registered via Google: {mask_email(email)}")
            
        elif not user.is_verified:
            # If user exists but not verified, verify them now
            user.is_verified = True
            user.is_active = True
            db.commit()
            logger.info(f"User verified via Google: {mask_email(email)}")
        
        # Create JWT tokens
        access_token_jwt = create_access_token({"sub": user.email, "user_id": user.id})
        refresh_token_jwt = create_refresh_token({"sub": user.email, "user_id": user.id})
        
        # Create session
        client_ip = request.client.host if request else "unknown"
        user_agent = request.headers.get("user-agent", "") if request else ""
        
        session = UserSession(
            user_id=user.id,
            session_token=access_token_jwt,
            refresh_token=refresh_token_jwt,
            ip_address=client_ip,
            user_agent=user_agent,
            expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        db.add(session)
        
        # Update last login
        user.last_login_at = datetime.utcnow()
        user.last_login_ip = client_ip
        db.commit()
        
        logger.info(f"User logged in via Google: {mask_email(email)}")
        
        # Return tokens
        return {
            "access_token": access_token_jwt,
            "refresh_token": refresh_token_jwt,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email
            }
        }