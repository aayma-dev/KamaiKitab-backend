# app/routers/__init__.py
from app.routers.auth import router as auth_router
from app.routers.google_auth import router as google_auth_router
from app.routers.chat import router as chat_router  # ADD THIS LINE
from app.routers.earnings import router as earnings_router
from app.routers.anomaly import router as anomaly_router


__all__ = ["auth_router", "google_auth_router", "chat_router", "earnings_router", "anomaly_router"]  # ADD chat_router, earnings_router, and anomaly_router