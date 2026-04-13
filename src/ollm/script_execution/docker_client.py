"""Docker client wrapper for script execution."""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from contextlib import asynccontextmanager

import docker
from docker.models.containers import Container
from docker.errors import DockerException, ContainerError, ImageNotFound

from ..config import ScriptExecutionConfig
from ..exceptions import OllmError

logger = logging.getLogger(__name__)

@dataclass
class ContainerSpec:
    """Container specification for script execution."""
    image: str
    command: List[str]
    environment: Dict[str, str]
    working_dir: str = "/workspace"
    volumes: Dict[str, Dict[str, str]] = None
    network_disabled: bool = True
    memory_limit: str = "128m"
    cpu_quota: int = 50000  # 50% of 1 CPU
    cpu_period: int = 100000

@dataclass
class ExecutionResult:
    """Result of script execution."""
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    container_id: str
    timed_out: bool = False

class DockerClient:
    """Docker API wrapper for secure script execution."""
    
    def __init__(self, config: ScriptExecutionConfig):
        """Initialize Docker client with configuration.
        
        Args:
            config: Script execution configuration
        """
        self.config = config
        self._client: Optional[docker.DockerClient] = None
        
    async def initialize(self) -> None:
        """Initialize Docker client connection.
        
        Raises:
            OllmError: If Docker is not available or configuration is invalid
        """
        try:
            # Create Docker client (synchronous)
            self._client = docker.from_env()
            
            # Test Docker connectivity
            self._client.ping()
            
            # Ensure required image exists
            await self._ensure_image_available()
            
            logger.info("Docker client initialized successfully")
            
        except DockerException as e:
            raise OllmError(f"Failed to connect to Docker: {e}")
        except Exception as e:
            raise OllmError(f"Unexpected error initializing Docker client: {e}")
    
    async def cleanup(self) -> None:
        """Cleanup Docker client resources."""
        if self._client:
            try:
                self._client.close()
                logger.debug("Closed Docker client")
            except Exception as e:
                logger.error(f"Error closing Docker client: {e}")
            finally:
                self._client = None
    
    async def _ensure_image_available(self) -> None:
        """Ensure the required Docker image is available.
        
        Raises:
            OllmError: If image is not available and cannot be pulled
        """
        try:
            # Check if image exists locally
            self._client.images.get(self.config.image)
            logger.debug(f"Docker image '{self.config.image}' available locally")
            
        except ImageNotFound:
            logger.info(f"Docker image '{self.config.image}' not found locally, attempting to pull")
            
            # Attempt to pull the image
            try:
                self._client.images.pull(self.config.image)
                logger.info(f"Successfully pulled Docker image '{self.config.image}'")
                
            except DockerException as e:
                raise OllmError(f"Failed to pull Docker image '{self.config.image}': {e}")
    
    async def run_container(self, spec: ContainerSpec, timeout_seconds: int) -> ExecutionResult:
        """Run a container with the given specification.
        
        Args:
            spec: Container specification
            timeout_seconds: Maximum execution time in seconds
            
        Returns:
            ExecutionResult with exit code, output, and metadata
            
        Raises:
            OllmError: If container execution fails
        """
        if not self._client:
            raise OllmError("Docker client not initialized")
        
        container = None
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Create container with security restrictions
            container = self._client.containers.create(
                image=spec.image,
                command=spec.command,
                environment=spec.environment,
                working_dir=spec.working_dir,
                volumes=spec.volumes or {},
                network_disabled=spec.network_disabled,
                mem_limit=spec.memory_limit,
                cpu_quota=spec.cpu_quota,
                cpu_period=spec.cpu_period,
                detach=True,
                remove=False,  # We'll remove manually for better error handling
                user="1000:1000",  # Non-root user
                read_only=True,  # Read-only filesystem
                tmpfs={"/tmp": "noexec,nosuid,size=64m"},  # Limited tmp space
                cap_drop=["ALL"],  # Drop all capabilities
                security_opt=["no-new-privileges:true"],  # Security hardening
            )
            
            logger.debug(f"Created container {container.id[:12]} with image '{spec.image}'")
            
            # Start container
            container.start()
            
            # Wait for completion with timeout
            try:
                exit_code = await asyncio.wait_for(
                    self._wait_for_container(container),
                    timeout=timeout_seconds
                )
                timed_out = False
                
            except asyncio.TimeoutError:
                logger.warning(f"Container {container.id[:12]} timed out after {timeout_seconds}s")
                container.stop(timeout=5)
                exit_code = -1
                timed_out = True
            
            # Get execution time
            end_time = asyncio.get_event_loop().time()
            execution_time = end_time - start_time
            
            # Get output
            stdout = ""
            stderr = ""
            
            try:
                logs = container.logs(stdout=True, stderr=True)
                # Docker returns combined output, we'd need to separate if needed
                stdout = logs.decode('utf-8', errors='replace')
                
            except Exception as e:
                logger.error(f"Failed to get container logs: {e}")
                stderr = f"Failed to retrieve logs: {e}"
            
            return ExecutionResult(
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                execution_time=execution_time,
                container_id=container.id[:12],
                timed_out=timed_out
            )
            
        except DockerException as e:
            raise OllmError(f"Docker container execution failed: {e}")
        
        except Exception as e:
            raise OllmError(f"Unexpected error running container: {e}")
        
        finally:
            # Cleanup container
            if container:
                try:
                    container.remove(force=True)
                    logger.debug(f"Removed container {container.id[:12]}")
                except Exception as e:
                    logger.error(f"Failed to remove container {container.id[:12]}: {e}")
    
    async def _wait_for_container(self, container: Container) -> int:
        """Wait for container completion in an async manner.
        
        Args:
            container: Docker container to wait for
            
        Returns:
            Container exit code
        """
        loop = asyncio.get_event_loop()
        
        while True:
            # Check container status in executor to avoid blocking
            status = await loop.run_in_executor(None, lambda: container.reload())
            
            if container.status == "exited":
                return container.attrs["State"]["ExitCode"]
            
            elif container.status in ("stopped", "dead"):
                return -1
            
            # Sleep briefly before checking again
            await asyncio.sleep(0.1)
    
    def get_client_info(self) -> Dict[str, Any]:
        """Get Docker client information for debugging.
        
        Returns:
            Dictionary with Docker version and status info
        """
        if not self._client:
            return {"status": "not_initialized"}
        
        try:
            version_info = self._client.version()
            info = self._client.info()
            
            return {
                "status": "connected",
                "version": version_info.get("Version", "unknown"),
                "api_version": version_info.get("ApiVersion", "unknown"),
                "containers": info.get("Containers", 0),
                "images": info.get("Images", 0)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }