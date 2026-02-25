"""Tests for AIGenerator.generate_response()."""

import pytest
from unittest.mock import MagicMock
from ai_generator import AIGenerator
from tests.helpers import MockAnthropicResponse, MockTextBlock, MockToolUseBlock


@pytest.fixture
def generator(mock_anthropic_client):
    """AIGenerator with a mocked Anthropic client."""
    gen = AIGenerator(api_key="fake-key", model="claude-test")
    gen.client = mock_anthropic_client
    return gen


@pytest.fixture
def mock_tool_manager():
    mgr = MagicMock()
    mgr.execute_tool.return_value = "tool result text"
    return mgr


SAMPLE_TOOLS = [
    {"name": "search_course_content", "description": "...", "input_schema": {}},
    {"name": "get_course_outline", "description": "...", "input_schema": {}},
]


# ── Direct response (no tools) ──────────────────────────────────────


class TestDirectResponse:

    def test_direct_response_without_tools(self, generator, mock_anthropic_client):
        mock_anthropic_client.messages.create.return_value = MockAnthropicResponse(
            content=[MockTextBlock(text="Hello there")], stop_reason="end_turn"
        )

        result = generator.generate_response("hi")

        assert result == "Hello there"

    def test_no_tools_in_api_call_when_none(self, generator, mock_anthropic_client):
        generator.generate_response("hi")

        kwargs = mock_anthropic_client.messages.create.call_args
        assert "tools" not in kwargs.kwargs

    def test_tools_included_in_api_call(self, generator, mock_anthropic_client):
        generator.generate_response("hi", tools=SAMPLE_TOOLS)

        kwargs = mock_anthropic_client.messages.create.call_args.kwargs
        assert kwargs["tools"] == SAMPLE_TOOLS
        assert kwargs["tool_choice"] == {"type": "auto"}

    def test_conversation_history_in_system_prompt(
        self, generator, mock_anthropic_client
    ):
        generator.generate_response(
            "hi", conversation_history="User: hello\nAssistant: hi"
        )

        kwargs = mock_anthropic_client.messages.create.call_args.kwargs
        assert "Previous conversation:" in kwargs["system"]
        assert "User: hello" in kwargs["system"]


# ── Tool execution flow ──────────────────────────────────────────────


class TestToolExecution:

    def test_tool_use_triggers_execution_and_followup(
        self, generator, mock_anthropic_client, mock_tool_manager
    ):
        # First call: tool_use response
        tool_block = MockToolUseBlock()
        first_response = MockAnthropicResponse(
            content=[tool_block], stop_reason="tool_use"
        )
        # Second call: final text
        final_response = MockAnthropicResponse(
            content=[MockTextBlock(text="Final answer")], stop_reason="end_turn"
        )
        mock_anthropic_client.messages.create.side_effect = [
            first_response,
            final_response,
        ]

        result = generator.generate_response(
            "query", tools=SAMPLE_TOOLS, tool_manager=mock_tool_manager
        )

        assert result == "Final answer"
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="test query"
        )
        assert mock_anthropic_client.messages.create.call_count == 2

    def test_tool_execution_message_format(
        self, generator, mock_anthropic_client, mock_tool_manager
    ):
        tool_block = MockToolUseBlock(id="toolu_42")
        first_response = MockAnthropicResponse(
            content=[tool_block], stop_reason="tool_use"
        )
        final_response = MockAnthropicResponse(stop_reason="end_turn")
        mock_anthropic_client.messages.create.side_effect = [
            first_response,
            final_response,
        ]

        generator.generate_response(
            "q", tools=SAMPLE_TOOLS, tool_manager=mock_tool_manager
        )

        # Inspect the second API call's messages
        second_call_kwargs = mock_anthropic_client.messages.create.call_args_list[
            1
        ].kwargs
        messages = second_call_kwargs["messages"]

        # messages: [user, assistant(tool_use), user(tool_result)]
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        # The tool_result content
        tool_result_content = messages[2]["content"]
        assert tool_result_content[0]["type"] == "tool_result"
        assert tool_result_content[0]["tool_use_id"] == "toolu_42"


# ── Error propagation (query failed paths) ───────────────────────────


class TestErrorPropagation:

    def test_api_error_propagates(self, generator, mock_anthropic_client):
        mock_anthropic_client.messages.create.side_effect = RuntimeError("API boom")

        with pytest.raises(RuntimeError, match="API boom"):
            generator.generate_response("q")

    def test_second_api_call_error_propagates(
        self, generator, mock_anthropic_client, mock_tool_manager
    ):
        first_response = MockAnthropicResponse(
            content=[MockToolUseBlock()], stop_reason="tool_use"
        )
        mock_anthropic_client.messages.create.side_effect = [
            first_response,
            RuntimeError("Second call failed"),
        ]

        with pytest.raises(RuntimeError, match="Second call failed"):
            generator.generate_response(
                "q", tools=SAMPLE_TOOLS, tool_manager=mock_tool_manager
            )

    def test_tool_manager_exception_propagates(
        self, generator, mock_anthropic_client, mock_tool_manager
    ):
        first_response = MockAnthropicResponse(
            content=[MockToolUseBlock()], stop_reason="tool_use"
        )
        mock_anthropic_client.messages.create.return_value = first_response
        mock_tool_manager.execute_tool.side_effect = RuntimeError("Tool exploded")

        with pytest.raises(RuntimeError, match="Tool exploded"):
            generator.generate_response(
                "q", tools=SAMPLE_TOOLS, tool_manager=mock_tool_manager
            )


# ── Multi-round tool execution ───────────────────────────────────────


class TestMultiRoundToolExecution:

    def test_two_sequential_tool_calls(
        self, generator, mock_anthropic_client, mock_tool_manager
    ):
        outline_block = MockToolUseBlock(
            name="get_course_outline", id="t1", input={"course_name": "MCP"}
        )
        search_block = MockToolUseBlock(
            name="search_course_content", id="t2", input={"query": "MCP basics"}
        )
        mock_anthropic_client.messages.create.side_effect = [
            MockAnthropicResponse(content=[outline_block], stop_reason="tool_use"),
            MockAnthropicResponse(content=[search_block], stop_reason="tool_use"),
            MockAnthropicResponse(
                content=[MockTextBlock(text="Complete answer")], stop_reason="end_turn"
            ),
        ]
        mock_tool_manager.execute_tool.side_effect = ["outline data", "search data"]

        result = generator.generate_response(
            "complex query", tools=SAMPLE_TOOLS, tool_manager=mock_tool_manager
        )

        assert result == "Complete answer"
        assert mock_anthropic_client.messages.create.call_count == 3
        assert mock_tool_manager.execute_tool.call_count == 2
        calls = mock_tool_manager.execute_tool.call_args_list
        assert calls[0].args[0] == "get_course_outline"
        assert calls[1].args[0] == "search_course_content"

    def test_max_rounds_forces_final_call_without_tools(
        self, generator, mock_anthropic_client, mock_tool_manager
    ):
        mock_anthropic_client.messages.create.side_effect = [
            MockAnthropicResponse(
                content=[MockToolUseBlock(id="t1")], stop_reason="tool_use"
            ),
            MockAnthropicResponse(
                content=[MockToolUseBlock(id="t2")], stop_reason="tool_use"
            ),
            MockAnthropicResponse(
                content=[MockTextBlock(text="Forced")], stop_reason="end_turn"
            ),
        ]
        mock_tool_manager.execute_tool.side_effect = ["r1", "r2"]

        result = generator.generate_response(
            "q", tools=SAMPLE_TOOLS, tool_manager=mock_tool_manager
        )

        assert result == "Forced"
        call_list = mock_anthropic_client.messages.create.call_args_list
        # First two calls include tools
        assert "tools" in call_list[0].kwargs
        assert "tools" in call_list[1].kwargs
        # Third call (forced) does NOT include tools
        assert "tools" not in call_list[2].kwargs

    def test_message_accumulation_across_rounds(
        self, generator, mock_anthropic_client, mock_tool_manager
    ):
        block1 = MockToolUseBlock(
            name="get_course_outline", id="t1", input={"course_name": "X"}
        )
        block2 = MockToolUseBlock(
            name="search_course_content", id="t2", input={"query": "Y"}
        )
        mock_anthropic_client.messages.create.side_effect = [
            MockAnthropicResponse(content=[block1], stop_reason="tool_use"),
            MockAnthropicResponse(content=[block2], stop_reason="tool_use"),
            MockAnthropicResponse(
                content=[MockTextBlock(text="done")], stop_reason="end_turn"
            ),
        ]
        mock_tool_manager.execute_tool.side_effect = ["outline", "content"]

        generator.generate_response(
            "q", tools=SAMPLE_TOOLS, tool_manager=mock_tool_manager
        )

        # The third call should have 5 messages
        third_call = mock_anthropic_client.messages.create.call_args_list[2].kwargs
        msgs = third_call["messages"]
        assert len(msgs) == 5
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"
        assert msgs[2]["role"] == "user"
        assert msgs[3]["role"] == "assistant"
        assert msgs[4]["role"] == "user"
        # Verify tool_result IDs match tool_use IDs
        assert msgs[2]["content"][0]["tool_use_id"] == "t1"
        assert msgs[4]["content"][0]["tool_use_id"] == "t2"

    def test_tool_error_on_second_round_propagates(
        self, generator, mock_anthropic_client, mock_tool_manager
    ):
        mock_anthropic_client.messages.create.side_effect = [
            MockAnthropicResponse(
                content=[MockToolUseBlock(id="t1")], stop_reason="tool_use"
            ),
            MockAnthropicResponse(
                content=[MockToolUseBlock(id="t2")], stop_reason="tool_use"
            ),
        ]
        mock_tool_manager.execute_tool.side_effect = [
            "data",
            RuntimeError("Round 2 fail"),
        ]

        with pytest.raises(RuntimeError, match="Round 2 fail"):
            generator.generate_response(
                "q", tools=SAMPLE_TOOLS, tool_manager=mock_tool_manager
            )

    def test_api_error_on_third_call_propagates(
        self, generator, mock_anthropic_client, mock_tool_manager
    ):
        mock_anthropic_client.messages.create.side_effect = [
            MockAnthropicResponse(
                content=[MockToolUseBlock(id="t1")], stop_reason="tool_use"
            ),
            MockAnthropicResponse(
                content=[MockToolUseBlock(id="t2")], stop_reason="tool_use"
            ),
            RuntimeError("Third call boom"),
        ]
        mock_tool_manager.execute_tool.side_effect = ["r1", "r2"]

        with pytest.raises(RuntimeError, match="Third call boom"):
            generator.generate_response(
                "q", tools=SAMPLE_TOOLS, tool_manager=mock_tool_manager
            )
