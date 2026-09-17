"""
seed.py — Database seeding script for OpsPilot.
Run directly: python backend/seed.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import structlog

log = structlog.get_logger(__name__)


def run_seed() -> str:
    """Execute seed.sql against the configured MySQL database."""
    from backend.database import engine

    seed_file = Path(__file__).parent.parent / "data" / "seed.sql"
    if not seed_file.exists():
        return f"Seed file not found: {seed_file}"

    sql = seed_file.read_text(encoding="utf-8")

    # Strip line comments before splitting
    cleaned_lines = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--") or stripped.startswith("/*"):
            continue
        cleaned_lines.append(line)
    cleaned_sql = "\n".join(cleaned_lines)

    # Split into individual statements
    statements = [s.strip() for s in cleaned_sql.split(";") if s.strip()]

    from sqlalchemy import text
    with engine.begin() as conn:
        # Disable FK checks during seeding
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        errors = []
        for stmt in statements:
            if not stmt:
                continue
            try:
                conn.execute(text(stmt))
            except Exception as e:
                if "Duplicate entry" not in str(e):
                    errors.append(str(e)[:100])
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))

    if errors:
        return f"Seed completed with {len(errors)} errors: {errors[:3]}"
    return "Seed completed successfully"


if __name__ == "__main__":
    # Bootstrap path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from backend.database import init_db
    init_db()
    result = run_seed()
    print(result)
