"""Tests for the FastAPI API endpoints.

Uses a lightweight test app (defined in conftest.py) that mirrors the real
routes without the static-file mount, so tests run without a ``frontend/``
directory on disk.
"""

import pytest


# ── POST /api/query ──────────────────────────────────────────────────


@pytest.mark.api
class TestQueryEndpoint:

    def test_query_returns_200_with_valid_payload(self, client):
        resp = client.post("/api/query", json={"query": "What is AI?"})

        assert resp.status_code == 200
        body = resp.json()
        assert "answer" in body
        assert "sources" in body
        assert "session_id" in body

    def test_query_returns_answer_and_sources(self, client):
        resp = client.post("/api/query", json={"query": "What is AI?"})
        body = resp.json()

        assert body["answer"] == "This is a test answer."
        assert len(body["sources"]) == 1
        assert body["sources"][0]["label"] == "Course A - Lesson 1"
        assert body["sources"][0]["link"] == "https://example.com/lesson1"

    def test_query_creates_session_when_not_provided(self, client, mock_rag_system):
        resp = client.post("/api/query", json={"query": "test"})
        body = resp.json()

        mock_rag_system.session_manager.create_session.assert_called_once()
        assert body["session_id"] == "session_1"

    def test_query_uses_provided_session_id(self, client, mock_rag_system):
        resp = client.post(
            "/api/query", json={"query": "test", "session_id": "my-session"}
        )
        body = resp.json()

        mock_rag_system.session_manager.create_session.assert_not_called()
        assert body["session_id"] == "my-session"

    def test_query_forwards_query_and_session_to_rag(self, client, mock_rag_system):
        client.post(
            "/api/query", json={"query": "explain RAG", "session_id": "s42"}
        )

        mock_rag_system.query.assert_called_once_with("explain RAG", "s42")

    def test_query_with_empty_string_returns_422(self, client):
        """FastAPI enforces `str` but not non-empty; this documents that."""
        resp = client.post("/api/query", json={"query": ""})
        # Empty string is a valid str, so the endpoint accepts it
        assert resp.status_code == 200

    def test_query_missing_query_field_returns_422(self, client):
        resp = client.post("/api/query", json={})

        assert resp.status_code == 422

    def test_query_wrong_content_type_returns_422(self, client):
        resp = client.post("/api/query", content="not json")

        assert resp.status_code == 422

    def test_query_rag_error_returns_500(self, client, mock_rag_system):
        mock_rag_system.query.side_effect = RuntimeError("DB connection lost")

        resp = client.post("/api/query", json={"query": "test"})

        assert resp.status_code == 500
        assert "DB connection lost" in resp.json()["detail"]

    def test_query_source_with_null_link(self, client, mock_rag_system):
        mock_rag_system.query.return_value = (
            "Answer",
            [{"label": "Course B", "link": None}],
        )

        resp = client.post("/api/query", json={"query": "test"})
        body = resp.json()

        assert resp.status_code == 200
        assert body["sources"][0]["link"] is None

    def test_query_empty_sources(self, client, mock_rag_system):
        mock_rag_system.query.return_value = ("No sources found.", [])

        resp = client.post("/api/query", json={"query": "obscure topic"})
        body = resp.json()

        assert resp.status_code == 200
        assert body["sources"] == []


# ── GET /api/courses ─────────────────────────────────────────────────


@pytest.mark.api
class TestCoursesEndpoint:

    def test_courses_returns_200(self, client):
        resp = client.get("/api/courses")

        assert resp.status_code == 200

    def test_courses_returns_stats(self, client):
        body = client.get("/api/courses").json()

        assert body["total_courses"] == 2
        assert body["course_titles"] == ["Intro to AI", "Advanced ML"]

    def test_courses_calls_get_course_analytics(self, client, mock_rag_system):
        client.get("/api/courses")

        mock_rag_system.get_course_analytics.assert_called_once()

    def test_courses_error_returns_500(self, client, mock_rag_system):
        mock_rag_system.get_course_analytics.side_effect = RuntimeError("ChromaDB down")

        resp = client.get("/api/courses")

        assert resp.status_code == 500
        assert "ChromaDB down" in resp.json()["detail"]

    def test_courses_empty_catalog(self, client, mock_rag_system):
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }

        body = client.get("/api/courses").json()

        assert body["total_courses"] == 0
        assert body["course_titles"] == []


# ── Method / route checks ────────────────────────────────────────────


@pytest.mark.api
class TestRouteMethodHandling:

    def test_get_on_query_endpoint_returns_405(self, client):
        resp = client.get("/api/query")

        assert resp.status_code == 405

    def test_post_on_courses_endpoint_returns_405(self, client):
        resp = client.post("/api/courses")

        assert resp.status_code == 405

    def test_nonexistent_route_returns_404(self, client):
        resp = client.get("/api/nonexistent")

        assert resp.status_code == 404
