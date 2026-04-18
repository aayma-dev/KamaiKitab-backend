# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
import logging
import time
# Add this import at the top with other imports
from app.routers import auth_router, google_auth_router, chat_router, earnings_router,anomaly_router


from app.config import settings
from app.database import engine, init_db, check_db_connection
from app.routers import auth_router, google_auth_router
from app.middleware import SecurityHeadersMiddleware, RequestLoggingMiddleware
from app.rate_limiter import limiter

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Production-ready authentication system with email verification",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",           # Your local frontend
        "http://localhost:3000",            # Alternative React port
        "http://127.0.0.1:5173",
        "http://192.168.8.100:5173",        # YOUR IP with frontend port
        "http://192.168.8.100:3000",        # Alternative port
        # Add your teammate's IP when they share it
        # "http://TEAMMATE_IP:5173",
    ],
    #settings.CORS_ORIGINS_LIST,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": exc.errors()}
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.APP_NAME}...")
    
    if not check_db_connection():
        logger.error("Database connection failed")
        raise RuntimeError("Database connection failed")
    
    init_db()
    logger.info("Application started successfully")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down...")
    engine.dispose()

# Include routers
app.include_router(auth_router)
app.include_router(google_auth_router)
app.include_router(chat_router) #this line for chat router
# Add these lines where other routers are included
app.include_router(earnings_router)
app.include_router(anomaly_router)

@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "environment": settings.ENVIRONMENT,
        "endpoints": {
            "signup": "POST /api/auth/signup",
            "signin": "POST /api/auth/signin",
            "signout": "POST /api/auth/signout",
            "verify_email": "GET /api/auth/verify-email",
            "refresh_token": "POST /api/auth/refresh",
            "forgot_password": "POST /api/auth/forgot-password",
            "reset_password": "POST /api/auth/reset-password",
            "me": "GET /api/auth/me",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    db_status = check_db_connection()
    return {
        "status": "healthy" if db_status else "unhealthy",
        "timestamp": time.time(),
        "database": "connected" if db_status else "disconnected",
        "environment": settings.ENVIRONMENT
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=settings.DEBUG
    )