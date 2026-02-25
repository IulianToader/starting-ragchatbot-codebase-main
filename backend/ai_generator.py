import anthropic
from typing import List, Optional


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to tools for course information.

Available Tools:
1. **search_course_content**: Search within course materials for specific content or detailed educational materials
2. **get_course_outline**: Get course structure including course title, course link, and complete lesson list (lesson numbers and titles). Use this for outline, syllabus, or "what lessons are in this course" questions.

Tool Usage:
- **Outline/structure questions**: Use get_course_outline to retrieve the course title, course link, and all lessons with their numbers and titles
- **Content questions**: Use search_course_content for specific course content or detailed materials
- **Up to 2 tool calls per query** — you may call a tool, examine its results, then call another tool if needed before giving your final answer
- Synthesize tool results into accurate, fact-based responses
- If a tool yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course-specific questions**: Use appropriate tool first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results" or "based on the tool results"

For outline questions, always include:
- Course title
- Course link
- Each lesson's number and title

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    MAX_TOOL_ROUNDS = 2

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 800}

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
    ) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        messages = [{"role": "user", "content": query}]

        for round_num in range(self.MAX_TOOL_ROUNDS + 1):
            # Build API call parameters
            call_params = {
                **self.base_params,
                "messages": messages,
                "system": system_content,
            }

            # Include tools unless this is the final forced-text round
            if tools and round_num < self.MAX_TOOL_ROUNDS:
                call_params["tools"] = tools
                call_params["tool_choice"] = {"type": "auto"}

            response = self.client.messages.create(**call_params)

            # Return text if Claude didn't request a tool call
            if response.stop_reason != "tool_use" or not tool_manager:
                return response.content[0].text

            # Execute tool calls and append results to conversation
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = tool_manager.execute_tool(block.name, **block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )

            messages.append({"role": "user", "content": tool_results})
