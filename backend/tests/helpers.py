"""Shared test helpers — importable from test modules."""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from vector_store import SearchResults


def make_search_results(
    documents: List[str] = None,
    metadata: List[Dict[str, Any]] = None,
    distances: List[float] = None,
    error: Optional[str] = None,
) -> SearchResults:
    """Create SearchResults with sensible defaults."""
    docs = documents or []
    meta = metadata or [{} for _ in docs]
    dists = distances or [0.5] * len(docs)
    return SearchResults(documents=docs, metadata=meta, distances=dists, error=error)


@dataclass
class MockTextBlock:
    type: str = "text"
    text: str = "Mock AI response"


@dataclass
class MockToolUseBlock:
    type: str = "tool_use"
    id: str = "toolu_01"
    name: str = "search_course_content"
    input: dict = None

    def __post_init__(self):
        if self.input is None:
            self.input = {"query": "test query"}


@dataclass
class MockAnthropicResponse:
    content: list = None
    stop_reason: str = "end_turn"

    def __post_init__(self):
        if self.content is None:
            self.content = [MockTextBlock()]
