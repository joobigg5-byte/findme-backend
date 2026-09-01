"""
Database connection and session management.

Uses SQLite for local development — swap DATABASE_URL to a real Postgres
connection string in production (e.g. postgresql://user:pass@host/dbname).
SQLAlchemy's ORM layer means almost nothing else in this codebase needs to
change when you make that swap.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./findme.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
