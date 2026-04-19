from app.routers.auth import router as auth_router
from app.routers.google_auth import router as google_auth_router
from app.routers.chat import router as chat_router
from app.routers.earnings import router as earnings_router
from app.routers.anomaly import router as anomaly_router
from app.routers.analytics import router as analytics_router
from app.routers.certificate import router as certificate_router

__all__ = [
    "auth_router",
    "google_auth_router",
    "chat_router",
    "earnings_router",
    "anomaly_router",
    "analytics_router",
    "certificate_router"
]
