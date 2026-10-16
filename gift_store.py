"""SQLite persistence operations for pending gifts and their lifecycle."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping

BASE_DIR = Path(__file__).resolve().parent


def resolve_default_db_path() -> Path:
    """Return the configured database path, honoring the current environment override."""
    return Path(os.getenv("GIFT_DB_PATH", BASE_DIR / "gifting.db"))


def get_db_connection(db_path: str | os.PathLike | None = None) -> sqlite3.Connection:
    """Create a SQLite connection configured with row access by name."""
    resolved_path = Path(db_path) if db_path is not None else resolve_default_db_path()
    connection = sqlite3.connect(str(resolved_path))
    connection.row_factory = sqlite3.Row
    return connection


def init_database(db_path: str | os.PathLike | None = None) -> None:
    """Create persistent draft and active-gift tables without replacing existing data."""
    connection = get_db_connection(db_path)
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pending_gifts (
            session_id TEXT PRIMARY KEY,
            product_json TEXT,
            sender_name TEXT,
            recipient_name TEXT,
            personal_message TEXT,
            wrapping_style TEXT,
            scheduled_time TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS active_gifts (
            gift_token TEXT PRIMARY KEY,
            product_title TEXT,
            product_price TEXT,
            product_currency TEXT,
            product_image TEXT,
            product_brand TEXT,
            sender_name TEXT,
            recipient_name TEXT,
            personal_message TEXT,
            wrapping_style TEXT,
            scheduled_time TEXT,
            expires_at TEXT,
            claimed INTEGER,
            expired INTEGER,
            refunded INTEGER
        )
        """
    )
    connection.commit()
    connection.close()


def save_pending_gift(product_data: Mapping[str, Any], form_data: Mapping[str, Any], db_path=None) -> str:
    """Persist a gift draft before the sender confirms checkout."""
    session_id = str(uuid.uuid4())[:8]
    with get_db_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO pending_gifts (
                session_id,
                product_json,
                sender_name,
                recipient_name,
                personal_message,
                wrapping_style,
                scheduled_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                json.dumps(product_data),
                form_data.get("sender_name"),
                form_data.get("recipient_name"),
                form_data.get("personal_message"),
                form_data.get("wrapping_style"),
                form_data.get("scheduled_time"),
            ),
        )
    return session_id


def fetch_pending_gift(session_id: str, db_path=None):
    """Return the pending gift record for a checkout session if it exists."""
    with get_db_connection(db_path) as connection:
        return connection.execute(
            "SELECT * FROM pending_gifts WHERE session_id = ?",
            (session_id,),
        ).fetchone()


def save_active_gift(gift_data: Mapping[str, Any], db_path=None) -> str:
    """Create a shareable gift record with a 24-hour claim window and unique token."""
    gift_token = str(uuid.uuid4())[:8]
    expires_at = datetime.now() + timedelta(hours=24)
    product = gift_data["product"]

    with get_db_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO active_gifts (
                gift_token,
                product_title,
                product_price,
                product_currency,
                product_image,
                product_brand,
                sender_name,
                recipient_name,
                personal_message,
                wrapping_style,
                scheduled_time,
                expires_at,
                claimed,
                expired,
                refunded
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0)
            """,
            (
                gift_token,
                product.get("title"),
                str(product.get("final_price")),
                product.get("currency", "$"),
                str(product.get("image_url")),
                product.get("brand"),
                gift_data["sender_name"],
                gift_data["recipient_name"],
                gift_data["personal_message"],
                gift_data["wrapping_style"],
                gift_data["scheduled_time"],
                expires_at.strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
    return gift_token


def fetch_active_gift(gift_token: str, db_path=None):
    """Return the active gift record for a gift token."""
    with get_db_connection(db_path) as connection:
        return connection.execute(
            "SELECT * FROM active_gifts WHERE gift_token = ?",
            (gift_token,),
        ).fetchone()


def delete_pending_gift(session_id: str, db_path=None) -> None:
    """Remove a validated pending gift after checkout is complete."""
    with get_db_connection(db_path) as connection:
        connection.execute(
            "DELETE FROM pending_gifts WHERE session_id = ?",
            (session_id,),
        )


def mark_gift_claimed(gift_token: str, db_path=None) -> None:
    """Mark an active gift as claimed when the recipient opens it."""
    with get_db_connection(db_path) as connection:
        connection.execute(
            "UPDATE active_gifts SET claimed = 1 WHERE gift_token = ?",
            (gift_token,),
        )


def mark_gift_expired(gift_token: str, db_path=None) -> None:
    """Mark an active gift as expired and refunded when its time window is exceeded."""
    with get_db_connection(db_path) as connection:
        connection.execute(
            "UPDATE active_gifts SET expired = 1, refunded = 1 WHERE gift_token = ?",
            (gift_token,),
        )


def fetch_active_gifts_for_ussd(db_path=None):
    """Return up to three unclaimed gifts for the feature-phone menu."""
    with get_db_connection(db_path) as connection:
        return connection.execute(
            "SELECT * FROM active_gifts WHERE claimed = 0 LIMIT 3"
        ).fetchall()
