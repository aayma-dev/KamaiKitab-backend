import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings
import logging

logger = logging.getLogger(__name__)

async def send_email_async(to_email: str, subject: str, html_content: str) -> bool:
   # \"\"\"Send email using Gmail SMTP with STARTTLS\"\"\"
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("Email not configured - skipping send")
        return False
    
    try:
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{settings.FROM_NAME} <{settings.FROM_EMAIL}>"
        message["To"] = to_email
        
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)
        
        # Use smtplib directly with STARTTLS (not aiosmtplib for Gmail)
        import smtplib
        import ssl
        
        # Create secure connection with STARTTLS
        context = ssl.create_default_context()
        
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(message)
        
        logger.info(f"Email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Email failed: {str(e)}")
        return False

async def send_verification_email(user_email: str, user_name: str, token: str) -> bool:
   # \"\"\"Send email verification link\"\"\"
    verification_link = f"{settings.APP_URL}/api/auth/verify-email?token={token}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Verify Your Email</title></head>
    <body style="font-family: Arial, sans-serif;">
        <h2>Welcome {user_name}!</h2>
        <p>Thank you for registering! Please verify your email address:</p>
        <p><a href="{verification_link}">Click here to verify your email</a></p>
        <p>Or copy this link: {verification_link}</p>
        <p>This link expires in {settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS} hours.</p>
        <p>If you didn't create an account, please ignore this email.</p>
        <hr>
        <p style="font-size: 12px; color: #666;">{settings.APP_NAME}</p>
    </body>
    </html>
    """
    
    return await send_email_async(user_email, f"Verify Your {settings.APP_NAME} Account", html_content)

async def send_password_reset_email(user_email: str, user_name: str, token: str) -> bool:
    #\"\"\"Send password reset link\"\"\"
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Reset Your Password</title></head>
    <body style="font-family: Arial, sans-serif;">
        <h2>Hello {user_name},</h2>
        <p>We received a request to reset your password. Click the link below:</p>
        <p><a href="{reset_link}">Reset Password</a></p>
        <p>Or copy this link: {reset_link}</p>
        <p>This link expires in {settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS} hours.</p>
        <p>If you didn't request this, please ignore this email.</p>
        <hr>
        <p style="font-size: 12px; color: #666;">{settings.APP_NAME}</p>
    </body>
    </html>
    """
    
    return await send_email_async(user_email, f"Reset Your {settings.APP_NAME} Password", html_content)
