"""MCP configuration schema and parsing."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from pydantic import BaseModel, field_validator, model_validator

from ..errors import ConfigurationError


class SandboxConfig(BaseModel):
    """Sandbox configuration for MCP servers."""
    
    # Filesystem rules
    filesystem_allow_write: Optional[List[str]] = None
    filesystem_deny_read: Optional[List[str]] = None  
    filesystem_deny_write: Optional[List[str]] = None
    
    # Network rules
    network_allowed_domains: Optional[List[str]] = None
    network_denied_domains: Optional[List[str]] = None
    
    class Config:
        alias_generator = lambda field_name: field_name.replace('_', '.')
        populate_by_name = True


class DevConfig(BaseModel):
    """Development configuration for MCP servers."""
    
    watch: Optional[str] = None
    debug: Optional[Dict[str, Any]] = None


class StdioServerConfig(BaseModel):
    """Configuration for stdio MCP server."""
    
    type: str = "stdio"
    command: str
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    env_file: Optional[str] = None
    sandbox_enabled: Optional[bool] = None
    sandbox: Optional[SandboxConfig] = None
    dev: Optional[DevConfig] = None
    
    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v != "stdio":
            raise ValueError(f"Expected type 'stdio', got '{v}'")
        return v
    
    class Config:
        alias_generator = lambda field_name: field_name.replace('_', '')
        populate_by_name = True


class HttpServerConfig(BaseModel):
    """Configuration for HTTP/SSE MCP server."""
    
    type: str
    url: str
    headers: Optional[Dict[str, str]] = None
    dev: Optional[DevConfig] = None
    
    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ["http", "sse"]:
            raise ValueError(f"Expected type 'http' or 'sse', got '{v}'")
        return v


class InputConfig(BaseModel):
    """Configuration for runtime input prompts."""
    
    type: str = "promptString"
    id: str
    description: str
    password: Optional[bool] = False
    
    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v != "promptString":
            raise ValueError(f"Expected type 'promptString', got '{v}'")
        return v


class McpConfig(BaseModel):
    """Complete MCP configuration."""
    
    servers: Dict[str, Union[StdioServerConfig, HttpServerConfig]]
    inputs: Optional[List[InputConfig]] = None
    
    @model_validator(mode='before')
    @classmethod
    def validate_server_configs(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and parse server configurations."""
        if 'servers' not in values:
            return values
            
        servers = values['servers']
        parsed_servers = {}
        
        for name, config in servers.items():
            if not isinstance(config, dict):
                continue
                
            server_type = config.get('type', '')
            
            if server_type == 'stdio':
                parsed_servers[name] = StdioServerConfig(**config)
            elif server_type in ['http', 'sse']:
                parsed_servers[name] = HttpServerConfig(**config)
            else:
                raise ValueError(f"Unknown server type '{server_type}' for server '{name}'")
        
        values['servers'] = parsed_servers
        return values


def load_mcp_config(install_dir: Path) -> Optional[McpConfig]:
    """Load MCP configuration from mcp.json.
    
    Args:
        install_dir: Directory to search for mcp.json
        
    Returns:
        McpConfig if mcp.json exists and is valid, None otherwise
        
    Raises:
        ConfigurationError: If mcp.json exists but is invalid
    """
    mcp_path = install_dir / "mcp.json"
    
    if not mcp_path.exists():
        return None
    
    try:
        with open(mcp_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Import secrets function locally to avoid circular imports
        from ..secrets import process_secrets_in_dict
        
        # Process secrets in MCP configuration
        data = process_secrets_in_dict(data)
        
        return McpConfig(**data)
    
    except json.JSONDecodeError as e:
        raise ConfigurationError(f"Invalid JSON in {mcp_path}: {e}")
    except Exception as e:
        raise ConfigurationError(f"Error loading MCP config from {mcp_path}: {e}")