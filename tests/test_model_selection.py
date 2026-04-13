"""Unit tests for model selection logic."""

from unittest.mock import Mock

import pytest

from ollm.model_selection import select_model
from ollm.ollama_client import OllamaClient


class TestModelSelection:
    """Test model selection behavior."""

    @pytest.fixture
    def mock_client(self):
        """Create mock Ollama client."""
        client = Mock(spec=OllamaClient)
        return client

    def test_explicit_model_takes_precedence(self, mock_client):
        """Test that explicit model parameter takes precedence."""
        result = select_model(mock_client, requested_model="explicit-model")
        
        assert result == "explicit-model"
        # Should not call list_models when explicit model provided
        mock_client.list_models.assert_not_called()

    def test_automatic_selection_when_no_explicit_model(self, mock_client):
        """Test automatic selection when no model specified."""
        mock_client.list_models.return_value = [
            "zephyr:7b",
            "llama3.2:latest", 
            "codellama:13b",
            "alpaca:7b"
        ]
        
        result = select_model(mock_client, requested_model=None)
        
        assert result == "alpaca:7b"  # Lexically first
        mock_client.list_models.assert_called_once()

    def test_empty_model_list_raises_error(self, mock_client):
        """Test that empty model list raises clear error."""
        mock_client.list_models.return_value = []
        
        with pytest.raises(ValueError, match="No models available"):
            select_model(mock_client, requested_model=None)

    def test_lexical_sorting_case_insensitive(self, mock_client):
        """Test that lexical sorting is case insensitive."""
        mock_client.list_models.return_value = [
            "Zephyr:7b",
            "alpaca:7b", 
            "Llama3.2:latest"
        ]
        
        result = select_model(mock_client, requested_model=None)
        
        # Should sort case-insensitively and pick lexically first
        assert result == "alpaca:7b"