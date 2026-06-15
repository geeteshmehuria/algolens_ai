"""Standalone, idempotent DSA curriculum seeder.

Run from backend/:
    .venv\\Scripts\\python.exe seed_curriculum.py

Safe to run repeatedly — upserts topics by slug, never deletes user data.
Requires the 0006 migration to be applied first (alembic upgrade head).
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlmodel import Session  # noqa: E402

from app.database import engine  # noqa: E402
from app.seed.curriculum import seed_curriculum  # noqa: E402


def main() -> None:
    print("Seeding DSA curriculum into dsa_topics (idempotent)...")
    with Session(engine) as session:
        stats = seed_curriculum(session)
    print(
        "Done. "
        f"created={stats['created']} updated={stats['updated']} "
        f"default_patterns_created={stats['patterns_created']} "
        f"total_topics={stats['total']}"
    )


if __name__ == "__main__":
    main()
