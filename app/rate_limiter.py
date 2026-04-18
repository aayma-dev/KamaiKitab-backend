from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException, status
import logging

logger = logging.getLogger(__name__)

# In-memory rate limiting (works without Redis)
limiter = Limiter(key_func=get_remote_address)

async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(f"Rate limit exceeded for {request.client.host}")
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many requests. Please try again later."
    )

def signup_limit():
    return limiter.limit("5/hour")

def login_limit():
    return limiter.limit("10/minute")

def password_reset_limit():
    return limiter.limit("3/hour")
