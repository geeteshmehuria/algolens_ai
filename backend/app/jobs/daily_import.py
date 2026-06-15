"""Daily problem-import job.

Run by an external scheduler (Windows Task Scheduler locally; a Render or
GitHub-Actions cron in production):

    backend\\.venv\\Scripts\\python.exe -m app.jobs.daily_import

Imports up to PROBLEM_IMPORT_DAILY_LIMIT problems from the safe default sources
(curated public lists + AI-generated original practice; live LeetCode only if
explicitly enabled), all landing as ``review_required`` for admin publishing.
Exits non-zero if the run hard-fails, so the scheduler can surface the failure.
"""

import logging
import sys

from sqlmodel import Session

from app.database import engine
from app.services.problem_import.runner import run_import

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("daily_import")


def main() -> int:
    logger.info("Starting daily problem import...")
    try:
        with Session(engine) as session:
            run = run_import(session, trigger="daily")
    except Exception:  # noqa: BLE001 — top-level guard so cron gets a clean exit code
        logger.exception("Daily import crashed")
        return 1

    print(
        f"Daily import #{run.id}: status={run.status} "
        f"imported={run.imported_count} "
        f"skipped_duplicate={run.skipped_duplicate_count} "
        f"failed={run.failed_count}"
    )
    if run.error_log:
        print("Errors:\n" + run.error_log)
    return 0 if run.status in ("success", "partial") else 1


if __name__ == "__main__":
    sys.exit(main())
