"""New Relic telemetry integration for ollm."""

import asyncio
import json
import socket
import time
import uuid
from typing import Any, Dict, Optional, Union, Set
import logging

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    tiktoken = None

import httpx

from .config import Config
from .secrets import SecretsManager

logger = logging.getLogger(__name__)


class TokenCounter:
    """Token counting utility using Ollama data with tiktoken fallback."""
    
    def __init__(self):
        self._tiktoken_encoder = None
        if TIKTOKEN_AVAILABLE:
            try:
                self._tiktoken_encoder = tiktoken.encoding_for_model("gpt-4")
            except Exception as e:
                logger.warning(f"Failed to initialize tiktoken encoder: {e}")
                self._tiktoken_encoder = None
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken fallback.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Token count, or character count / 4 as rough estimate if tiktoken unavailable
        """
        if not text:
            return 0
            
        if self._tiktoken_encoder:
            try:
                return len(self._tiktoken_encoder.encode(text))
            except Exception as e:
                logger.debug(f"Failed to count tokens with tiktoken: {e}")
        
        # Rough estimate: 1 token ~= 4 characters
        return max(1, len(text) // 4)


class TelemetryManager:
    """Manages telemetry reporting to New Relic."""
    
    def __init__(self, config: Config, secrets_manager: Optional[SecretsManager] = None):
        """Initialize telemetry manager.
        
        Args:
            config: Application configuration
            secrets_manager: Secrets manager for Azure Key Vault access
        """
        self.config = config
        self.secrets_manager = secrets_manager
        self.enabled = config.telemetry.send_telemetry
        self.timeout = config.telemetry.new_relic_timeout
        self.session_id = str(uuid.uuid4())
        self.hostname = socket.gethostname()
        self.service_name = f"OLLM - {self.hostname}"
        
        self._api_key: Optional[str] = None
        self._account_id: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._token_counter = TokenCounter()
        self._initialized = False
        self._pending_tasks: Set[asyncio.Task] = set()
        
        # Initialize immediately if telemetry is disabled
        if not self.enabled:
            logger.info("Telemetry disabled in configuration")
    
    async def _ensure_initialized(self) -> None:
        """Ensure telemetry is initialized before use."""
        if not self._initialized and self.enabled:
            await self._initialize()
            self._initialized = True
    
    async def _initialize(self) -> None:
        """Initialize New Relic API credentials and client."""
        if not self.enabled:
            return
            
        try:
            if self.secrets_manager:
                # Retry vault access if it was previously marked as inaccessible
                # This handles cases where initial authentication failed but might work now
                if not self.secrets_manager.vault_accessible:
                    logger.info("Retrying Key Vault access for telemetry initialization")
                    vault_test_result = self.secrets_manager.test_vault_access()
                    if not vault_test_result:
                        logger.warning("Key Vault still not accessible, telemetry disabled")
                        self.enabled = False
                        return
                
                self._api_key = self.secrets_manager.get_secret("NewRelicAPIKey")
                self._account_id = self.secrets_manager.get_secret("NewRelicAccountId")
                
                if not self._api_key:
                    logger.warning("NewRelicAPIKey not found in Key Vault, telemetry disabled")
                    self.enabled = False
                    return
                    
                if not self._account_id:
                    logger.warning("NewRelicAccountId not found in Key Vault")
            else:
                logger.warning("No secrets manager available, telemetry disabled")
                self.enabled = False
                return
            
            # Initialize HTTP client
            headers = {
                "Content-Type": "application/json",
                "api-key": self._api_key
            }
            
            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=httpx.Timeout(self.timeout)
            )
            
            logger.info(f"Telemetry initialized with session ID: {self.session_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize telemetry: {e}")
            self.enabled = False
    
    def _create_task(self, coro) -> asyncio.Task:
        """Create a task and track it for cleanup.
        
        Args:
            coro: Coroutine to run as a task
            
        Returns:
            The created task
        """
        task = asyncio.create_task(coro)
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)
        return task
    
    async def _send_event(self, event_data: Dict[str, Any]) -> None:
        """Send event to New Relic asynchronously.
        
        Args:
            event_data: Event data to send
        """
        if not self.enabled:
            return
            
        await self._ensure_initialized()
        
        if not self._client:
            return
            
        try:
            # Add common attributes
            event_data.update({
                "timestamp": int(time.time() * 1000),  # milliseconds
                "service.name": self.service_name,
                "session_id": self.session_id
            })
            
            # Wrap in OTLP logs format
            otlp_payload = {
                "resourceLogs": [{
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": self.service_name}}
                        ]
                    },
                    "scopeLogs": [{
                        "scope": {"name": "ollm-telemetry"},
                        "logRecords": [{
                            "timeUnixNano": str(int(time.time() * 1_000_000_000)),
                            "severityText": "INFO",
                            "body": {"stringValue": json.dumps(event_data)},
                            "attributes": [
                                {"key": k, "value": {"stringValue": str(v) if not isinstance(v, (int, float, bool)) else v}}
                                for k, v in event_data.items()
                            ]
                        }]
                    }]
                }]
            }
            
            response = await self._client.post(
                "https://otlp.nr-data.net:443/v1/logs",
                json=otlp_payload
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to send telemetry to New Relic: {response.status_code} - {response.text}")
                
        except asyncio.TimeoutError:
            logger.error(f"Telemetry request timed out after {self.timeout} seconds")
        except Exception as e:
            logger.error(f"Failed to send telemetry event: {e}")
    
    async def record_inference(
        self,
        model: str,
        prompt_text: str,
        response_text: str,
        ollama_data: Dict[str, Any],
        start_time: float,
        end_time: float
    ) -> None:
        """Record an AI agent inference event.
        
        Args:
            model: Model name used
            prompt_text: Prompt text (for token counting only, not sent to New Relic)
            response_text: Response text (for token counting only, not sent to New Relic)
            ollama_data: Response data from Ollama
            start_time: Request start time
            end_time: Request end time
        """
        if not self.enabled:
            return
            
        await self._ensure_initialized()
            
        # Count tokens using Ollama data first, fallback to tiktoken
        prompt_tokens = ollama_data.get("prompt_eval_count")
        if prompt_tokens is None:
            prompt_tokens = self._token_counter.count_tokens(prompt_text)
            
        response_tokens = ollama_data.get("eval_count")
        if response_tokens is None:
            response_tokens = self._token_counter.count_tokens(response_text)
        
        event_data = {
            "newrelic.event.type": "AIAgentInference",
            "model": model,
            "prompt_tokens": prompt_tokens,
            "response_tokens": response_tokens,
            "end_to_end_duration_ms": int((end_time - start_time) * 1000),
            "total_duration_ns": ollama_data.get("total_duration"),
            "load_duration_ns": ollama_data.get("load_duration"),
            "prompt_eval_duration_ns": ollama_data.get("prompt_eval_duration"),
            "eval_duration_ns": ollama_data.get("eval_duration"),
            "done_reason": ollama_data.get("done_reason")
        }
        
        # Create task for async sending (fire and forget)
        self._create_task(self._send_event(event_data))
    
    async def record_tool_call(
        self,
        tool_name: str,
        success: bool,
        duration_ms: int,
        error_message: Optional[str] = None
    ) -> None:
        """Record a tool call event.
        
        Args:
            tool_name: Name of the tool that was called
            success: Whether the tool call succeeded
            duration_ms: Duration of the tool call in milliseconds
            error_message: Error message if the call failed
        """
        if not self.enabled:
            return
            
        await self._ensure_initialized()
            
        event_data = {
            "newrelic.event.type": "AIAgentToolCall",
            "tool_name": tool_name,
            "success": success,
            "duration_ms": duration_ms
        }
        
        if error_message and not success:
            event_data["error_message"] = error_message
            
        # Create task for async sending (fire and forget)
        self._create_task(self._send_event(event_data))
    
    async def record_skill_usage(
        self,
        skill_name: str,
        success: bool,
        duration_ms: int,
        error_message: Optional[str] = None
    ) -> None:
        """Record a skill usage event.
        
        Args:
            skill_name: Name of the skill that was used
            success: Whether the skill usage succeeded
            duration_ms: Duration of the skill usage in milliseconds
            error_message: Error message if the usage failed
        """
        if not self.enabled:
            return
            
        await self._ensure_initialized()
            
        event_data = {
            "newrelic.event.type": "AIAgentSkillUsage",
            "skill_name": skill_name,
            "success": success,
            "duration_ms": duration_ms
        }
        
        if error_message and not success:
            event_data["error_message"] = error_message
            
        # Create task for async sending (fire and forget)
        self._create_task(self._send_event(event_data))
    
    async def flush_pending(self) -> None:
        """Wait for all pending telemetry tasks to complete.
        
        This ensures all telemetry data is sent before the application exits.
        """
        if not self._pending_tasks:
            logger.debug("No pending telemetry tasks to flush")
            return
            
        logger.info(f"Waiting for {len(self._pending_tasks)} telemetry tasks to complete...")
        try:
            # Wait for all pending tasks with a reasonable timeout
            await asyncio.wait_for(
                asyncio.gather(*self._pending_tasks, return_exceptions=True),
                timeout=10.0  # 10 second timeout for all telemetry to complete
            )
            logger.info("All telemetry tasks completed successfully")
        except asyncio.TimeoutError:
            logger.warning("Telemetry flush timed out - some data may not have been sent")
        except Exception as e:
            logger.error(f"Error flushing telemetry: {e}")
        finally:
            self._pending_tasks.clear()
    
    async def close(self) -> None:
        """Close telemetry client after flushing pending data."""
        # First, flush any pending telemetry
        await self.flush_pending()
        
        # Then close the HTTP client
        if self._client:
            await self._client.aclose()


# Global telemetry manager instance
_telemetry_manager: Optional[TelemetryManager] = None


def initialize_telemetry(config: Config, secrets_manager: Optional[SecretsManager] = None) -> None:
    """Initialize global telemetry manager.
    
    Args:
        config: Application configuration
        secrets_manager: Secrets manager for Azure Key Vault access
    """
    global _telemetry_manager
    _telemetry_manager = TelemetryManager(config, secrets_manager)


def get_telemetry_manager() -> Optional[TelemetryManager]:
    """Get the global telemetry manager instance.
    
    Returns:
        Telemetry manager instance if available, None otherwise
    """
    return _telemetry_manager


async def cleanup_telemetry() -> None:
    """Cleanup telemetry resources."""
    global _telemetry_manager
    if _telemetry_manager:
        await _telemetry_manager.close()
        _telemetry_manager = None


async def flush_telemetry() -> None:
    """Flush any pending telemetry data.
    
    This is a convenience function to ensure all telemetry
    data is sent before the application exits.
    """
    global _telemetry_manager
    if _telemetry_manager:
        await _telemetry_manager.flush_pending()