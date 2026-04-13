"""Simplified integration tests for AgentLoop functionality."""

import pytest
from unittest.mock import Mock

from ollm.loop.agent_loop import AgentLoop
from ollm.config import Config


class TestAgentLoopInitialization:
    """Test AgentLoop initialization and configuration."""

    def test_agent_loop_creation_with_valid_config(self, mock_config: Config, mock_ollama_client, mock_mcp_client):
        """Test that AgentLoop can be created with valid configuration."""
        agent_loop = AgentLoop(mock_ollama_client, mock_mcp_client, mock_config.agent_loop)
        
        assert agent_loop is not None
        assert agent_loop.config == mock_config.agent_loop
        assert agent_loop.ollama_client == mock_ollama_client
        assert agent_loop.mcp_client == mock_mcp_client

    def test_timeout_config_settings(self, timeout_config: Config, mock_ollama_client, mock_mcp_client):
        """Test that timeout configuration is properly set."""
        agent_loop = AgentLoop(mock_ollama_client, mock_mcp_client, timeout_config.agent_loop)
        
        # Test that timeout configuration is properly set
        assert agent_loop.config.request_timeout_seconds == 1

    def test_max_turns_configuration(self, mock_config: Config, mock_ollama_client, mock_mcp_client):
        """Test that max turns limit is properly configured."""
        mock_config.agent_loop.max_turns = 5
        
        agent_loop = AgentLoop(mock_ollama_client, mock_mcp_client, mock_config.agent_loop)
        
        # Test that the configuration is properly set
        assert agent_loop.config.max_turns == 5