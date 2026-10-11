from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # handles dropped connections
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def get_db():
    """
    Yields a database session for FastAPI dependencies.
    Automatically closes the session after request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()