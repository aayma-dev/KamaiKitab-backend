from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Create engine with PostgreSQL connection pool
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.DEBUG
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

def get_db():
   # \"\"\"Dependency for getting database session\"\"\"
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

@event.listens_for(engine, "connect")
def set_database_settings(dbapi_connection, connection_record):
    #\"\"\"Set PostgreSQL connection settings\"\"\"
    cursor = dbapi_connection.cursor()
    cursor.execute("SET TIME ZONE 'UTC';")
    cursor.execute("SET client_encoding TO 'UTF8';")
    cursor.close()

def init_db():
    #\"\"\"Initialize database - create all tables\"\"\"#
    Base.metadata.create_all(bind=engine)
    logger.info("PostgreSQL database tables created successfully")

def check_db_connection() -> bool:
   # \"\"\"Check if PostgreSQL connection is working\"\"\"#
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"PostgreSQL connection failed: {str(e)}")
        return False
