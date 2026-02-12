import pytest
from unittest.mock import MagicMock
from tests.helpers import make_search_results, MockAnthropicResponse


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
