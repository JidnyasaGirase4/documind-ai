"""Connectivity helpers. The schema itself is managed by Alembic migrations, never create_all()."""

from sqlalchemy import text

from app.db.session import engine


def check_database() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
