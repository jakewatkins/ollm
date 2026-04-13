"""Container lifecycle management for script execution."""

import asyncio
import logging
import tempfile
import os
from typing import Dict, List, Optional, Any
from pathlib import Path
import json

from .docker_client import DockerClient, ContainerSpec, ExecutionResult
from ..config import ScriptExecutionConfig
from ..errors import OllmError

logger = logging.getLogger(__name__)

class ContainerManager:
    """High-level container lifecycle manager."""
    
    def __init__(self, config: ScriptExecutionConfig, docker_client: DockerClient):
        """Initialize container manager.
        
        Args:
            config: Script execution configuration
            docker_client: Initialized Docker client
        """
        self.config = config
        self.docker_client = docker_client
        self._active_containers: Dict[str, str] = {}  # task_id -> container_id
    
    async def execute_script(
        self,
        script_content: str,
        script_language: str,
        task_id: str,
        skill_resources: Dict[str, str] = None,
        environment_vars: Dict[str, str] = None
    ) -> ExecutionResult:
        """Execute a script in an isolated container.
        
        Args:
            script_content: The script code to execute
            script_language: Programming language (python, bash, etc.)
            task_id: Unique identifier for this execution
            skill_resources: Additional files to mount (filename -> content)
            environment_vars: Environment variables to set
            
        Returns:
            ExecutionResult with execution details
            
        Raises:
            OllmError: If execution fails or is not supported
        """
        if task_id in self._active_containers:
            raise OllmError(f"Task {task_id} is already running")
        
        # Validate script language
        if not self._is_language_supported(script_language):
            raise OllmError(f"Unsupported script language: {script_language}")
        
        # Create temporary directory for script files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            try:
                # Prepare script file
                script_file = await self._prepare_script_file(
                    script_content, script_language, temp_path
                )
                
                # Prepare skill resources
                if skill_resources:
                    await self._prepare_skill_resources(skill_resources, temp_path)
                
                # Build container specification
                spec = await self._build_container_spec(
                    script_file, script_language, temp_path, environment_vars
                )
                
                # Track active container
                self._active_containers[task_id] = "pending"
                
                # Execute container
                result = await self.docker_client.run_container(
                    spec=spec,
                    timeout_seconds=self.config.execution_timeout_seconds
                )
                
                # Update tracking
                self._active_containers[task_id] = result.container_id
                
                logger.info(
                    f"Script execution completed",
                    extra={
                        "task_id": task_id,
                        "language": script_language,
                        "exit_code": result.exit_code,
                        "execution_time": result.execution_time,
                        "container_id": result.container_id
                    }
                )
                
                return result
                
            except Exception as e:
                logger.error(f"Script execution failed for task {task_id}: {e}")
                raise
            
            finally:
                # Cleanup tracking
                self._active_containers.pop(task_id, None)
    
    async def _prepare_script_file(
        self,
        script_content: str,
        script_language: str,
        temp_path: Path
    ) -> Path:
        """Prepare the script file for execution.
        
        Args:
            script_content: Script source code
            script_language: Programming language
            temp_path: Temporary directory path
            
        Returns:
            Path to the prepared script file
        """
        # Get file extension for the language
        extensions = {
            "python": "py",
            "bash": "sh",
            "shell": "sh", 
            "javascript": "js",
            "node": "js"
        }
        
        extension = extensions.get(script_language.lower(), script_language.lower())
        script_file = temp_path / f"script.{extension}"
        
        # Write script content
        script_file.write_text(script_content, encoding="utf-8")
        
        # Make executable for shell scripts
        if extension == "sh":
            script_file.chmod(0o755)
        
        logger.debug(f"Prepared script file: {script_file} ({len(script_content)} bytes)")
        
        return script_file
    
    async def _prepare_skill_resources(
        self,
        skill_resources: Dict[str, str],
        temp_path: Path
    ) -> None:
        """Prepare additional skill resource files.
        
        Args:
            skill_resources: Mapping of filename to file content
            temp_path: Temporary directory path
        """
        for filename, content in skill_resources.items():
            # Sanitize filename
            safe_filename = self._sanitize_filename(filename)
            resource_file = temp_path / safe_filename
            
            # Write resource content
            resource_file.write_text(content, encoding="utf-8")
            
            logger.debug(f"Prepared resource file: {safe_filename} ({len(content)} bytes)")
    
    async def _build_container_spec(
        self,
        script_file: Path,
        script_language: str,
        temp_path: Path,
        environment_vars: Dict[str, str]
    ) -> ContainerSpec:
        """Build container specification for script execution.
        
        Args:
            script_file: Path to the script file
            script_language: Programming language
            temp_path: Temporary directory with all files
            environment_vars: Additional environment variables
            
        Returns:
            ContainerSpec for the container
        """
        # Build command based on language
        command = self._build_execution_command(script_file, script_language)
        
        # Prepare environment
        env = {
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": "/workspace",
            **self.config.environment
        }
        
        if environment_vars:
            env.update(environment_vars)
        
        # Prepare volumes (mount temp directory as read-only)
        volumes = {
            str(temp_path): {
                "bind": "/workspace",
                "mode": "ro"
            }
        }
        
        return ContainerSpec(
            image=self.config.image,
            command=command,
            environment=env,
            working_dir="/workspace",
            volumes=volumes,
            network_disabled=True,
            memory_limit=self.config.resources.memory_limit,
            cpu_quota=int(self.config.resources.cpu_limit * 100000),  # Convert to quota
            cpu_period=100000
        )
    
    def _build_execution_command(self, script_file: Path, script_language: str) -> List[str]:
        """Build the execution command for the script.
        
        Args:
            script_file: Path to the script file
            script_language: Programming language
            
        Returns:
            Command list to execute the script
        """
        script_name = script_file.name
        language = script_language.lower()
        
        if language == "python":
            return ["python3", script_name]
        elif language in ("bash", "shell"):
            return ["bash", script_name]
        elif language in ("javascript", "node"):
            return ["node", script_name]
        else:
            # Fallback: try to execute directly
            return [f"./{script_name}"]
    
    def _is_language_supported(self, language: str) -> bool:
        """Check if a script language is supported.
        
        Args:
            language: Programming language name
            
        Returns:
            True if language is supported
        """
        supported = {"python", "bash", "shell", "javascript", "node"}
        return language.lower() in supported
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize a filename for safe usage.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove path separators and dangerous characters
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
        sanitized = "".join(c for c in filename if c in safe_chars)
        
        # Ensure it's not empty and doesn't start with dot
        if not sanitized or sanitized.startswith("."):
            sanitized = f"file_{sanitized}"
        
        return sanitized
    
    async def cleanup(self) -> None:
        """Cleanup any remaining active containers."""
        if self._active_containers:
            logger.warning(f"Cleaning up {len(self._active_containers)} active containers")
            
            # Note: Containers should already be cleaned up by DockerClient,
            # but we track them here for potential future force-cleanup
            self._active_containers.clear()
    
    def get_active_tasks(self) -> List[str]:
        """Get list of currently active task IDs.
        
        Returns:
            List of active task IDs
        """
        return list(self._active_containers.keys())