# tests/test_topic_notes_router.py
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from datetime import datetime

from app.main import app
from app.database import get_session
from app.models import DSATopic, TopicNote, UserTopicNoteState
from app.routers.auth import get_current_user


@pytest.fixture
def client(session: Session, user):
    # Override get_session dependency
    def get_session_override():
        return session
    app.dependency_overrides[get_session] = get_session_override

    # Override get_current_user dependency
    def get_current_user_override():
        return user
    app.dependency_overrides[get_current_user] = get_current_user_override

    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()


def test_get_notes_not_found(client, session: Session):
    # If topic doesn't exist, should return 404
    response = client.get("/api/topics/99999/notes")
    assert response.status_code == 404


def test_get_notes_can_generate(client, session: Session):
    t = DSATopic(name="Binary Search", description="desc")
    session.add(t)
    session.commit()
    session.refresh(t)

    response = client.get(f"/api/topics/{t.id}/notes")
    assert response.status_code == 200
    data = response.json()
    assert data["can_generate"] is True
    assert "detail" in data


def test_toggle_bookmark(client, session: Session):
    t = DSATopic(name="Dynamic Programming", description="desc")
    session.add(t)
    session.commit()
    session.refresh(t)

    response = client.post(f"/api/topics/{t.id}/notes/bookmark")
    assert response.status_code == 200
    assert response.json()["is_bookmarked"] is True

    # toggle again
    response = client.post(f"/api/topics/{t.id}/notes/bookmark")
    assert response.status_code == 200
    assert response.json()["is_bookmarked"] is False


def test_update_progress(client, session: Session):
    t = DSATopic(name="Recursion", description="desc")
    session.add(t)
    session.commit()
    session.refresh(t)

    # First add a mock published note so that the section key can be validated
    note = TopicNote(
        topic_id=t.id,
        version=1,
        status="published",
        content={"sections": [{"section_key": "overview", "title": "Overview", "content_md": "..."}]},
    )
    session.add(note)
    session.commit()

    response = client.put(f"/api/topics/{t.id}/notes/progress", json={
        "section_key": "overview",
        "completed": True
    })
    assert response.status_code == 200
    data = response.json()
    assert "overview" in data["completed_sections"]


def test_update_checklist(client, session: Session):
    t = DSATopic(name="Backtracking", description="desc")
    session.add(t)
    session.commit()
    session.refresh(t)

    response = client.put(f"/api/topics/{t.id}/notes/checklist", json={
        "key": "explain_backtracking",
        "checked": True
    })
    assert response.status_code == 200
    data = response.json()
    assert data["checklist_state"]["explain_backtracking"] is True


def test_update_personal_note(client, session: Session):
    t = DSATopic(name="Greedy", description="desc")
    session.add(t)
    session.commit()
    session.refresh(t)

    response = client.put(f"/api/topics/{t.id}/notes/personal-note", json={
        "content": "My greedy approach thoughts."
    })
    assert response.status_code == 200
    data = response.json()
    assert data["personal_notes_md"] == "My greedy approach thoughts."


def test_get_user_topics_list(client, session: Session):
    t = DSATopic(name="Trees", description="Tree topics")
    session.add(t)
    session.commit()

    response = client.get("/api/me/topic-notes")
    assert response.status_code == 200
    data = response.json()
    # Find tree topic in the response
    tree_topic = next(item for item in data if item["name"] == "Trees")
    assert tree_topic is not None
    assert tree_topic["has_published_note"] is False


def test_get_note_by_id(client, session: Session):
    t = DSATopic(name="Graphs", description="Graph topics")
    session.add(t)
    session.commit()

    note = TopicNote(
        topic_id=t.id,
        version=1,
        status="published",
        content={"sections": []},
    )
    session.add(note)
    session.commit()

    response = client.get(f"/api/topic-notes/{note.id}")
    assert response.status_code == 200
    assert response.json()["id"] == note.id

