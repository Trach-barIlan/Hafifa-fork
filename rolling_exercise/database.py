"""Database configuration and session management for the Air Quality API."""

import sqlite3
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import settings

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=settings.debug,
)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key constraints for SQLite connections."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""

    pass


def get_db() -> Generator[Session, None, None]:
    """Dependency generator that provides a transactional database session.

    Yields:
        Session: Active SQLAlchemy database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all database tables defined in the ORM models."""
    Base.metadata.create_all(bind=engine)
