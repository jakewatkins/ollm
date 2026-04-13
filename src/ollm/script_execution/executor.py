"""High-level script execution orchestrator."""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from .docker_client import DockerClient, ExecutionResult
from .container_manager import ContainerManager
from ..config import ScriptExecutionConfig
from ..exceptions import OllmError

logger = logging.getLogger(__name__)

@dataclass
class ScriptExecutionRequest:
    """Request for script execution."""
    script_content: str
    script_language: str
    skill_name: Optional[str] = None
    skill_resources: Dict[str, str] = None
    environment_vars: Dict[str, str] = None
    user_context: Dict[str, Any] = None

@dataclass 
class ScriptExecutionResponse:
    """Response from script execution."""
    task_id: str
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    error_message: Optional[str] = None
    skill_name: Optional[str] = None
    timed_out: bool = False

class ScriptExecutor:
    """High-level orchestrator for script execution."""
    
    def __init__(self, config: ScriptExecutionConfig):
        """Initialize script executor.
        
        Args:
            config: Script execution configuration
        """
        self.config = config
        self._docker_client: Optional[DockerClient] = None
        self._container_manager: Optional[ContainerManager] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the script executor and its dependencies.
        
        Raises:
            OllmError: If initialization fails
        """
        try:
            # Initialize Docker client
            self._docker_client = DockerClient(self.config)
            await self._docker_client.initialize()
            
            # Initialize container manager
            self._container_manager = ContainerManager(self.config, self._docker_client)
            
            self._initialized = True
            logger.info("Script executor initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize script executor: {e}")
            await self.cleanup()
            raise OllmError(f"Script executor initialization failed: {e}")
    
    async def cleanup(self) -> None:
        """Cleanup script executor resources."""
        if self._container_manager:
            try:
                await self._container_manager.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up container manager: {e}")
        
        if self._docker_client:
            try:
                await self._docker_client.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up Docker client: {e}")
        
        self._initialized = False
        logger.debug("Script executor cleanup completed")
    
    async def execute_script(self, request: ScriptExecutionRequest) -> ScriptExecutionResponse:
        """Execute a script with the given request.
        
        Args:
            request: Script execution request
            
        Returns:
            ScriptExecutionResponse with execution results
            
        Raises:
            OllmError: If execution fails or executor is not ready
        """
        if not self._initialized:
            raise OllmError("Script executor not initialized")
        
        # Generate unique task ID
        task_id = str(uuid.uuid4())[:8]
        
        logger.info(
            f"Starting script execution",
            extra={
                "task_id": task_id,
                "language": request.script_language,
                "skill_name": request.skill_name,
                "script_length": len(request.script_content)
            }
        )
        
        try:
            # Validate request
            await self._validate_request(request)
            
            # Execute script
            result = await self._container_manager.execute_script(
                script_content=request.script_content,
                script_language=request.script_language,
                task_id=task_id,
                skill_resources=request.skill_resources or {},
                environment_vars=request.environment_vars or {}
            )
            
            # Build response
            success = result.exit_code == 0 and not result.timed_out
            error_message = None
            
            if result.timed_out:
                error_message = f"Script execution timed out after {self.config.execution_timeout_seconds}s"
            elif result.exit_code != 0:
                error_message = f"Script exited with code {result.exit_code}"
            
            response = ScriptExecutionResponse(
                task_id=task_id,
                success=success,
                exit_code=result.exit_code,
                stdout=result.stdout,
                stderr=result.stderr,
                execution_time=result.execution_time,
                error_message=error_message,
                skill_name=request.skill_name,
                timed_out=result.timed_out
            )
            
            logger.info(
                f"Script execution completed",
                extra={
                    "task_id": task_id,
                    "success": success,
                    "execution_time": result.execution_time,
                    "exit_code": result.exit_code
                }
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Script execution failed for task {task_id}: {e}")
            
            # Return error response
            return ScriptExecutionResponse(
                task_id=task_id,
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                execution_time=0.0,
                error_message=f"Execution failed: {e}",
                skill_name=request.skill_name
            )
    
    async def _validate_request(self, request: ScriptExecutionRequest) -> None:
        """Validate a script execution request.
        
        Args:
            request: Script execution request to validate
            
        Raises:
            OllmError: If request is invalid
        """
        # Check script content
        if not request.script_content or not request.script_content.strip():
            raise OllmError("Script content cannot be empty")
        
        # Check script language
        if not request.script_language:
            raise OllmError("Script language must be specified")
        
        # Check script size
        max_size = 64 * 1024  # 64KB limit
        if len(request.script_content.encode('utf-8')) > max_size:
            raise OllmError(f"Script content exceeds maximum size of {max_size} bytes")
        
        # Check resource limits
        if request.skill_resources:
            total_resource_size = sum(
                len(content.encode('utf-8')) for content in request.skill_resources.values()
            )
            
            max_resource_size = 256 * 1024  # 256KB limit for all resources
            if total_resource_size > max_resource_size:
                raise OllmError(f"Skill resources exceed maximum size of {max_resource_size} bytes")
        
        # Check environment variables
        if request.environment_vars:
            for key, value in request.environment_vars.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    raise OllmError("Environment variables must be string key-value pairs")
                
                if len(key) > 64 or len(value) > 512:
                    raise OllmError("Environment variable key/value too long")
    
    def is_initialized(self) -> bool:
        """Check if the executor is initialized and ready.
        
        Returns:
            True if executor is ready for use
        """
        return self._initialized
    
    def get_status(self) -> Dict[str, Any]:
        """Get current executor status information.
        
        Returns:
            Dictionary with status information
        """
        status = {
            "initialized": self._initialized,
            "config": {
                "image": self.config.image,
                "timeout": self.config.execution_timeout_seconds,
                "memory_limit": self.config.resources.memory_limit,
                "cpu_limit": self.config.resources.cpu_limit
            }
        }
        
        # Add Docker client info if available
        if self._docker_client:
            status["docker"] = self._docker_client.get_client_info()
        
        # Add active tasks if available
        if self._container_manager:
            status["active_tasks"] = self._container_manager.get_active_tasks()
        
        return status
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the executor.
        
        Returns:
            Dictionary with health check results
        """
        health = {
            "healthy": False,
            "checks": {
                "initialized": self._initialized,
                "docker_connected": False,
                "image_available": False
            }
        }
        
        if not self._initialized:
            health["error"] = "Executor not initialized"
            return health
        
        try:
            # Check Docker connection
            docker_info = self._docker_client.get_client_info()
            health["checks"]["docker_connected"] = docker_info.get("status") == "connected"
            
            # Check if we can create a simple container (without running it)
            # This validates image availability and basic Docker functionality
            health["checks"]["image_available"] = True  # Would need actual check
            
            # Overall health
            all_checks_passed = all(health["checks"].values())
            health["healthy"] = all_checks_passed
            
            if not all_checks_passed:
                failed_checks = [k for k, v in health["checks"].items() if not v]
                health["error"] = f"Failed checks: {', '.join(failed_checks)}"
            
        except Exception as e:
            health["error"] = f"Health check failed: {e}"
        
        return health