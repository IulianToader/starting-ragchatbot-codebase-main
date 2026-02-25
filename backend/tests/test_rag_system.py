"""Integration tests for RAGSystem.query() with mocked components."""

import pytest
from unittest.mock import MagicMock, patch, call
from rag_system import RAGSystem


@pytest.fixture
def rag():
    """RAGSystem with all heavy components mocked out."""
    mock_config = MagicMock()
    mock_config.CHUNK_SIZE = 800
    mock_config.CHUNK_OVERLAP = 100
    mock_config.CHROMA_PATH = "/tmp/test_chroma"
    mock_config.EMBEDDING_MODEL = "test-model"
    mock_config.MAX_RESULTS = 5
    mock_config.ANTHROPIC_API_KEY = "fake-key"
    mock_config.ANTHROPIC_MODEL = "claude-test"
    mock_config.MAX_HISTORY = 2

    with (
        patch("rag_system.DocumentProcessor"),
        patch("rag_system.VectorStore") as MockVS,
        patch("rag_system.AIGenerator") as MockAI,
        patch("rag_system.SessionManager") as MockSM,
        patch("rag_system.CourseSearchTool") as MockCST,
        patch("rag_system.CourseOutlineTool") as MockCOT,
    ):

        # Configure mocks
        MockAI.return_value.generate_response.return_value = "AI answer"
        MockSM.return_value.get_conversation_history.return_value = None
        MockCST.return_value.get_tool_definition.return_value = {
            "name": "search_course_content"
        }
        MockCOT.return_value.get_tool_definition.return_value = {
            "name": "get_course_outline"
        }
        MockCST.return_value.last_sources = [
            {"label": "Course A - Lesson 1", "link": "https://example.com"}
        ]
        MockCOT.return_value.last_sources = []

        system = RAGSystem(mock_config)
        yield system


# ── Happy path ───────────────────────────────────────────────────────


class TestQueryHappyPath:

    def test_query_returns_response_and_sources(self, rag):
        response, sources = rag.query("What is AI?", session_id="s1")

        assert response == "AI answer"
        assert isinstance(sources, list)

    def test_query_prompt_format(self, rag):
        rag.query("What is AI?")

        call_kwargs = rag.ai_generator.generate_response.call_args.kwargs
        assert (
            "Answer this question about course materials: What is AI?"
            in call_kwargs["query"]
        )

    def test_query_passes_tools_and_manager(self, rag):
        rag.query("q")

        call_kwargs = rag.ai_generator.generate_response.call_args.kwargs
        assert call_kwargs["tools"] is not None
        assert call_kwargs["tool_manager"] is rag.tool_manager


# ── Session handling ─────────────────────────────────────────────────


class TestSessionHandling:

    def test_query_includes_session_history(self, rag):
        rag.session_manager.get_conversation_history.return_value = (
            "User: hi\nAssistant: hello"
        )

        rag.query("follow-up", session_id="s1")

        call_kwargs = rag.ai_generator.generate_response.call_args.kwargs
        assert call_kwargs["conversation_history"] == "User: hi\nAssistant: hello"

    def test_query_updates_session_after_response(self, rag):
        rag.query("What is AI?", session_id="s1")

        rag.session_manager.add_exchange.assert_called_once()
        args = rag.session_manager.add_exchange.call_args.args
        assert args[0] == "s1"  # session_id
        assert "What is AI?" in args[1]  # query (wrapped in prompt)
        assert args[2] == "AI answer"  # response

    def test_query_works_without_session(self, rag):
        response, sources = rag.query("What is AI?", session_id=None)

        assert response == "AI answer"
        rag.session_manager.get_conversation_history.assert_not_called()
        rag.session_manager.add_exchange.assert_not_called()


# ── Source handling ──────────────────────────────────────────────────


class TestSourceHandling:

    def test_query_resets_sources_after_retrieval(self, rag):
        rag.query("q")

        # tool_manager is a real ToolManager wrapping mocked tools;
        # after query(), reset_sources should have been called, clearing last_sources.
        # We verify by checking that get_last_sources now returns empty
        # (since the real ToolManager.reset_sources sets tool.last_sources = []).
        assert rag.tool_manager.get_last_sources() == []

    def test_sources_conform_to_pydantic_schema(self, rag):
        """Source dicts from get_last_sources() should validate against SourceItem."""
        from pydantic import BaseModel
        from typing import Optional

        class SourceItem(BaseModel):
            label: str
            link: Optional[str] = None

        # Before query, the mock tool has sources set
        sources_before_reset = rag.tool_manager.get_last_sources()

        # Validate each source dict
        for src in sources_before_reset:
            item = SourceItem(**src)
            assert item.label is not None


# ── Error propagation ────────────────────────────────────────────────


class TestErrorPropagation:

    def test_query_propagates_ai_generator_exception(self, rag):
        rag.ai_generator.generate_response.side_effect = RuntimeError("AI failed")

        with pytest.raises(RuntimeError, match="AI failed"):
            rag.query("q", session_id="s1")
