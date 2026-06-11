# tests/test_note_service.py
import pytest
from unittest.mock import patch
from sqlmodel import Session

from app.models import DSATopic, TopicNote, TopicQuizQuestion
from app.services.note_service import (
    generate_topic_notes,
    generate_topic_quiz,
    grade_quiz_submission,
)
from app.services.ai_service import AIGenerationError


@pytest.fixture
def topic(session: Session):
    t = DSATopic(name="Binary Search", description="Divide and conquer algorithm")
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


def mock_chunk_a():
    return {
        "sections": [
            {
                "section_key": "overview",
                "title": "Overview",
                "content_md": "Binary search is...",
                "examples": ["Ex 1"],
                "common_mistakes": ["Mistake 1", "Mistake 2"],
                "interview_tips": ["Tip 1"]
            },
            {
                "section_key": "core_concepts",
                "title": "Core Concepts",
                "content_md": "Concepts...",
                "examples": [],
                "common_mistakes": ["Mistake 3", "Mistake 4"],
                "interview_tips": ["Tip 2"]
            },
            {
                "section_key": "visual_walkthrough",
                "title": "Visual Walkthrough",
                "content_md": "Walkthrough...",
                "examples": [],
                "common_mistakes": ["Mistake 5", "Mistake 6"],
                "interview_tips": ["Tip 3"]
            },
            {
                "section_key": "interview_patterns",
                "title": "Interview Patterns",
                "content_md": "Patterns...",
                "examples": [],
                "common_mistakes": ["Mistake 7", "Mistake 8"],
                "interview_tips": ["Tip 4"]
            },
            {
                "section_key": "roadmap",
                "title": "Roadmap",
                "content_md": "Roadmap...",
                "examples": [],
                "common_mistakes": ["Mistake 9", "Mistake 10"],
                "interview_tips": ["Tip 5"]
            }
        ]
    }


def mock_chunk_b():
    return {
        "sections": [
            {
                "section_key": "practice_problems",
                "title": "Practice Problems",
                "content_md": "Problems...",
                "problems": [
                    {
                        "title": "Binary Search",
                        "difficulty": "Easy",
                        "pattern": "Classic",
                        "what_to_learn": "Learn search space halving",
                        "leetcode_slug": "binary-search"
                    }
                ],
                "examples": [],
                "common_mistakes": ["Mistake 11", "Mistake 12"],
                "interview_tips": ["Tip 6"]
            },
            {
                "section_key": "edge_cases",
                "title": "Edge Cases",
                "content_md": "Edge cases...",
                "examples": [],
                "common_mistakes": ["Mistake 13", "Mistake 14"],
                "interview_tips": ["Tip 7"]
            },
            {
                "section_key": "interview_script",
                "title": "Interview Script",
                "content_md": "Script...",
                "examples": [],
                "common_mistakes": ["Mistake 15", "Mistake 16"],
                "interview_tips": ["Tip 8"]
            }
        ],
        "pseudocode_templates": [
            {
                "name": "Classic",
                "when_to_use": "Exact match",
                "pseudocode": "low = 0, high = n-1..."
            }
        ],
        "code_templates": [
            {
                "language": "python",
                "name": "Classic",
                "code": "def search...",
                "line_explanations": [{"lines": "3", "explanation": "Explanation"}]
            }
        ],
        "complexity_notes": {
            "table": [{"operation": "Search", "time": "O(log n)", "space": "O(1)", "note": "halves space"}],
            "how_to_derive": "By halving space",
            "common_mistakes": ["Assuming space is O(log n)"]
        }
    }


def mock_chunk_c():
    return {
        "sections": [
            {
                "section_key": "revision_notes",
                "title": "Revision Notes",
                "content_md": "Short revision...",
                "examples": [],
                "common_mistakes": ["Mistake 17", "Mistake 18"],
                "interview_tips": ["Tip 9"]
            }
        ],
        "practice_plan": {
            "one_day": ["Read notes"],
            "seven_day": [
                {
                    "day": 1,
                    "focus": "Basic search",
                    "tasks": ["Read and implement"],
                    "problems": [
                        {
                            "title": "Search",
                            "difficulty": "Easy",
                            "pattern": "Classic",
                            "what_to_learn": "invariant",
                            "leetcode_slug": "search"
                        }
                    ]
                }
            ]
        },
        "confidence_checklist": [
            {"key": "explain_it", "label": "I can explain it"}
        ],
        "estimated_reading_minutes": 15,
        "level": "beginner_to_intermediate"
    }


def mock_quiz():
    return {
        "questions": [
            {
                "kind": "mcq",
                "question": "What is complexity?",
                "options": ["O(n)", "O(log n)", "O(1)", "O(n^2)"],
                "correct_answer": "1",
                "answer_explanation": "halving"
            },
            {
                "kind": "short_answer",
                "question": "How to handle overflow in mid computation?",
                "options": None,
                "correct_answer": "low + (high-low)/2",
                "answer_explanation": "prevents int overflow"
            }
        ]
    }


@patch("app.services.note_service._call_gemini_with_usage")
def test_generate_topic_notes_success(mock_call, session: Session, topic: DSATopic, user):
    # Setup mocks for sequential calls (Chunk A, Chunk B, Chunk C)
    mock_call.side_effect = [
        (mock_chunk_a(), 10, 20, 100),  # Chunk A
        (mock_chunk_b(), 15, 25, 120),  # Chunk B
        (mock_chunk_c(), 8, 18, 90),    # Chunk C
    ]

    note = generate_topic_notes(session, topic.id, user.id)

    assert note.topic_id == topic.id
    assert note.version == 1
    assert note.status == "draft"
    assert note.level == "beginner_to_intermediate"
    assert note.estimated_reading_minutes == 15
    assert len(note.content["sections"]) == 9  # 5 from A, 3 from B, 1 from C
    assert note.content["complexity_notes"]["table"][0]["time"] == "O(log n)"


@patch("app.services.note_service._call_gemini_with_usage")
def test_generate_topic_notes_retry_success(mock_call, session: Session, topic: DSATopic, user):
    # Chunk A fails validation on first call (missing sections), but succeeds on second call (retry)
    invalid_chunk_a = {"sections": None}
    mock_call.side_effect = [
        (invalid_chunk_a, 5, 5, 50),     # Chunk A (fails)
        (mock_chunk_a(), 10, 20, 100),   # Chunk A retry (succeeds)
        (mock_chunk_b(), 15, 25, 120),   # Chunk B (succeeds)
        (mock_chunk_c(), 8, 18, 90),     # Chunk C (succeeds)
    ]

    note = generate_topic_notes(session, topic.id, user.id)

    assert note.version == 1
    assert len(note.content["sections"]) == 9
    assert mock_call.call_count == 4


@patch("app.services.note_service._call_gemini_with_usage")
def test_generate_topic_notes_fails_twice(mock_call, session: Session, topic: DSATopic, user):
    invalid_chunk_a = {"sections": None}
    mock_call.side_effect = [
        (invalid_chunk_a, 5, 5, 50),  # Chunk A fails
        (invalid_chunk_a, 5, 5, 50),  # Chunk A retry fails
    ]

    with pytest.raises(AIGenerationError):
        generate_topic_notes(session, topic.id, user.id)

    assert mock_call.call_count == 2


@patch("app.services.note_service._call_gemini_with_usage")
def test_quiz_generation_and_grading(mock_call, session: Session, topic: DSATopic, user):
    # Mock Chunk A, B, C for note generation
    mock_call.side_effect = [
        (mock_chunk_a(), 10, 20, 100),
        (mock_chunk_b(), 15, 25, 120),
        (mock_chunk_c(), 8, 18, 90),
    ]
    note = generate_topic_notes(session, topic.id, user.id)

    # Mock Quiz generation
    mock_call.reset_mock()
    mock_call.side_effect = [
        (mock_quiz(), 20, 30, 150),  # Quiz gen
        ({"correct": True}, 5, 5, 50), # Mock AI grading for question 2 (short_answer)
    ]

    questions = generate_topic_quiz(session, note.id, user.id)
    assert len(questions) == 2
    assert questions[0].kind == "mcq"
    assert questions[1].kind == "short_answer"

    # Submit quiz
    answers = [
        {"question_id": str(questions[0].id), "answer": "1"},  # correct MCQ
        {"question_id": str(questions[1].id), "answer": "low + (high-low)/2"},  # correct short answer
    ]

    attempt, results = grade_quiz_submission(session, note.id, user.id, answers)
    assert attempt.score == 2
    assert attempt.total == 2
    assert results[0]["correct"] is True
    assert results[1]["correct"] is True
