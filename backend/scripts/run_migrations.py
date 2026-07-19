"""Apply pending SQL migrations from backend/migrations/*.sql.

Usage:
    python scripts/run_migrations.py

Reads DATABASE_URL from the environment.  Safe to run multiple times —
each migration file is applied at most once, recorded in
chat.schema_migrations(filename TEXT PRIMARY KEY, applied_at TIMESTAMPTZ).
"""
from __future__ import annotations

import os
import pathlib
import sys

import psycopg2
import psycopg2.extensions

DSN = os.environ.get("DATABASE_URL", "postgresql://querio:querio@localhost:5432/querio")

_MIGRATIONS_DIR = pathlib.Path(__file__).parent.parent / "migrations"

_ENSURE_TRACKER = """
CREATE SCHEMA IF NOT EXISTS chat;
CREATE TABLE IF NOT EXISTS chat.schema_migrations (
    filename   TEXT        PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def run_migrations() -> None:
    """Apply all pending .sql files under backend/migrations/ in sorted order."""
    conn: psycopg2.extensions.connection = psycopg2.connect(DSN)
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            # Bootstrap the tracker table (idempotent).
            cur.execute(_ENSURE_TRACKER)
            conn.commit()

            sql_files = sorted(_MIGRATIONS_DIR.glob("*.sql"))
            if not sql_files:
                print("No migration files found in", _MIGRATIONS_DIR)
                return

            for sql_file in sql_files:
                filename = sql_file.name
                cur.execute(
                    "SELECT 1 FROM chat.schema_migrations WHERE filename = %s",
                    (filename,),
                )
                if cur.fetchone() is not None:
                    print(f"[skip] {filename} (already applied)")
                    continue

                print(f"[apply] {filename}")
                sql_text = sql_file.read_text(encoding="utf-8")
                try:
                    cur.execute(sql_text)
                    cur.execute(
                        "INSERT INTO chat.schema_migrations (filename) VALUES (%s)",
                        (filename,),
                    )
                    conn.commit()
                    print(f"[done]  {filename}")
                except Exception as exc:
                    conn.rollback()
                    print(f"[FAIL]  {filename}: {exc}", file=sys.stderr)
                    raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migrations()
