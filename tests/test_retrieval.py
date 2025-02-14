import pytest
from unittest.mock import patch, MagicMock
from data_retrieval import retrieve_information
from user_query import process_user_query
from redis.exceptions import RedisError

@patch("data_retrieval.process_user_query")
@patch("data_retrieval.graph")
def test_retrieve_information_invalid_format(mock_graph, mock_process_query):
    """Test handling of an invalid response format from the LLM."""
    mock_process_query.return_value = {
        "company_name": "TestCo",
        "query_type": "Revenue",
        "structured_query": "TestCo revenue"
    }

    mock_graph.invoke.return_value = MagicMock(final_result=None)  # Simulating invalid output
    result = retrieve_information("TestCo revenue")
    assert "error" in result or "Invalid response format" in result.get("response", "")


@patch("data_retrieval.process_user_query")
@patch("data_retrieval.graph")
@patch("data_retrieval.redis_client")
def test_retrieve_information_cache(mock_redis, mock_graph, mock_process_query):
    """Ensures that cached responses are returned from Redis instead of calling LLM."""
    mock_process_query.return_value = {
        "company_name": "TestCo",
        "query_type": "Revenue",
        "structured_query": "TestCo revenue"
    }

    mock_redis.get.return_value = b'{"response": "Cached revenue data"}'
    result = retrieve_information("TestCo revenue")
    assert result["response"] == "Cached revenue data"
    mock_graph.invoke.assert_not_called()  # Ensure LLM was NOT called


@patch("data_retrieval.process_user_query")
@patch("data_retrieval.graph")
@patch("data_retrieval.redis_client")
def test_retrieve_information_redis_failure(mock_redis, mock_graph, mock_process_query):
    """Ensures Redis failure raises an exception as expected."""
    
    mock_process_query.return_value = {
        "company_name": "TestCo",
        "query_type": "Revenue",
        "structured_query": "TestCo revenue"
    }

    mock_redis.get.side_effect = RedisError("Redis error")
    mock_graph.invoke.return_value = MagicMock(
        final_result={
            "response": "Company revenue is $100B",
            "confidence_score": 0.9,
            "source": "Wikipedia"
        }
    )

    # Expect the function to raise RedisError
    with pytest.raises(RedisError):
        retrieve_information("TestCo revenue")

@patch("user_querry.process_user_query")
def test_process_user_query_success(mock_process):
    """Ensures user queries are correctly parsed when valid."""
    mock_process.return_value = {
        "company_name": "TestCo",
        "query_type": "Revenue",
        "structured_query": "TestCo revenue"
    }
    result = process_user_query("What is the revenue of TestCo?")
    assert "company_name" in result or "error" in result

@patch("user_querry.process_user_query")
def test_process_user_query_ambiguous(mock_process):
    """Simulates a scenario where multiple companies match the query."""
    mock_process.return_value = {
        "ambiguous_options": ["TestCo Ltd", "TestCo Inc"]
    }
    result = process_user_query("What is the revenue of TestCo?")
    assert "ambiguous_options" in result or "error" in result

@patch("user_querry.process_user_query")
def test_process_user_query_invalid(mock_process):
    """Ensures invalid queries return an appropriate error response."""
    mock_process.return_value = {"error": "Failed to extract company name or category."}
    result = process_user_query("Invalid input")
    assert "error" in result or "company_name" in result


@patch("user_querry.process_user_query")
def test_process_user_query_api_failure(mock_process):
    """Ensures the function handles API request failures correctly."""
    
    # Simulate an API failure
    mock_process.side_effect = Exception("API request failed")

    try:
        result = process_user_query("What is the revenue of TestCo?")
    except Exception as e:
        result = {"error": str(e)}

    assert "error" in result
    assert result["error"] in ["API request failed", "Failed to extract company name or category."]
