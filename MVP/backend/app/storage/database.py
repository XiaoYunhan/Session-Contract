"""Database setup and connection management."""
import sqlite3
from contextlib import contextmanager
from typing import Generator
import os


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./session_contracts.db")


def get_db_path() -> str:
    """Extract file path from DATABASE_URL."""
    if DATABASE_URL.startswith("sqlite:///"):
        return DATABASE_URL.replace("sqlite:///", "")
    return DATABASE_URL


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Get database connection context manager."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Initialize database schema."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Events table (append-only event store)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_session
            ON events(session_id, sequence)
        """)

        # Sessions table (projection)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                legs TEXT NOT NULL,
                basket_q TEXT NOT NULL,
                t1 TEXT,
                t2 TEXT,
                status TEXT NOT NULL,
                start_mode TEXT NOT NULL,
                end_mode TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # Participants table (projection)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS participants (
                participant_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                name TEXT,
                joined_at TEXT NOT NULL,
                PRIMARY KEY (participant_id, session_id)
            )
        """)

        # Allocations table (projection, current state)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS allocations (
                session_id TEXT NOT NULL,
                participant_id TEXT NOT NULL,
                leg TEXT NOT NULL,
                amount REAL NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (session_id, participant_id, leg)
            )
        """)

        # RFQs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rfqs (
                rfq_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                requester_id TEXT NOT NULL,
                leg_from TEXT NOT NULL,
                leg_to TEXT NOT NULL,
                amount_from REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT
            )
        """)

        # Quotes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                quote_id TEXT PRIMARY KEY,
                rfq_id TEXT NOT NULL,
                quoter_id TEXT NOT NULL,
                rate REAL NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT
            )
        """)

        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                rfq_id TEXT NOT NULL,
                quote_id TEXT NOT NULL,
                participant_a TEXT NOT NULL,
                participant_b TEXT NOT NULL,
                leg_from TEXT NOT NULL,
                leg_to TEXT NOT NULL,
                amount_from REAL NOT NULL,
                amount_to REAL NOT NULL,
                executed_at TEXT NOT NULL
            )
        """)

        # Orders table (new order-based trading)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                participant_id TEXT NOT NULL,
                asset TEXT NOT NULL,
                side TEXT NOT NULL,
                order_type TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL,
                filled_quantity REAL DEFAULT 0,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_orders_session_asset
            ON orders(session_id, asset, status)
        """)

        # Price ticks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_ticks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                leg TEXT NOT NULL,
                price REAL NOT NULL
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_price_ticks_session
            ON price_ticks(session_id, timestamp DESC)
        """)

        # Settlements table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settlements (
                session_id TEXT PRIMARY KEY,
                settlement_prices TEXT NOT NULL,
                payouts TEXT NOT NULL,
                settled_at TEXT NOT NULL
            )
        """)

        conn.commit()
