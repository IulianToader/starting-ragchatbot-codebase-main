import pytest
from unittest.mock import MagicMock
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from tests.helpers import make_search_results, MockAnthropicResponse


# ── Existing unit-test fixtures ──────────────────────────────────────


@pytest.fixture
def mock_vector_store():
    """A MagicMock that behaves like VectorStore for search operations."""
    store = MagicMock()
    store.search.return_value = make_search_results()
    store.get_lesson_link.return_value = "https://example.com/lesson"
    return store


@pytest.fixture
def mock_anthropic_client():
    """A MagicMock Anthropic client that returns a simple text response."""
    client = MagicMock()
    client.messages.create.return_value = MockAnthropicResponse()
    return client


# ── API test fixtures ────────────────────────────────────────────────


@pytest.fixture
def mock_rag_system():
    """A MagicMock RAGSystem with sensible defaults for API tests."""
    rag = MagicMock()
    rag.query.return_value = (
        "This is a test answer.",
        [{"label": "Course A - Lesson 1", "link": "https://example.com/lesson1"}],
    )
    rag.session_manager.create_session.return_value = "session_1"
    rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Intro to AI", "Advanced ML"],
    }
    return rag


@pytest.fixture
def test_app(mock_rag_system):
    """A minimal FastAPI app that mirrors the real API routes.

    This avoids importing backend/app.py, which mounts static files
    from a ``../frontend`` directory that doesn't exist during tests.
    The endpoint logic is intentionally kept identical to the real app
    so we validate request parsing, response serialisation, and error
    handling through the HTTP layer.
    """

    # ── Pydantic models (same as app.py) ─────────────────────────
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class SourceItem(BaseModel):
        label: str
        link: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[SourceItem]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    # ── App ───────────────────────────────────────────────────────
    app = FastAPI()
    rag_system = mock_rag_system

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = rag_system.session_manager.create_session()
            answer, sources = rag_system.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


@pytest.fixture
def client(test_app):
    """Starlette TestClient wired to the test app."""
    return TestClient(test_app)
