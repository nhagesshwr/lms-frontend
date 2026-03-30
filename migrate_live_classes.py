"""
Migration: upgrade live_classes table
Adds new columns and creates live_class_audience + live_class_enrollments (if missing).
Safe to run multiple times (uses IF NOT EXISTS / IF column does not exist pattern).
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.database import engine
from sqlalchemy import text

ALTER_STATEMENTS = [
    # ── live_classes: add new columns ─────────────────────────────────────────
    "ALTER TABLE live_classes ADD COLUMN IF NOT EXISTS description TEXT;",
    "ALTER TABLE live_classes ADD COLUMN IF NOT EXISTS meet_title VARCHAR;",
    "ALTER TABLE live_classes ADD COLUMN IF NOT EXISTS meet_url VARCHAR;",
    "ALTER TABLE live_classes ADD COLUMN IF NOT EXISTS audience_type VARCHAR DEFAULT 'all';",
    "ALTER TABLE live_classes ADD COLUMN IF NOT EXISTS course_id INTEGER REFERENCES courses(id) ON DELETE SET NULL;",
    "ALTER TABLE live_classes ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES employees(id) ON DELETE SET NULL;",

    # ── drop old column that was renamed ──────────────────────────────────────
    # (only if it still exists — harmless if already gone)
    'ALTER TABLE live_classes DROP COLUMN IF EXISTS "meetLink";',
    'ALTER TABLE live_classes DROP COLUMN IF EXISTS course;',

    # ── create live_class_enrollments if missing ───────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS live_class_enrollments (
        id SERIAL PRIMARY KEY,
        live_class_id INTEGER NOT NULL REFERENCES live_classes(id) ON DELETE CASCADE,
        employee_id   INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
        enrolled_at   TIMESTAMP DEFAULT NOW()
    );
    """,

    # ── create live_class_audience if missing ──────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS live_class_audience (
        id            SERIAL PRIMARY KEY,
        live_class_id INTEGER NOT NULL REFERENCES live_classes(id) ON DELETE CASCADE,
        employee_id   INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE
    );
    """,
]

def run():
    with engine.connect() as conn:
        for stmt in ALTER_STATEMENTS:
            stmt = stmt.strip()
            if not stmt:
                continue
            print(f"  → {stmt[:80]}{'…' if len(stmt) > 80 else ''}")
            conn.execute(text(stmt))
            conn.commit()
    print("\n✅ Migration complete.")

if __name__ == "__main__":
    run()
