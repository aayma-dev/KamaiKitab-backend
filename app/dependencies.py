from typing import Optional, AsyncGenerator
from redis import Redis
from app.config import settings
import logging

logger = logging.getLogger(__name__)

async def get_redis() -> AsyncGenerator[Optional[Redis], None]:
    #\"\"\"Get Redis client dependency (optional)\"\"\"
    redis_client = None
    try:
        redis_client = Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5
        )
        redis_client.ping()
        logger.info("Redis connected successfully")
        yield redis_client
    except Exception as e:
        logger.warning(f"Redis not available: {e}")
        yield None
    finally:
        if redis_client:
            redis_client.close()

def get_redis_sync() -> Optional[Redis]:
    #\"\"\"Get Redis client synchronously\"\"\"
    try:
        redis_client = Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5
        )
        redis_client.ping()
        return redis_client
    except Exception as e:
        logger.warning(f"Redis not available: {e}")
        return None
