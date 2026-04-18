from celery import Celery
from app.config import settings
import asyncio

# Only configure Celery if Redis is available
celery_app = None

try:
    celery_app = Celery(
        "auth_tasks",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL
    )
    
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=30 * 60,
        task_soft_time_limit=25 * 60,
    )
    print("✅ Celery configured")
except Exception as e:
    print(f"⚠️ Celery not configured: {e}")

# Define tasks if Celery is available
if celery_app:
    @celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
    def send_verification_email_task(self, email: str, name: str, token: str):
        #\"\"\"Send verification email as Celery task\"\"\"
        from app.email_utils import send_verification_email
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(send_verification_email(email, name, token))
            loop.close()
            return result
        except Exception as exc:
            raise self.retry(exc=exc)

    @celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
    def send_password_reset_email_task(self, email: str, name: str, token: str):
        #\"\"\"Send password reset email as Celery task\"\"\"
        from app.email_utils import send_password_reset_email
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(send_password_reset_email(email, name, token))
            loop.close()
            return result
        except Exception as exc:
            raise self.retry(exc=exc)
