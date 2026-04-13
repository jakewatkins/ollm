"""Script execution infrastructure for ollm skills.

This module provides Docker-based script execution capabilities for skills
that require running code in isolated environments.

Components:
- DockerClient: Docker API wrapper for container operations
- ContainerManager: Container lifecycle management and resource monitoring  
- ScriptExecutor: High-level orchestrator for script execution
- ScriptTool: MCP tool for exposing script execution to the agent loop

Security Features:
- Isolated container execution
- Resource limits (CPU, memory, timeout)
- Read-only skill files
- No host file system access
- Network restrictions
"""

from .docker_client import DockerClient
from .container_manager import ContainerManager
from .executor import ScriptExecutor
from .script_tool import ScriptTool

__all__ = [
    "DockerClient",
    "ContainerManager", 
    "ScriptExecutor",
    "ScriptTool"
]