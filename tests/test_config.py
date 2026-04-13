"""Unit tests for configuration handling."""

import os
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from ollm.config import Config, get_api_key, load_config
from ollm.errors import ConfigurationError


class TestConfigDefaults:
    """Test configuration defaults and invalid value fallbacks."""

    def test_config_creation_with_required_fields(self, sample_config: dict):
        """Test that config can be created with required fields."""
        config = Config(**sample_config)
        
        assert config.base_url == "http://localhost:11434"
        assert config.agent_loop.max_turns == 8
        assert config.skills.selection.min_score == 0.35

    def test_missing_required_base_url_fails(self):
        """Test that missing required baseUrl fails."""
        invalid_config = {"apiKey": "test"}
        
        with pytest.raises(ValueError, match="baseUrl is required"):
            Config(**invalid_config)

    def test_config_loading_from_file(self, temp_dir: Path, sample_config: dict):
        """Test loading config from file."""
        config_file = temp_dir / "config.json"
        config_file.write_text(json.dumps(sample_config))
        
        config = load_config(config_file)
        
        assert config.base_url == "http://localhost:11434"
        assert config.agent_loop.max_turns == 8

    def test_nonexistent_config_file_fails(self, temp_dir: Path):
        """Test that nonexistent config file fails clearly."""
        nonexistent_file = temp_dir / "missing.json"
        
        with pytest.raises(ConfigurationError, match="Configuration file not found"):
            load_config(nonexistent_file)


class TestApiKeyPrecedence:
    """Test API key precedence logic."""

    def test_env_var_takes_precedence(self, sample_config: dict):
        """Test that OLLM_OLLAMA_API_KEY takes precedence."""
        config = Config(**sample_config)
        config.api_key = "config-key"
        
        with patch.dict(os.environ, {"OLLM_OLLAMA_API_KEY": "env-key"}):
            key = get_api_key(config)
            assert key == "env-key"

    def test_config_key_used_when_no_env(self, sample_config: dict):
        """Test that config apiKey is used when no env var."""
        config = Config(**sample_config)
        config.api_key = "config-key"
        
        with patch.dict(os.environ, {}, clear=True):
            key = get_api_key(config)
            assert key == "config-key"

    def test_empty_env_var_falls_back_to_config(self, sample_config: dict):
        """Test that empty env var falls back to config."""
        config = Config(**sample_config)
        config.api_key = "config-key"
        
        with patch.dict(os.environ, {"OLLM_OLLAMA_API_KEY": ""}):
            key = get_api_key(config)
            assert key == "config-key"

    def test_no_key_returns_none(self, sample_config: dict):
        """Test that no key returns None."""
        config = Config(**sample_config)
        config.api_key = ""
        
        with patch.dict(os.environ, {}, clear=True):
            key = get_api_key(config)
            assert key is None


class TestConfigValidation:
    """Test configuration validation."""

    def test_base_url_validation(self):
        """Test base URL validation."""
        # Valid base URL should work
        config_data = {"baseUrl": "http://localhost:11434"}
        config = Config(**config_data)
        assert config.base_url == "http://localhost:11434"
        
        # Trailing slash should be stripped
        config_data = {"baseUrl": "http://localhost:11434/"}
        config = Config(**config_data)
        assert config.base_url == "http://localhost:11434"

    def test_agent_loop_defaults(self):
        """Test agent loop defaults."""
        config_data = {"baseUrl": "http://localhost:11434"}
        config = Config(**config_data)
        
        assert config.agent_loop.max_turns == 8
        assert config.agent_loop.request_timeout_seconds == 300
        assert config.agent_loop.tool_call_timeout_seconds == 60

    def test_skills_defaults(self):
        """Test skills defaults."""
        config_data = {"baseUrl": "http://localhost:11434"}
        config = Config(**config_data)
        
        assert config.skills.selection.top_k == 1
        assert config.skills.selection.min_score == 0.35
        assert config.skills.selection.fuzzy_match is True