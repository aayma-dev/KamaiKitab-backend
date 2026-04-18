from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Text, Index, ForeignKey, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class UserRole(str, enum.Enum):
    WORKER = "worker"
    VERIFIER = "verifier"
    ADVOCATE = "advocate"
    ADMIN = "admin"
    USER = "user"

class AuthProvider(str, enum.Enum):
    EMAIL = "email"
    GOOGLE = "google"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)
    
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_locked = Column(Boolean, default=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    
    auth_provider = Column(Enum(AuthProvider), default=AuthProvider.EMAIL)
    role = Column(Enum(UserRole), default=UserRole.USER)
    
    verification_token = Column(String(255), nullable=True, unique=True)
    verification_token_expires = Column(DateTime(timezone=True), nullable=True)
    reset_password_token = Column(String(255), nullable=True, unique=True)
    reset_password_token_expires = Column(DateTime(timezone=True), nullable=True)
    
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_user_email_verified', 'email', 'is_verified'),
        Index('idx_user_reset_token', 'reset_password_token'),
        Index('idx_user_verification_token', 'verification_token'),
    )

class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_token = Column(String(500), unique=True, nullable=False, index=True)
    refresh_token = Column(String(500), unique=True, nullable=False, index=True)
    ip_address = Column(String(45), nullable=False)
    user_agent = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="sessions")

class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(500), unique=True, nullable=False, index=True)
    token_type = Column(String(20), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    blacklisted_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(50), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    status = Column(String(20), default="success")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="audit_logs")

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False, default="New Conversation")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    session = relationship("ChatSession", back_populates="messages")

# ============================================
# FAIRGIG EARNINGS MODELS - SIMPLIFIED (NO CIRCULAR REFERENCES)
# ============================================

class EarningsLog(Base):
    __tablename__ = "earnings_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, nullable=False)  # Simple integer, no ForeignKey
    platform = Column(String(100), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    hours_worked = Column(Numeric(10, 2), nullable=False)
    gross_earned = Column(Numeric(10, 2), nullable=False)
    platform_deductions = Column(Numeric(10, 2), nullable=False)
    net_received = Column(Numeric(10, 2), nullable=False)
    effective_hourly_rate = Column(Numeric(10, 2), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    screenshots = relationship("EarningsScreenshot", back_populates="earnings_log", cascade="all, delete-orphan")
    verification = relationship("VerificationRecord", back_populates="earnings_log", uselist=False, cascade="all, delete-orphan")

class EarningsScreenshot(Base):
    __tablename__ = "earnings_screenshots"
    
    id = Column(Integer, primary_key=True, index=True)
    earnings_log_id = Column(Integer, ForeignKey("earnings_logs.id", ondelete="CASCADE"), nullable=False)
    image_url = Column(String(500), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    earnings_log = relationship("EarningsLog", back_populates="screenshots")

class VerificationRecord(Base):
    __tablename__ = "verification_records"
    
    id = Column(Integer, primary_key=True, index=True)
    earnings_log_id = Column(Integer, ForeignKey("earnings_logs.id", ondelete="CASCADE"), nullable=False, unique=True)
    verifier_id = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    verifier_notes = Column(Text, nullable=True)
    verified_at = Column(DateTime(timezone=True), server_default=func.now())
    
    earnings_log = relationship("EarningsLog", back_populates="verification")

class Grievance(Base):
    __tablename__ = "grievances"
    
    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, nullable=False)  # Simple integer, no ForeignKey
    platform = Column(String(100), nullable=False)
    category = Column(String(100), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="open")
    cluster_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    tags = relationship("GrievanceTag", back_populates="grievance", cascade="all, delete-orphan")
    escalations = relationship("GrievanceEscalation", back_populates="grievance", cascade="all, delete-orphan")

class GrievanceTag(Base):
    __tablename__ = "grievance_tags"
    
    id = Column(Integer, primary_key=True, index=True)
    grievance_id = Column(Integer, ForeignKey("grievances.id", ondelete="CASCADE"), nullable=False)
    tag = Column(String(50), nullable=False)
    
    grievance = relationship("Grievance", back_populates="tags")

class GrievanceEscalation(Base):
    __tablename__ = "grievance_escalations"
    
    id = Column(Integer, primary_key=True, index=True)
    grievance_id = Column(Integer, ForeignKey("grievances.id", ondelete="CASCADE"), nullable=False)
    escalated_by = Column(Integer, nullable=False)
    escalated_at = Column(DateTime(timezone=True), server_default=func.now())
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    grievance = relationship("Grievance", back_populates="escalations")

class CityMedianCache(Base):
    __tablename__ = "city_median_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    city_zone = Column(String(100), nullable=False)
    worker_category = Column(String(100), nullable=False)
    median_hourly_rate = Column(Numeric(10, 2), nullable=False)
    sample_size = Column(Integer, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())