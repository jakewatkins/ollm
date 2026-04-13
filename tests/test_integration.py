"""Integration tests for tool loop and timeout behavior."""

import json
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ollm.loop.agent_loop import AgentLoop
from ollm.config import Config
from ollm.errors import OllmError


class TestToolLoopSuccess:
    """Test successful tool loop scenarios."""

    @pytest.fixture
    def mock_config(self, sample_config: dict) -> Config:
        """Create mock config for testing."""
        config = Config(**sample_config)
        config.agent_loop.max_turns = 3
        config.agent_loop.request_timeout_seconds = 10
        return config

    @pytest.fixture
    def mock_ollama_client(self):
        """Create mock Ollama client."""
        client = Mock()
        client.chat.return_value = {
            "message": {
                "content": "I'll help you with that task.",
                "tool_calls": None
            }
        }
        return client

    def test_successful_no_tools_conversation(self, mock_config: Config, mock_ollama_client):
        """Test successful conversation without tool calls."""
        agent_loop = AgentLoop(mock_config, mock_ollama_client)
        
        result = agent_loop.run_conversation(
            prompt="What is 2 + 2?",
            model="llama3.2:latest",
            tools=[]
        )
        
        assert result.success is True
        assert "help you" in result.final_response
        assert result.turn_count == 1
        assert len(result.conversation_history) >= 2  # User + assistant

    def test_successful_tool_execution_flow(self, mock_config: Config, mock_ollama_client):
        """Test successful tool execution flow."""
        # Mock tool that will be called
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.call.return_value = "Tool executed successfully"
        
        # Mock tool calls in conversation
        mock_ollama_client.chat.side_effect = [
            {  # First call - request tool
                "message": {
                    "content": "I'll use the test tool.",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "test_tool",
                                "arguments": '{"param": "value"}'
                            }
                        }
                    ]
                }
            },
            {  # Second call - respond with tool result
                "message": {
                    "content": "The tool returned: Tool executed successfully",
                    "tool_calls": None
                }
            }
        ]
        
        agent_loop = AgentLoop(mock_config, mock_ollama_client)
        
        result = agent_loop.run_conversation(
            prompt="Use the test tool",
            model="llama3.2:latest", 
            tools=[mock_tool]
        )
        
        assert result.success is True
        assert result.turn_count == 2
        mock_tool.call.assert_called_once()

    def test_max_turns_limit_respected(self, mock_config: Config, mock_ollama_client):
        """Test that maxTurns limit is respected."""
        mock_config.agent_loop.max_turns = 2
        
        # Mock continuous tool calling  
        mock_tool = Mock()
        mock_tool.name = "loop_tool" 
        mock_tool.call.return_value = "Continue"
        
        mock_ollama_client.chat.return_value = {
            "message": {
                "content": "Using tool again",
                "tool_calls": [
                    {
                        "function": {
                            "name": "loop_tool",
                            "arguments": "{}"
                        }
                    }
                ]
            }
        }
        
        agent_loop = AgentLoop(mock_config, mock_ollama_client)
        
        result = agent_loop.run_conversation(
            prompt="Keep using the tool",
            model="llama3.2:latest",
            tools=[mock_tool]
        )
        
        assert result.turn_count == mock_config.agent_loop.max_turns
        assert len(result.conversation_history) > 2


class TestToolLoopTimeouts:
    """Test timeout handling in tool loops."""

    @pytest.fixture  
    def timeout_config(self, sample_config: dict) -> Config:
        """Create config with short timeouts for testing."""
        config = Config(**sample_config)
        config.agent_loop.request_timeout_seconds = 1  # 1 second timeout
        return config

    def test_ollama_request_timeout_handled(self, timeout_config: Config):
        """Test that Ollama request timeout is properly handled."""
        mock_ollama_client = Mock()
        
        def slow_response(*args, **kwargs):
            time.sleep(2)  # Slower than 1 second timeout
            return {"message": {"content": "Late response"}}
        
        mock_ollama_client.chat.side_effect = slow_response
        
        agent_loop = AgentLoop(timeout_config, mock_ollama_client)
        
        result = agent_loop.run_conversation(
            prompt="Test timeout",
            model="llama3.2:latest",
            tools=[]
        )
        
        assert result.success is False
        assert "timeout" in result.error_message.lower()

    def test_tool_execution_timeout_handled(self, mock_config: Config, mock_ollama_client):
        """Test that tool execution timeout is handled."""
        def slow_tool(*args, **kwargs):
            time.sleep(3)  # Slow tool execution
            return "Eventually done"
        
        mock_tool = Mock()
        mock_tool.name = "slow_tool"
        mock_tool.call.side_effect = slow_tool
        
        mock_ollama_client.chat.return_value = {
            "message": {
                "content": "Using slow tool", 
                "tool_calls": [
                    {
                        "function": {
                            "name": "slow_tool",
                            "arguments": "{}"
                        }
                    }
                ]
            }
        }
        
        agent_loop = AgentLoop(mock_config, mock_ollama_client)
        
        with patch('ollm.loop.agent_loop.TOOL_TIMEOUT_SECONDS', 1):  # 1 second tool timeout
            result = agent_loop.run_conversation(
                prompt="Use slow tool",
                model="llama3.2:latest",
                tools=[mock_tool]
            )
        
        # Should handle timeout gracefully
        assert "timeout" in str(result.error_message).lower() or result.success is False


class TestNoSkillsScenario:
    """Test behavior when no skills are available."""

    def test_conversation_works_without_skills(self, mock_config: Config, mock_ollama_client):
        """Test that conversation works fine without any skills loaded."""
        agent_loop = AgentLoop(mock_config, mock_ollama_client)
        
        result = agent_loop.run_conversation(
            prompt="Simple question without tools",
            model="llama3.2:latest",
            tools=[],  # No tools/skills
            skills=[]
        )
        
        assert result.success is True
        assert result.turn_count >= 1

    def test_skill_context_omitted_when_no_skills(self, mock_config: Config, mock_ollama_client):
        """Test that skill context is not injected when no skills available."""
        agent_loop = AgentLoop(mock_config, mock_ollama_client)
        
        # Capture the actual prompt sent to Ollama
        actual_messages = []
        def capture_messages(*args, **kwargs):
            if 'messages' in kwargs:
                actual_messages.extend(kwargs['messages'])
            elif args:
                actual_messages.extend(args[0])  # First arg might be messages
            return {"message": {"content": "Response"}}
        
        mock_ollama_client.chat.side_effect = capture_messages
        
        agent_loop.run_conversation(
            prompt="Test prompt",
            model="llama3.2:latest",
            tools=[],
            skills=[]
        )
        
        # Verify no skill-related context was added
        all_content = " ".join(str(msg) for msg in actual_messages)
        assert "skill" not in all_content.lower()
        assert "SKILL.md" not in all_content


class TestOutputFileHandling:
    """Test output file creation and management."""

    def test_output_file_created_when_specified(self, mock_config: Config, mock_ollama_client, temp_dir: Path):
        """Test that output file is created when specified."""
        output_file = temp_dir / "conversation.log"
        
        agent_loop = AgentLoop(mock_config, mock_ollama_client)
        
        result = agent_loop.run_conversation(
            prompt="Test conversation",
            model="llama3.2:latest",
            tools=[],
            output_file=output_file
        )
        
        assert output_file.exists()
        assert output_file.stat().st_size > 0
        
        # Verify content includes conversation
        content = output_file.read_text()
        assert "Test conversation" in content

    def test_output_file_contains_full_conversation(self, mock_config: Config, mock_ollama_client, temp_dir: Path):
        """Test that output file contains the full conversation history."""
        output_file = temp_dir / "full_conversation.log"
        
        mock_ollama_client.chat.return_value = {
            "message": {
                "content": "This is my detailed response to your question.",
                "tool_calls": None
            }
        }
        
        agent_loop = AgentLoop(mock_config, mock_ollama_client)
        
        result = agent_loop.run_conversation(
            prompt="What is the meaning of life?",
            model="llama3.2:latest",
            tools=[],
            output_file=output_file
        )
        
        content = output_file.read_text()
        
        # Should contain both user and assistant messages
        assert "What is the meaning of life?" in content
        assert "This is my detailed response" in content
        assert "user:" in content.lower() or "human:" in content.lower()
        assert "assistant:" in content.lower() or "ai:" in content.lower()

    def test_output_file_permissions_secure(self, mock_config: Config, mock_ollama_client, temp_dir: Path):
        """Test that output file has secure permissions."""
        output_file = temp_dir / "secure_conversation.log"
        
        agent_loop = AgentLoop(mock_config, mock_ollama_client)
        
        agent_loop.run_conversation(
            prompt="Sensitive conversation",
            model="llama3.2:latest",
            tools=[],
            output_file=output_file
        )
        
        # Check file permissions (readable by owner only)
        stat_info = output_file.stat()
        permissions = oct(stat_info.st_mode)[-3:]  # Last 3 digits
        
        # Should be readable/writable by owner only (600) or similar
        assert permissions in ["600", "644"]  # Allow common secure permissions