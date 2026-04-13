"""Configuration management for ollm."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, validator

from .errors import ConfigurationError
from .paths import get_config_path


class AgentLoopConfig(BaseModel):
    """Configuration for agent loop behavior."""
    max_turns: int = Field(default=8, alias="maxTurns", ge=1)
    tool_call_timeout_seconds: int = Field(default=60, alias="toolCallTimeoutSeconds", ge=1)
    request_timeout_seconds: int = Field(default=300, alias="requestTimeoutSeconds", ge=1)
    
    class Config:
        validate_by_name = True


class LoggingConfig(BaseModel):
    """Configuration for logging behavior."""
    level: str = Field(default="info")
    format: str = Field(default="jsonl") 
    max_file_size_mb: int = Field(default=10, alias="maxFileSizeMB", ge=1)
    max_files: int = Field(default=5, alias="maxFiles", ge=1)
    
    class Config:
        validate_by_name = True
    
    @validator('level')
    def validate_level(cls, v):
        allowed_levels = ['debug', 'info', 'warn', 'error']
        if v.lower() not in allowed_levels:
            return 'info'  # Default fallback
        return v.lower()
    
    @validator('format')
    def validate_format(cls, v):
        allowed_formats = ['jsonl', 'text']
        if v.lower() not in allowed_formats:
            return 'jsonl'  # Default fallback
        return v.lower()


class SkillsSelectionConfig(BaseModel):
    """Configuration for skills selection."""
    top_k: int = Field(default=1, alias="topK", ge=1)
    min_score: float = Field(default=0.35, alias="minScore", ge=0.0, le=1.0)
    fuzzy_match: bool = Field(default=True, alias="fuzzyMatch")
    
    class Config:
        validate_by_name = True
    
    @validator('top_k')
    def validate_top_k(cls, v):
        # In v1, must be 1
        if v != 1:
            return 1
        return v


class SkillsResourcesConfig(BaseModel):
    """Configuration for skills resources."""
    max_file_size_kb: int = Field(default=64, alias="maxFileSizeKB", ge=1)
    max_total_size_kb: int = Field(default=256, alias="maxTotalSizeKB", ge=1)
    
    class Config:
        validate_by_name = True


class SkillsConfig(BaseModel):
    """Configuration for skills system."""
    selection: SkillsSelectionConfig = Field(default_factory=SkillsSelectionConfig)
    resources: SkillsResourcesConfig = Field(default_factory=SkillsResourcesConfig)


class Config(BaseModel):
    """Main configuration for ollm."""
    base_url: str = Field(..., alias="baseUrl", description="Base URL for Ollama server")
    api_key: Optional[str] = Field(default=None, alias="apiKey", description="API key for Ollama")
    agent_loop: AgentLoopConfig = Field(default_factory=AgentLoopConfig, alias="agentLoop")
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    skills: SkillsConfig = Field(default_factory=SkillsConfig)
    
    class Config:
        validate_by_name = True
    
    @validator('base_url')
    def validate_base_url(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("baseUrl is required and must be a non-empty string")
        return v.rstrip('/')


def get_api_key(config: Config) -> Optional[str]:
    """Get API key with precedence: env var -> config -> None.
    
    Args:
        config: Configuration object
        
    Returns:
        API key if available, None otherwise
    """
    # Check environment variable first
    env_key = os.environ.get("OLLM_OLLAMA_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip()
    
    # Fallback to config
    if config.api_key and config.api_key.strip():
        return config.api_key.strip()
    
    return None


def load_config() -> Config:
    """Load configuration from config.json.
    
    Returns:
        Loaded configuration object
        
    Raises:
        ConfigurationError: If config cannot be loaded or is invalid
    """
    config_path = get_config_path()
    
    if not config_path.exists():
        raise ConfigurationError(
            f"Configuration file not found: {config_path}. "
            "Please create a config.json file in the ollm install directory."
        )
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigurationError(
            f"Invalid JSON in configuration file {config_path}: {e}"
        )
    except Exception as e:
        raise ConfigurationError(
            f"Error reading configuration file {config_path}: {e}"
        )
    
    try:
        return Config(**config_data)
    except Exception as e:
        raise ConfigurationError(
            f"Invalid configuration in {config_path}: {e}"
        )