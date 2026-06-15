"""Map a source's free-text topic tag onto a real (topic_id, pattern_id).

Imported problems carry a coarse tag like ``"arrays"`` or ``"dynamic-programming"``.
``DSAProblem`` requires a NOT-NULL ``topic_id`` and ``pattern_id``, so we resolve
each tag to a representative curriculum topic (the lowest-``learning_order`` topic
in the matching category) and that topic's first pattern. Every topic is
guaranteed at least one pattern by ``app.seed.curriculum._ensure_default_patterns``.

Unmappable tags return ``None`` — the runner skips the candidate and logs it
rather than crashing the whole import.
"""

from sqlmodel import Session, select

from app.models import DSAPattern, DSATopic
from app.services.problem_import.dedup import slugify_title

# Coarse import tags (slugified) -> curriculum category name. Keeps the curated
# lists / AI prompts working in terms of familiar interview tags while pointing
# at the real category rows seeded by app/seed/curriculum_data.py.
TAG_TO_CATEGORY: dict[str, str] = {
    "array": "Arrays",
    "arrays": "Arrays",
    "two-pointers": "Arrays",
    "sliding-window": "Arrays",
    "prefix-sum": "Arrays",
    "matrix": "Arrays",
    "string": "Strings",
    "strings": "Strings",
    "hashing": "Hashing",
    "hash-table": "Hashing",
    "hashmap": "Hashing",
    "stack": "Stack",
    "monotonic-stack": "Stack",
    "queue": "Queue and Deque",
    "deque": "Queue and Deque",
    "linked-list": "Linked List",
    "binary-search": "Searching",
    "searching": "Searching",
    "sorting": "Sorting",
    "tree": "Trees",
    "trees": "Trees",
    "binary-tree": "Trees",
    "bst": "Binary Search Tree",
    "binary-search-tree": "Binary Search Tree",
    "heap": "Heap / Priority Queue",
    "priority-queue": "Heap / Priority Queue",
    "graph": "Graphs",
    "graphs": "Graphs",
    "dynamic-programming": "Dynamic Programming",
    "dp": "Dynamic Programming",
    "greedy": "Greedy Algorithms",
    "intervals": "Intervals",
    "trie": "Tries",
    "tries": "Tries",
    "backtracking": "Recursion and Backtracking",
    "recursion": "Recursion and Backtracking",
    "bit-manipulation": "Bit Manipulation",
    "bit": "Bit Manipulation",
    "math": "Math for DSA",
    "design": "Design / System-style Coding",
}


class TopicResolver:
    """Caches topic/pattern lookups for the duration of one import run."""

    def __init__(self, session: Session):
        self.session = session
        topics = session.exec(select(DSATopic).where(DSATopic.is_active == True)).all()  # noqa: E712
        self._by_slug = {t.slug: t for t in topics if t.slug}
        self._by_name = {t.name: t for t in topics}
        # Representative topic per category = lowest learning_order (then name).
        self._by_category: dict[str, DSATopic] = {}
        for t in sorted(topics, key=lambda x: (x.learning_order or 10**6, x.name)):
            if t.category and t.category not in self._by_category:
                self._by_category[t.category] = t
        self._pattern_cache: dict[int, int | None] = {}

    def _first_pattern_id(self, topic_id: int) -> int | None:
        if topic_id not in self._pattern_cache:
            pattern = self.session.exec(
                select(DSAPattern)
                .where(DSAPattern.topic_id == topic_id)
                .order_by(DSAPattern.id)
            ).first()
            self._pattern_cache[topic_id] = pattern.id if pattern else None
        return self._pattern_cache[topic_id]

    def resolve(self, tag: str) -> tuple[int, int] | None:
        """Return (topic_id, pattern_id) for a tag, or None if unmappable."""
        slug = slugify_title(tag)
        topic: DSATopic | None = None

        category = TAG_TO_CATEGORY.get(slug)
        if category:
            topic = self._by_category.get(category)
        if topic is None:
            topic = self._by_slug.get(slug) or self._by_name.get(tag)
        # Last resort: a category whose name slugifies to the tag.
        if topic is None:
            for cat_name, cat_topic in self._by_category.items():
                if slugify_title(cat_name) == slug:
                    topic = cat_topic
                    break

        if topic is None or topic.id is None:
            return None
        pattern_id = self._first_pattern_id(topic.id)
        if pattern_id is None:
            return None
        return topic.id, pattern_id
