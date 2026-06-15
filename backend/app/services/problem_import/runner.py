"""Orchestrates one import run: gather -> rank -> dedup -> map -> persist -> log.

Resilience contract: a single failing source or candidate is recorded and
skipped; it never aborts the run. Every run is written to ``problem_import_runs``
with terminal status ``success`` (no errors), ``partial`` (some errors but work
done), or ``failed`` (errors and nothing imported).
"""

import logging
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.models import DSAProblem, ProblemImportRun
from app.services.problem_import import ai_content
from app.services.problem_import.dedup import find_duplicate, slugify_title
from app.services.problem_import.ranking import rank_candidates
from app.services.problem_import.sources import ImportCandidate, ProblemSource
from app.services.problem_import.topic_map import TopicResolver

logger = logging.getLogger(__name__)


def run_import(
    session: Session,
    *,
    trigger: str = "manual",
    sources: list[ProblemSource] | None = None,
    created_by: int | None = None,
    daily_limit: int | None = None,
) -> ProblemImportRun:
    if sources is None:
        from app.services.problem_import.sources import default_daily_sources

        sources = default_daily_sources()
    if daily_limit is None:
        from app.config import settings

        daily_limit = settings.PROBLEM_IMPORT_DAILY_LIMIT

    run = ProblemImportRun(
        source=", ".join(s.name for s in sources)[:120],
        trigger=trigger,
        status="running",
        created_by=created_by,
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    errors: list[str] = []

    # 1. Gather candidates (each source guarded).
    candidates: list[ImportCandidate] = []
    for source in sources:
        try:
            fetched = source.fetch(session, limit=daily_limit)
            candidates.extend(fetched)
            logger.info("Source %s yielded %d candidates", source.name, len(fetched))
        except Exception as exc:  # noqa: BLE001 — one source can't break the run
            msg = f"Source {source.name} failed: {exc}"
            logger.error(msg)
            errors.append(msg)

    # 2. Rank (coverage gaps + difficulty + interview frequency).
    ranked = rank_candidates(session, candidates)

    # 3. Persist up to the daily limit, deduping + mapping topics.
    resolver = TopicResolver(session)
    imported = skipped = failed = 0
    for candidate in ranked:
        if imported >= daily_limit:
            break
        try:
            if _persist_candidate(session, candidate, resolver):
                imported += 1
            else:
                skipped += 1
        except _UnmappedTopic as exc:
            failed += 1
            errors.append(str(exc))
        except Exception as exc:  # noqa: BLE001
            failed += 1
            errors.append(f"Persist failed for {candidate.title!r}: {exc}")
            logger.exception("Persist failed for %r", candidate.title)

    # 4. Finalize the run.
    run.imported_count = imported
    run.skipped_duplicate_count = skipped
    run.failed_count = failed
    run.completed_at = datetime.utcnow()
    run.error_log = ("\n".join(errors))[:10_000] or None
    if errors and imported == 0:
        run.status = "failed"
    elif errors:
        run.status = "partial"
    else:
        run.status = "success"
    session.add(run)
    session.commit()
    session.refresh(run)
    logger.info(
        "Import run %s done: imported=%d skipped=%d failed=%d status=%s",
        run.id,
        imported,
        skipped,
        failed,
        run.status,
    )
    return run


class _UnmappedTopic(Exception):
    """Candidate's topic tag could not be resolved to a curriculum topic."""


def _persist_candidate(
    session: Session, candidate: ImportCandidate, resolver: TopicResolver
) -> bool:
    """Persist one candidate. Returns True if a new row was created, False if it
    was a duplicate (skipped). Raises _UnmappedTopic if the topic is unknown."""
    resolved = resolver.resolve(candidate.topic_tag)
    if resolved is None:
        raise _UnmappedTopic(
            f"Unmapped topic tag {candidate.topic_tag!r} for {candidate.title!r}"
        )
    topic_id, pattern_id = resolved

    title_slug = slugify_title(candidate.title)
    if find_duplicate(
        session,
        source_name=candidate.source_name,
        leetcode_slug=candidate.leetcode_slug,
        title_slug=title_slug,
        topic_id=topic_id,
    ):
        return False

    problem = DSAProblem(
        title=candidate.title,
        difficulty=candidate.difficulty,
        topic_id=topic_id,
        pattern_id=pattern_id,
        description=candidate.description,
        constraints_text=candidate.constraints_text,
        examples=candidate.examples or [],
        starter_code=candidate.starter_code,
        leetcode_slug=candidate.leetcode_slug,
        leetcode_url=candidate.leetcode_url,
        external_url=candidate.external_url,
        title_slug=title_slug,
        source_type=candidate.source_type,
        source_name=candidate.source_name,
        attribution=candidate.attribution,
        tags=candidate.tags or [],
        is_premium=candidate.is_premium,
        import_status="review_required",
        interview_frequency_score=candidate.interview_frequency_score,
        learning_priority_score=candidate.learning_priority_score,
    )
    session.add(problem)
    try:
        session.commit()
    except IntegrityError:
        # Lost a race against the partial unique index — treat as a duplicate.
        session.rollback()
        return False
    session.refresh(problem)

    # Cache an original AI learning pack when the source supplied one.
    if candidate.ai_learning_pack:
        try:
            ai_content.persist_learning_pack(
                session, problem.id, candidate.ai_learning_pack
            )
        except Exception as exc:  # noqa: BLE001 — pack is best-effort
            logger.warning("Could not cache learning pack for %s: %s", problem.id, exc)
    return True
