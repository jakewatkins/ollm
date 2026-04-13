"""Test configuration for ollm test suite."""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Generator
from unittest.mock import Mock

from ollm.config import Config, AgentLoopConfig
from ollm.ollama_client import OllamaClient
from ollm.mcp.client import McpClient


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    try:
        yield temp_path
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture  
def sample_config() -> dict:
    """Sample valid configuration."""
    return {
        "baseUrl": "http://localhost:11434",
        "apiKey": "",
        "agentLoop": {
            "maxTurns": 8,
            "requestTimeoutSeconds": 300,
            "toolCallTimeoutSeconds": 60
        },
        "skills": {
            "selection": {
                "topK": 1,
                "minScore": 0.35,
                "fuzzyMatch": True
            },
            "resources": {
                "maxFileSizeKB": 64,
                "maxTotalSizeKB": 256
            }
        },
        "scriptExecution": {
            "enabled": True,
            "image": "python:3.11-slim",
            "executionTimeoutSeconds": 30,
            "environment": {},
            "resources": {
                "memoryLimit": "128m",
                "cpuLimit": 0.5
            }
        }
    }


@pytest.fixture
def sample_skill_metadata() -> str:
    """Sample skill markdown with frontmatter."""
    return """---
name: test-skill
description: Test skill for unit testing
requiredMcpServers: []
preferredTools: []
resources: []
scriptExecution: true
---

# Test Skill

This is a test skill for unit testing.

## Features

- Test feature 1
- Test feature 2
"""


@pytest.fixture
def mock_config(sample_config: dict) -> Config:
    """Mock config object for tests."""
    return Config(**sample_config)


@pytest.fixture
def mock_ollama_client() -> Mock:
    """Mock Ollama client for tests."""
    client = Mock(spec=OllamaClient)
    client.chat.return_value = {
        "message": {
            "content": "I'll help you with that task.",
            "tool_calls": None
        }
    }
    return client


@pytest.fixture
def mock_mcp_client() -> Mock:
    """Mock MCP client for tests."""
    client = Mock(spec=McpClient)
    client.get_tools.return_value = []
    return client


@pytest.fixture
def timeout_config(sample_config: dict) -> Config:
    """Config with short timeouts for testing."""
    config_data = sample_config.copy()
    config_data["agentLoop"]["requestTimeoutSeconds"] = 1  # 1 second timeout
    return Config(**config_data)


@pytest.fixture
def invalid_skill_metadata() -> str:
    """Invalid skill markdown missing required fields."""
    return """---
description: Missing name field
---

# Invalid Skill

This skill is missing the required name field.
"""