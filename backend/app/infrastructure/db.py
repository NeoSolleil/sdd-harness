"""SQLAlchemy 2.0 engine/session setup and declarative base (infrastructure layer)."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# SQLite for now; kept swappable to PostgreSQL via a single URL change.
engine = create_engine("sqlite:///./aim_trainer.db", echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy ORM models."""
