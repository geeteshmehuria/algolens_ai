"""Problem source adapters.

Each adapter yields normalized ``ImportCandidate`` objects. Adapters must be
defensive — a network/parse failure should surface as an empty list plus a log,
never an exception that aborts the whole run (the runner also guards each call).

Legal rule baked in here: only public metadata (title/difficulty/topic/slug/URL)
or our OWN original AI content is ever produced. Third-party problem statements,
editorials, hidden tests and premium/company data are never fetched or stored.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Protocol

from sqlmodel import Session

from app.config import settings

logger = logging.getLogger(__name__)

_CURATED_DIR = Path(__file__).resolve().parents[2] / "seed" / "curated_lists"

# Our own neutral, original placeholder for problems whose statement we may not
# reproduce (curated lists / LeetCode metadata). Points users to the source link.
_METADATA_DESCRIPTION = (
    "This problem is indexed for practice from a public interview list. "
    "AlgoLens does not reproduce third-party problem statements — open the "
    "original problem via the source link above. Use **Generate learning notes** "
    "for an original AlgoLens explanation, approach, and hints."
)

_VALID_DIFFICULTY = {"easy": "Easy", "medium": "Medium", "hard": "Hard"}


@dataclass
class ImportCandidate:
    """A normalized, source-agnostic problem ready for dedup + persistence."""

    title: str
    difficulty: str  # Easy | Medium | Hard
    topic_tag: str
    source_type: str  # curated_list | ai_generated | manual | leetcode
    source_name: str
    leetcode_slug: Optional[str] = None
    leetcode_url: Optional[str] = None
    external_url: Optional[str] = None
    attribution: Optional[str] = None
    is_premium: bool = False
    interview_frequency_score: Optional[float] = None
    tags: list[str] = field(default_factory=list)
    description: str = _METADATA_DESCRIPTION
    constraints_text: Optional[str] = None
    examples: list[dict] = field(default_factory=list)
    starter_code: Optional[str] = None
    # An optional original AI learning pack to cache alongside the problem.
    ai_learning_pack: Optional[dict] = None
    # Filled in by ranking.rank_candidates.
    learning_priority_score: Optional[float] = None


def _normalize_difficulty(value: str) -> Optional[str]:
    return _VALID_DIFFICULTY.get((value or "").strip().lower())


class ProblemSource(Protocol):
    name: str

    def fetch(self, session: Session, limit: int) -> list[ImportCandidate]: ...


class CuratedListSource:
    """Loads a bundled public interview list (metadata only) by file name."""

    def __init__(self, list_name: str):
        self.list_name = list_name
        self.name = f"curated:{list_name}"

    def fetch(self, session: Session, limit: int) -> list[ImportCandidate]:
        path = _CURATED_DIR / f"{self.list_name}.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("Curated list %s could not be loaded: %s", path, exc)
            return []

        attribution = data.get("attribution", self.list_name)
        source_name = data.get("source_name", self.list_name)
        candidates: list[ImportCandidate] = []
        for entry in data.get("problems", []):
            difficulty = _normalize_difficulty(entry.get("difficulty", ""))
            slug = entry.get("slug")
            title = entry.get("title")
            topic = entry.get("topic")
            if not (difficulty and slug and title and topic):
                logger.warning("Skipping malformed curated entry: %r", entry)
                continue
            # Never import problems flagged premium — metadata may be restricted.
            if entry.get("premium"):
                continue
            url = entry.get("url") or f"https://leetcode.com/problems/{slug}/"
            candidates.append(
                ImportCandidate(
                    title=title,
                    difficulty=difficulty,
                    topic_tag=topic,
                    source_type="curated_list",
                    source_name=source_name,
                    leetcode_slug=slug,
                    leetcode_url=url,
                    external_url=url,
                    attribution=attribution,
                    interview_frequency_score=entry.get("interview_frequency_score"),
                    tags=[topic],
                )
            )
        return candidates


class ManualUploadSource:
    """Wraps pre-parsed, validated entries from an admin CSV/JSON upload."""

    def __init__(self, entries: list[dict], source_name: str = "manual_upload"):
        self.entries = entries
        self.source_name = source_name
        self.name = f"manual:{source_name}"

    def fetch(self, session: Session, limit: int) -> list[ImportCandidate]:
        candidates: list[ImportCandidate] = []
        for entry in self.entries:
            difficulty = _normalize_difficulty(entry.get("difficulty", ""))
            title = entry.get("title")
            topic = entry.get("topic")
            if not (difficulty and title and topic):
                logger.warning("Skipping malformed manual entry: %r", entry)
                continue
            slug = entry.get("slug")
            url = entry.get("url")
            candidates.append(
                ImportCandidate(
                    title=title,
                    difficulty=difficulty,
                    topic_tag=topic,
                    source_type="manual",
                    source_name=self.source_name,
                    leetcode_slug=slug,
                    leetcode_url=url,
                    external_url=url,
                    attribution=entry.get("attribution", "Manual admin upload"),
                    interview_frequency_score=entry.get("interview_frequency_score"),
                    tags=[topic],
                    description=entry.get("description") or _METADATA_DESCRIPTION,
                )
            )
        return candidates


class AIGeneratedSource:
    """Generates ORIGINAL beginner/intermediate practice for under-covered topics.

    Nothing is copied: Gemini produces a brand-new problem statement plus a
    learning pack, validated as strict JSON. Disabled if the API key is missing
    or PROBLEM_IMPORT_AI_ENABLED is false.
    """

    name = "ai_generated"

    def fetch(self, session: Session, limit: int) -> list[ImportCandidate]:
        if not settings.PROBLEM_IMPORT_AI_ENABLED:
            logger.info("AI-generated source disabled via PROBLEM_IMPORT_AI_ENABLED")
            return []
        # Imported lazily to avoid a hard dependency / import cycle at module load.
        from app.services.ai_service import ai_available
        from app.services.problem_import import ai_content
        from app.services.problem_import.ranking import coverage_snapshot

        if not ai_available():
            logger.info("AI-generated source skipped — no Gemini API key configured")
            return []

        # Target the most under-covered categories first.
        gaps = [row for row in coverage_snapshot(session) if row["gap"] > 0]
        candidates: list[ImportCandidate] = []
        for row in gaps[: max(1, limit)]:
            try:
                pack = ai_content.generate_practice_problem(row["category"])
            except Exception as exc:  # never let one generation abort the source
                logger.warning(
                    "AI practice generation failed for %s: %s", row["category"], exc
                )
                continue
            candidates.append(_candidate_from_ai(pack, row["category"]))
            if len(candidates) >= limit:
                break
        return candidates


def _candidate_from_ai(pack: dict[str, Any], category: str) -> ImportCandidate:
    return ImportCandidate(
        title=pack["title"],
        difficulty=pack["difficulty"],
        topic_tag=category,
        source_type="ai_generated",
        source_name="algolens_ai",
        attribution="Original practice problem generated by AlgoLens AI",
        tags=[category],
        description=pack["description"],
        constraints_text=pack.get("constraints"),
        examples=pack.get("examples", []),
        starter_code=pack.get("starter_code"),
        ai_learning_pack=pack.get("learning_pack"),
    )


class LeetCodeMetadataSource:
    """Live public-metadata adapter — DISABLED by default.

    Automated access to LeetCode is legally grey even for metadata, so this is
    gated behind PROBLEM_IMPORT_LEETCODE_ENABLED (default false). When enabled it
    fetches ONLY public metadata (title/difficulty/topic tags/slug) and never
    statements, editorials, hidden tests, or premium/company data.
    """

    name = "leetcode_metadata"

    def fetch(self, session: Session, limit: int) -> list[ImportCandidate]:
        if not settings.PROBLEM_IMPORT_LEETCODE_ENABLED:
            logger.info(
                "LeetCode metadata source disabled "
                "(set PROBLEM_IMPORT_LEETCODE_ENABLED=true to enable, "
                "understanding the legal trade-off)."
            )
            return []
        try:
            return self._fetch_public_metadata(limit)
        except Exception as exc:  # defensive: never abort the run
            logger.error("LeetCode metadata fetch failed: %s", exc)
            return []

    def _fetch_public_metadata(self, limit: int) -> list[ImportCandidate]:
        """Fetch public problem metadata via LeetCode's GraphQL endpoint.

        Metadata only. Uses the stdlib so no new dependency is required.
        """
        import urllib.request

        query = {
            "query": (
                "query problemsetQuestionList($categorySlug: String, $limit: Int, "
                "$skip: Int, $filters: QuestionListFilterInput) {"
                " problemsetQuestionList: questionList(categorySlug: $categorySlug, "
                "limit: $limit, skip: $skip, filters: $filters) { questions {"
                " title titleSlug difficulty paidOnly topicTags { slug } } } }"
            ),
            "variables": {
                "categorySlug": "",
                "skip": 0,
                "limit": max(1, min(limit, 50)),
                "filters": {},
            },
        }
        req = urllib.request.Request(
            "https://leetcode.com/graphql",
            data=json.dumps(query).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "AlgoLens-AI/1.0 (metadata import)",
                "Referer": "https://leetcode.com",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:  # nosec - opt-in only
            payload = json.loads(resp.read().decode("utf-8"))

        questions = (
            payload.get("data", {})
            .get("problemsetQuestionList", {})
            .get("questions", [])
        )
        candidates: list[ImportCandidate] = []
        for q in questions:
            if q.get("paidOnly"):
                continue  # never touch premium content
            difficulty = _normalize_difficulty(q.get("difficulty", ""))
            slug = q.get("titleSlug")
            title = q.get("title")
            tags = [t.get("slug") for t in q.get("topicTags", []) if t.get("slug")]
            if not (difficulty and slug and title and tags):
                continue
            url = f"https://leetcode.com/problems/{slug}/"
            candidates.append(
                ImportCandidate(
                    title=title,
                    difficulty=difficulty,
                    topic_tag=tags[0],
                    source_type="leetcode",
                    source_name="leetcode",
                    leetcode_slug=slug,
                    leetcode_url=url,
                    external_url=url,
                    attribution="Public metadata from LeetCode (statement not reproduced)",
                    tags=tags,
                )
            )
        return candidates


def default_daily_sources() -> list[ProblemSource]:
    """Sources the daily job pulls from (safe set: no live LeetCode by default)."""
    return [
        CuratedListSource("blind75"),
        CuratedListSource("grind75"),
        AIGeneratedSource(),
        LeetCodeMetadataSource(),  # no-op unless explicitly enabled
    ]
