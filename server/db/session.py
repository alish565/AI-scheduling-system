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
    Returns a database session.
    Caller is responsible for closing it.
    """
    db = SessionLocal()
    try:
        return db
    finally:
        pass
