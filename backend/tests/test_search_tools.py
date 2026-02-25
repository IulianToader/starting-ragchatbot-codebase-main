"""Tests for CourseSearchTool and ToolManager."""

import pytest
from search_tools import CourseSearchTool, ToolManager
from tests.helpers import make_search_results

# ── CourseSearchTool.execute() ───────────────────────────────────────


class TestCourseSearchToolExecute:

    def _make_tool(self, mock_vector_store):
        return CourseSearchTool(mock_vector_store)

    # Happy path
    def test_execute_returns_formatted_results(self, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results(
            documents=["Chunk text here"],
            metadata=[{"course_title": "Intro to AI", "lesson_number": 1}],
        )
        tool = self._make_tool(mock_vector_store)

        result = tool.execute(query="what is AI")

        assert "[Intro to AI - Lesson 1]" in result
        assert "Chunk text here" in result
        assert len(tool.last_sources) == 1
        src = tool.last_sources[0]
        assert "label" in src and "link" in src

    # Error from search
    def test_execute_returns_error_string_when_search_errors(self, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results(
            error="Search error: something went wrong"
        )
        tool = self._make_tool(mock_vector_store)

        result = tool.execute(query="fail")

        assert "something went wrong" in result

    # Empty results (no filters)
    def test_execute_returns_no_content_message_when_empty(self, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results()
        tool = self._make_tool(mock_vector_store)

        result = tool.execute(query="obscure")

        assert "No relevant content found" in result

    # Empty results with filters
    def test_execute_empty_results_with_filters_includes_filter_info(
        self, mock_vector_store
    ):
        mock_vector_store.search.return_value = make_search_results()
        tool = self._make_tool(mock_vector_store)

        result = tool.execute(query="x", course_name="MCP", lesson_number=3)

        assert "MCP" in result
        assert "lesson 3" in result

    # Parameter forwarding
    def test_execute_passes_parameters_to_vector_store(self, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results()
        tool = self._make_tool(mock_vector_store)

        tool.execute(query="q", course_name="MCP", lesson_number=2)

        mock_vector_store.search.assert_called_once_with(
            query="q", course_name="MCP", lesson_number=2
        )

    # Source deduplication
    def test_format_results_deduplicates_sources(self, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results(
            documents=["a", "b", "c"],
            metadata=[
                {"course_title": "AI", "lesson_number": 1},
                {"course_title": "AI", "lesson_number": 1},  # duplicate
                {"course_title": "AI", "lesson_number": 2},
            ],
        )
        tool = self._make_tool(mock_vector_store)

        tool.execute(query="q")

        assert len(tool.last_sources) == 2

    # No lesson number in metadata
    def test_format_results_handles_no_lesson_number(self, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results(
            documents=["text"],
            metadata=[{"course_title": "AI", "lesson_number": None}],
        )
        tool = self._make_tool(mock_vector_store)

        result = tool.execute(query="q")

        assert "[AI]" in result
        assert "Lesson None" not in result

    # Exception propagation — key "query failed" scenario
    def test_execute_propagates_exception_from_vector_store(self, mock_vector_store):
        mock_vector_store.search.side_effect = RuntimeError("ChromaDB exploded")
        tool = self._make_tool(mock_vector_store)

        with pytest.raises(RuntimeError, match="ChromaDB exploded"):
            tool.execute(query="boom")


# ── ToolManager ──────────────────────────────────────────────────────


class TestToolManager:

    def _make_manager_with_search(self, mock_vector_store):
        mgr = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        mgr.register_tool(tool)
        return mgr, tool

    def test_tool_manager_dispatches_to_registered_tool(self, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results()
        mgr, _ = self._make_manager_with_search(mock_vector_store)

        result = mgr.execute_tool("search_course_content", query="test")

        mock_vector_store.search.assert_called_once()
        assert isinstance(result, str)

    def test_tool_manager_returns_not_found_for_unknown_tool(self):
        mgr = ToolManager()

        result = mgr.execute_tool("nonexistent_tool", query="x")

        assert "not found" in result.lower()

    def test_tool_manager_get_last_sources(self, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results(
            documents=["doc"],
            metadata=[{"course_title": "C", "lesson_number": 1}],
        )
        mgr, _ = self._make_manager_with_search(mock_vector_store)

        mgr.execute_tool("search_course_content", query="q")

        assert len(mgr.get_last_sources()) >= 1

    def test_tool_manager_reset_sources_clears(self, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results(
            documents=["doc"],
            metadata=[{"course_title": "C", "lesson_number": 1}],
        )
        mgr, _ = self._make_manager_with_search(mock_vector_store)

        mgr.execute_tool("search_course_content", query="q")
        mgr.reset_sources()

        assert mgr.get_last_sources() == []
