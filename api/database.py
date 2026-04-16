"""
SQLAlchemy database setup and ORM table definitions.

Tables
------
loads       — available freight loads on the board
call_logs   — record of every inbound carrier call handled by the AI agent
"""

from __future__ import annotations

import os
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/carrier_sales.db")

# SQLite-specific: enable WAL mode and foreign keys via connect_args
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# ORM models
# ---------------------------------------------------------------------------

class LoadORM(Base):
    __tablename__ = "loads"

    load_id = Column(String, primary_key=True, index=True)
    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    equipment_type = Column(String, nullable=False)
    weight_lbs = Column(Integer, nullable=False)
    miles = Column(Integer, nullable=False)
    rate_usd = Column(Float, nullable=False)
    commodity = Column(String, nullable=False)
    pickup_date = Column(DateTime, nullable=False)
    delivery_date = Column(DateTime, nullable=False)
    available = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class CallLogORM(Base):
    __tablename__ = "call_logs"

    call_id = Column(String, primary_key=True, index=True)
    mc_number = Column(String, nullable=False, index=True)
    carrier_name = Column(String, nullable=False)
    load_id = Column(String, nullable=True)
    initial_rate_offered = Column(Float, nullable=False)
    final_agreed_rate = Column(Float, nullable=True)
    num_negotiation_rounds = Column(Integer, nullable=False)
    outcome = Column(String, nullable=False)
    sentiment = Column(String, nullable=False)
    call_duration_seconds = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    notes = Column(Text, nullable=True)
    # AI enrichment fields — populated via POST /calls/enrich after the call
    negotiation_summary = Column(Text, nullable=True)
    ai_sentiment = Column(String, nullable=True)
    ai_confidence = Column(Float, nullable=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_tables() -> None:
    """Create all tables if they don't already exist."""
    Base.metadata.create_all(bind=engine)


def drop_tables() -> None:
    """Drop all tables. Used by --reset in seed_data to apply schema changes."""
    Base.metadata.drop_all(bind=engine)


def migrate_tables(engine) -> None:
    """Add new columns to existing tables if they don't exist.

    Safe to call on every startup — checks column existence before altering,
    so it is a no-op when the schema is already current.
    """
    with engine.connect() as conn:
        # Get existing columns in call_logs
        result = conn.execute(text("PRAGMA table_info(call_logs)"))
        existing_columns = [row[1] for row in result.fetchall()]

        # Add missing columns
        migrations = [
            ("negotiation_summary", "TEXT"),
            ("ai_sentiment", "VARCHAR"),
            ("ai_confidence", "FLOAT"),
        ]

        for col_name, col_type in migrations:
            if col_name not in existing_columns:
                conn.execute(text(
                    f"ALTER TABLE call_logs ADD COLUMN {col_name} {col_type}"
                ))
                conn.commit()
                print(f"Migration: added column {col_name} to call_logs")


def get_db():
    """FastAPI dependency that yields a DB session and closes it after use."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
