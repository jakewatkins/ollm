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
    log_filename: Optional[str] = Field(default=None, alias="logFilename", description="Absolute path to log file")
    
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


class ScriptExecutionResourcesConfig(BaseModel):
    """Configuration for script execution resource limits."""
    memory_limit: str = Field(default="128m", alias="memoryLimit", description="Memory limit for containers")
    cpu_limit: float = Field(default=0.5, alias="cpuLimit", ge=0.1, le=8.0, description="CPU limit for containers")


class ScriptExecutionConfig(BaseModel):
    """Configuration for script execution."""
    enabled: bool = Field(default=False, description="Enable script execution")
    image: str = Field(default="ollm-runner:latest", description="Docker image for script execution")
    execution_timeout_seconds: int = Field(default=30, alias="executionTimeoutSeconds", ge=1, le=600, description="Execution timeout in seconds")
    environment: Dict[str, str] = Field(default_factory=dict, description="Environment variables for containers")
    resources: ScriptExecutionResourcesConfig = Field(default_factory=ScriptExecutionResourcesConfig)
    
    class Config:
        validate_by_name = True


class Config(BaseModel):
    """Main configuration for ollm."""
    base_url: str = Field(..., alias="baseUrl", description="Base URL for Ollama server")
    api_key: Optional[str] = Field(default=None, alias="apiKey", description="API key for Ollama")
    keyvault: Optional[str] = Field(default=None, description="Azure Key Vault name for secrets")
    agent_loop: AgentLoopConfig = Field(default_factory=AgentLoopConfig, alias="agentLoop")
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    skills: SkillsConfig = Field(default_factory=SkillsConfig)
    script_execution: ScriptExecutionConfig = Field(default_factory=ScriptExecutionConfig, alias="scriptExecution")
    enable_new_relic: bool = Field(default=True, alias="EnableNewRelic", description="Enable New Relic observability")
    environment: str = Field(default="dev", description="Environment name for New Relic")
    
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


def load_config(config_path: Optional[Path] = None, verbose: bool = False) -> Config:
    """Load configuration from config JSON file.
    
    Args:
        config_path: Optional path to config file. If None, uses default location.
        verbose: Whether to show secret warnings to console
    
    Returns:
        Loaded configuration object
        
    Raises:
        ConfigurationError: If config cannot be loaded or is invalid
    """
    if config_path is None:
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
        # Import secrets functions locally to avoid circular imports
        from .secrets import initialize_secrets_manager, process_secrets_in_dict
        
        # Initialize secrets manager if keyvault is specified
        keyvault_name = config_data.get('keyvault')
        initialize_secrets_manager(keyvault_name, verbose=verbose)
        
        # Process secrets in config data
        config_data = process_secrets_in_dict(config_data)
        
        return Config(**config_data)
    except Exception as e:
        raise ConfigurationError(
            f"Invalid configuration in {config_path}: {e}"
        )