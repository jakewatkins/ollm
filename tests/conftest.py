"""Test configuration for ollm test suite."""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Generator


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
                "minScore": 0.30,
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
def invalid_skill_metadata() -> str:
    """Invalid skill markdown missing required fields."""
    return """---
description: Missing name field
---

# Invalid Skill

This skill is missing the required name field.
"""