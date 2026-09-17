"""
database.py — SQLAlchemy engine and session management.
Provides both sync and async session factories.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import settings


# ── Declarative base ─────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ── Sync engine (used by tools, seed, and general queries) ────────

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,        # verify connection before use
    pool_recycle=3600,         # recycle connections after 1h
    pool_size=10,
    max_overflow=20,
    echo=settings.app_env == "development",
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


# ── Session context managers ──────────────────────────────────────

@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Yield a database session and handle commit/rollback."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a session."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── Database initialization ───────────────────────────────────────

def init_db() -> None:
    """Create all tables if they don't exist."""
    # Import models so Base knows about them
    import backend.models  # noqa: F401
    Base.metadata.create_all(bind=engine)


def health_check() -> bool:
    """Return True if the database is reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
