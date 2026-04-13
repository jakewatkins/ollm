"""Unit tests for script execution timeout behavior."""

import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ollm.script_execution.executor import ScriptExecutor, ScriptExecutionRequest
from ollm.config import ScriptExecutionConfig
from ollm.errors import OllmError


class TestScriptExecutionLimits:
    """Test script execution timeouts and limits."""

    @pytest.fixture
    def script_config(self) -> ScriptExecutionConfig:
        """Create script execution config for testing."""
        return ScriptExecutionConfig(
            enabled=True,
            execution_timeout_seconds=5
        )

    @pytest.fixture
    def executor(self, script_config: ScriptExecutionConfig) -> ScriptExecutor:
        """Create script executor for testing."""
        return ScriptExecutor(script_config)

    def test_script_execution_request_creation(self):
        """Test that script execution requests can be created."""
        request = ScriptExecutionRequest(
            script_content="print('hello')",
            script_language="python",
            skill_name="test-skill"
        )
        
        assert request.script_content == "print('hello')"
        assert request.script_language == "python"
        assert request.skill_name == "test-skill"

    def test_executor_initialization(self, script_config: ScriptExecutionConfig):
        """Test that script executor initializes correctly."""
        executor = ScriptExecutor(script_config)
        
        assert executor.config == script_config
        assert hasattr(executor, '_docker_client')
        assert hasattr(executor, '_container_manager')

    def test_config_timeout_setting(self, script_config: ScriptExecutionConfig):
        """Test that timeout configuration is properly set."""
        assert script_config.execution_timeout_seconds == 5
        assert script_config.enabled is True

    @pytest.mark.skip(reason="Integration test - requires Docker")
    def test_actual_script_execution_timeout(self, executor: ScriptExecutor):
        """Test actual script execution with timeout (integration test)."""
        request = ScriptExecutionRequest(
            script_content="import time; time.sleep(10)",  # Longer than timeout
            script_language="python"
        )
        
        # This would require actual Docker integration which we skip for unit tests
        # In real implementation, this would test timeout behavior
        pass

    def test_resource_limit_validation(self):
        """Test that resource limits can be configured."""
        from ollm.config import ScriptExecutionResourcesConfig
        
        config = ScriptExecutionConfig(
            enabled=True,
            execution_timeout_seconds=30,
            resources={
                "memory_limit": "256m",
                "cpu_limit": 2.0
            }
        )
        
        assert config.resources.memory_limit == "256m"
        assert config.resources.cpu_limit == 2.0
        assert config.execution_timeout_seconds == 30

    def test_environment_variables_passed(self):
        """Test that environment variables are properly passed."""
        request = ScriptExecutionRequest(
            script_content="import os; print(os.getenv('TEST_VAR'))",
            script_language="python", 
            environment_vars={"TEST_VAR": "test_value"}
        )
        
        assert request.environment_vars == {"TEST_VAR": "test_value"}

    def test_skill_context_preserved(self):
        """Test that skill context is preserved in requests."""
        skill_resources = {"helper.py": "def helper(): return 42"}
        
        request = ScriptExecutionRequest(
            script_content="from helper import helper; print(helper())",
            script_language="python",
            skill_name="math-helper",
            skill_resources=skill_resources
        )
        
        assert request.skill_name == "math-helper"
        assert request.skill_resources == skill_resources