# app/services/ai_service.py
"""Google Gemini integration for AlgoLens AI.

All functions return plain dicts shaped exactly like the frontend expects.
Raises AIUnavailableError when no API key is configured and AIGenerationError
when the model call or response parsing fails — routers translate these into
honest HTTP errors instead of serving fake data.
"""

import json
import re
from typing import Any, Dict, Optional

from app.config import settings
from app.models import DSAProblem


class AIUnavailableError(Exception):
    """Raised when AI features are requested but no Gemini API key is configured."""


class AIGenerationError(Exception):
    """Raised when Gemini returns an unusable response."""


# Animation types the frontend knows how to render. Each entry documents the
# exact per-step JSON contract the Svelte renderer expects.
ANIMATION_CONTRACTS = {
    "hash_map_array": (
        'input: {"array": [numbers], "target": number or null}\n'
        'step: {"index": int (current array index), "current": number, '
        '"map": {seen value -> index}, "action": str, "result": str, "pseudocode_line": int}'
    ),
    "two_pointers": (
        'input: {"array": [numbers or chars]}\n'
        'step: {"left": int, "right": int, "found": [int,int] or null, '
        '"action": str, "result": str, "pseudocode_line": int}'
    ),
    "sliding_window": (
        'input: {"array": [numbers or single chars]}\n'
        'step: {"window_start": int, "window_end": int, "state": str (window contents/sum summary), '
        '"action": str, "result": str, "pseudocode_line": int}'
    ),
    "binary_search": (
        'input: {"array": [sorted numbers], "target": number}\n'
        'step: {"low": int, "mid": int or null, "high": int, "eliminated": [ints, indices ruled out so far], '
        '"found": int or null, "action": str, "result": str, "pseudocode_line": int}'
    ),
    "stack": (
        'input: {"array": [single chars or numbers being processed left to right]}\n'
        'step: {"cursor": int (index in input being read), "op": "push"|"pop"|"skip", "value": str, '
        '"stack": [current stack bottom to top], "action": str, "result": str, "pseudocode_line": int}'
    ),
}

# Map seeded pattern/topic names onto a renderable animation type.
_PATTERN_TO_ANIMATION = [
    (re.compile(r"hash|prefix", re.I), "hash_map_array"),
    (re.compile(r"two\s*pointer|palindrome", re.I), "two_pointers"),
    (re.compile(r"sliding|window", re.I), "sliding_window"),
    (re.compile(r"binary\s*search", re.I), "binary_search"),
    (re.compile(r"stack|bracket|parenthes", re.I), "stack"),
]


def ai_available() -> bool:
    key = settings.GOOGLE_GEMINI_API_KEY
    return bool(key) and key != "your_gemini_api_key_here"


_client = None


def _get_client():
    global _client
    if _client is None:
        from google import genai

        _client = genai.Client(api_key=settings.GOOGLE_GEMINI_API_KEY)
    return _client


def _generate_json(prompt: str, temperature: float = 0.3) -> Dict[str, Any]:
    """Call Gemini asking for JSON and parse it defensively."""
    if not ai_available():
        raise AIUnavailableError(
            "AI features are disabled. Set GOOGLE_GEMINI_API_KEY in backend/.env "
            "(get a free key at https://aistudio.google.com/)."
        )
    try:
        client = _get_client()
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "temperature": temperature,
            },
        )
        text = response.text or ""
    except Exception as exc:  # network, quota, auth — surface as one error type
        raise AIGenerationError(f"Gemini request failed: {exc}") from exc

    # Strip markdown fences if the model added them despite the mime type.
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise AIGenerationError(f"Gemini returned invalid JSON: {text[:200]}") from exc


def _problem_context(
    problem: DSAProblem, topic_name: str = "", pattern_name: str = ""
) -> str:
    examples = json.dumps(problem.examples or [], indent=2)
    return (
        f"Problem title: {problem.title}\n"
        f"Difficulty: {problem.difficulty}\n"
        f"Topic: {topic_name or 'unknown'}\n"
        f"Pattern: {pattern_name or 'unknown'}\n"
        f"Statement:\n{problem.description}\n\n"
        f"Constraints:\n{problem.constraints_text or 'not specified'}\n\n"
        f"Examples:\n{examples}\n"
    )


_TUTOR_RULES = (
    "You are a DSA tutor inside the AlgoLens learning platform. Your goal is to build "
    "understanding, not to hand out answers. Be technically accurate; never invent "
    "constraints or complexities. Audience: a learner who knows basic Python. "
    "Respond ONLY with valid JSON matching the requested schema — no markdown, no prose outside JSON."
)


def generate_explanation(
    problem: DSAProblem, topic_name: str = "", pattern_name: str = ""
) -> Dict[str, Any]:
    prompt = (
        f"{_TUTOR_RULES}\n\n{_problem_context(problem, topic_name, pattern_name)}\n"
        "Produce a structured explanation as JSON with EXACTLY these keys:\n"
        "{\n"
        '  "simple_explanation": "2-3 sentences, plain language, what the problem really asks",\n'
        '  "brute_force": "the obvious approach and why it is slow, with its big-O",\n'
        '  "optimized_approach": "the key insight first, then the approach, with its big-O",\n'
        '  "pseudocode": ["one line per step of the OPTIMIZED approach, max 12 lines"],\n'
        '  "time_complexity": "O(...) of the optimized approach",\n'
        '  "space_complexity": "O(...) of the optimized approach",\n'
        '  "common_mistakes": ["2-4 realistic mistakes learners make on this problem"],\n'
        '  "pattern": "the algorithmic pattern name"\n'
        "}"
    )
    data = _generate_json(prompt)
    required = [
        "simple_explanation",
        "brute_force",
        "optimized_approach",
        "pseudocode",
        "time_complexity",
        "space_complexity",
        "common_mistakes",
        "pattern",
    ]
    missing = [k for k in required if k not in data]
    if missing:
        raise AIGenerationError(f"Explanation response missing keys: {missing}")
    if not isinstance(data["pseudocode"], list):
        data["pseudocode"] = [str(data["pseudocode"])]
    if not isinstance(data["common_mistakes"], list):
        data["common_mistakes"] = [str(data["common_mistakes"])]
    return data


def pick_animation_type(pattern_name: str, topic_name: str = "") -> str:
    for regex, anim_type in _PATTERN_TO_ANIMATION:
        if regex.search(pattern_name or "") or regex.search(topic_name or ""):
            return anim_type
    return "hash_map_array"


def generate_animation(
    problem: DSAProblem,
    topic_name: str = "",
    pattern_name: str = "",
    pseudocode: Optional[list] = None,
) -> Dict[str, Any]:
    anim_type = pick_animation_type(pattern_name, topic_name)
    contract = ANIMATION_CONTRACTS[anim_type]
    pseudo_section = ""
    if pseudocode:
        numbered = "\n".join(f"{i + 1}. {line}" for i, line in enumerate(pseudocode))
        pseudo_section = (
            f"\nThe pseudocode shown to the learner (use these 1-based line numbers "
            f"for every step's pseudocode_line):\n{numbered}\n"
        )
    prompt = (
        f"{_TUTOR_RULES}\n\n{_problem_context(problem, topic_name, pattern_name)}{pseudo_section}\n"
        f"Create a step-by-step visual trace of the OPTIMIZED algorithm on a SMALL concrete input "
        f"(5-8 elements, ideally taken from the problem's first example).\n"
        f'The animation type is "{anim_type}". Follow this JSON contract exactly:\n{contract}\n\n'
        "Return JSON with EXACTLY these keys:\n"
        "{\n"
        f'  "animation_type": "{anim_type}",\n'
        '  "input": { ...as per contract... },\n'
        '  "steps": [ 6-14 step objects as per contract, each describing ONE state of the algorithm ]\n'
        "}\n"
        "Rules: every step must contain valid indices for the chosen input; the final step must show "
        "the conclusion; action describes what is being checked, result describes the outcome."
    )
    data = _generate_json(prompt)
    if data.get("animation_type") not in ANIMATION_CONTRACTS:
        data["animation_type"] = anim_type
    if (
        not isinstance(data.get("steps"), list)
        or not data["steps"]
        or not isinstance(data.get("input"), dict)
    ):
        raise AIGenerationError("Animation response missing usable 'input' or 'steps'.")
    return data


def review_code(
    problem: DSAProblem,
    submitted_code: str,
    topic_name: str = "",
    pattern_name: str = "",
) -> Dict[str, Any]:
    prompt = (
        f"{_TUTOR_RULES}\n\n{_problem_context(problem, topic_name, pattern_name)}\n"
        f"The learner submitted this Python code:\n```python\n{submitted_code[:6000]}\n```\n\n"
        "Review it against the problem spec WITHOUT executing it. Judge logic, not style. "
        "Do not rewrite the full solution — guide the fix. Return JSON with EXACTLY these keys:\n"
        "{\n"
        '  "is_correct": true/false (would it pass all valid inputs?),\n'
        '  "logic_feedback": "2-4 sentences on the approach taken and its soundness",\n'
        '  "bugs": ["each concrete bug with the reason, [] if none"],\n'
        '  "missed_edge_cases": ["edge cases this code mishandles, [] if none"],\n'
        '  "better_approach": "one short paragraph: how to improve, or confirmation it is optimal",\n'
        '  "dsa_pattern": "pattern the submitted code actually uses",\n'
        '  "time_complexity": "O(...) of the submitted code",\n'
        '  "space_complexity": "O(...) of the submitted code",\n'
        '  "score": 0-100 number (correctness 60%, efficiency 30%, edge cases 10%)\n'
        "}"
    )
    data = _generate_json(prompt, temperature=0.2)
    required = [
        "is_correct",
        "logic_feedback",
        "bugs",
        "missed_edge_cases",
        "better_approach",
        "score",
    ]
    missing = [k for k in required if k not in data]
    if missing:
        raise AIGenerationError(f"Code review response missing keys: {missing}")
    try:
        data["score"] = round(float(data["score"]), 1)
    except (TypeError, ValueError):
        data["score"] = 0.0
    data.setdefault("dsa_pattern", pattern_name or "Unknown")
    data.setdefault("time_complexity", "Unknown")
    data.setdefault("space_complexity", "Unknown")
    if not isinstance(data["bugs"], list):
        data["bugs"] = [str(data["bugs"])]
    if not isinstance(data["missed_edge_cases"], list):
        data["missed_edge_cases"] = [str(data["missed_edge_cases"])]
    return data


_HINT_LEVELS = {
    1: "a gentle nudge: ask a Socratic question about the problem structure. Do NOT name the algorithm or data structure.",
    2: "a stronger hint: point at the right data structure or pattern family, but do NOT describe the algorithm steps.",
    3: "a near-direct hint: outline the approach in 2-3 sentences, but do NOT write any code.",
}


def generate_hint(
    problem: DSAProblem, hint_level: int, topic_name: str = "", pattern_name: str = ""
) -> str:
    level = hint_level if hint_level in _HINT_LEVELS else 3
    prompt = (
        f"{_TUTOR_RULES}\n\n{_problem_context(problem, topic_name, pattern_name)}\n"
        f"Give the learner ONE hint at level {level}: {_HINT_LEVELS[level]}\n"
        'Maximum 60 words. Return JSON: {"hint_text": "..."}'
    )
    data = _generate_json(prompt, temperature=0.5)
    hint = data.get("hint_text")
    if not hint or not isinstance(hint, str):
        raise AIGenerationError("Hint response missing 'hint_text'.")
    return hint.strip()


def generate_roadmap(weak_topics: list, candidate_problems: list) -> Dict[str, Any]:
    """7-day plan grounded on the user's real weak topics and real problem IDs."""
    prompt = (
        f"{_TUTOR_RULES}\n\n"
        f"Learner's weak topics (lowest proficiency first):\n{json.dumps(weak_topics, indent=2)}\n\n"
        f"Problems available on the platform (ONLY reference these, by exact id and title):\n"
        f"{json.dumps(candidate_problems, indent=2)}\n\n"
        "Create a 7-day DSA recovery plan as JSON with EXACTLY these keys:\n"
        "{\n"
        '  "title": "short motivating plan title",\n'
        '  "summary": "2 sentences: what this plan fixes and how",\n'
        '  "days": [\n'
        '    {"day": 1, "focus": "topic name", "tasks": ["2-3 concrete tasks"],\n'
        '     "problems": [{"id": int, "title": "exact title from the list"}]}\n'
        "    ... 7 entries total ...\n"
        "  ]\n"
        "}\n"
        "Rules: earlier days target the weakest topics; each day has at most 2 problems; "
        "only use problem ids from the provided list; include at least one lighter review day."
    )
    data = _generate_json(prompt, temperature=0.4)
    if not isinstance(data.get("days"), list) or not data["days"]:
        raise AIGenerationError("Roadmap response missing 'days'.")
    valid_ids = {p["id"] for p in candidate_problems}
    for day in data["days"]:
        if isinstance(day.get("problems"), list):
            day["problems"] = [
                p
                for p in day["problems"]
                if isinstance(p, dict) and p.get("id") in valid_ids
            ]
    return data
