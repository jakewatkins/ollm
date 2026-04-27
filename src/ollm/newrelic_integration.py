"""New Relic integration for OLLM observability."""

import json
import logging
import os
import re
import socket
import sys
import traceback
import uuid
from datetime import datetime
from typing import Dict, Optional, Any, Union
from threading import Lock

try:
    import newrelic.agent
    NEW_RELIC_AVAILABLE = True
except ImportError:
    NEW_RELIC_AVAILABLE = False

from .config import Config
from .secrets import SecretsManager

logger = logging.getLogger(__name__)

# Global session manager instance
_session_manager: Optional['SessionManager'] = None
_session_lock = Lock()

# Global event recorder instance  
_event_recorder: Optional['EventRecorder'] = None
_recorder_lock = Lock()


class SessionManager:
    """Manages session ID for correlating events across an OLLM run."""
    
    def __init__(self):
        self._session_id: Optional[str] = None
        self._lock = Lock()
    
    def generate_session_id(self) -> str:
        """Generate new UUID session ID."""
        with self._lock:
            self._session_id = str(uuid.uuid4())
            logger.info(f"Generated new session ID: {self._session_id}")
            return self._session_id
    
    def get_session_id(self) -> str:
        """Get current session ID."""
        with self._lock:
            if self._session_id is None:
                self._session_id = str(uuid.uuid4())
                logger.info(f"Generated session ID on demand: {self._session_id}")
            return self._session_id


class NewRelicAgent:
    """Manages New Relic agent initialization and configuration."""
    
    def __init__(self, config: Config, secrets_manager: SecretsManager):
        self.config = config
        self.secrets_manager = secrets_manager
        self.initialized = False
        self.enabled = config.enable_new_relic
        
    def initialize(self) -> bool:
        """Initialize New Relic agent.
        
        Returns:
            True if successfully initialized, False otherwise
        """
        if not self.enabled:
            logger.info("New Relic integration disabled in configuration")
            return False
            
        if not NEW_RELIC_AVAILABLE:
            logger.warning("New Relic library not available. Install with: pip install newrelic")
            return False
            
        try:
            # Get secrets from Azure Key Vault
            api_key = self.secrets_manager.get_secret("NewRelicAPIKey")
            account_id = self.secrets_manager.get_secret("NewRelicAccountId")
            
            if not api_key or not account_id:
                missing = []
                if not api_key:
                    missing.append("NewRelicAPIKey")
                if not account_id:
                    missing.append("NewRelicAccountId")
                logger.warning(f"New Relic secrets unavailable: {', '.join(missing)}. Continuing without New Relic.")
                return False
            
            # Configure New Relic agent
            hostname = socket.gethostname()
            
            # Set environment variables for New Relic agent
            os.environ['NEW_RELIC_LICENSE_KEY'] = api_key
            os.environ['NEW_RELIC_APP_NAME'] = 'OLLM'
            os.environ['NEW_RELIC_ENVIRONMENT'] = self.config.environment
            os.environ['NEW_RELIC_HOST'] = hostname
            os.environ['NEW_RELIC_LOG_LEVEL'] = 'info'
            
            # Initialize the agent
            newrelic.agent.initialize()
            
            self.initialized = True
            logger.info(f"New Relic agent initialized successfully (environment: {self.config.environment}, host: {hostname})")
            return True
            
        except Exception as e:
            logger.warning(f"New Relic initialization failed: {e}. Continuing without New Relic.")
            return False
    
    def is_enabled(self) -> bool:
        """Check if New Relic is enabled and working."""
        return self.enabled and self.initialized


# Content sanitization patterns
SENSITIVE_PATTERNS = [
    # API keys and tokens
    (re.compile(r'(?i)(api[_-]?key|password|token|secret|authorization)["\s]*[:=]["\s]*([^\s"]+)', re.MULTILINE), r'\1: ***'),
    (re.compile(r'(?i)(bearer|basic)["\s]+([^\s"]+)', re.MULTILINE), r'\1 ***'),
    # Environment variables that might contain secrets
    (re.compile(r'(?i)(export\s+|set\s+)([A-Z_]*(?:API|KEY|TOKEN|SECRET|PASSWORD)[A-Z_]*)=([^\s]+)', re.MULTILINE), r'\1\2=***'),
    # File paths that might reveal system info (keep basic structure but hide specifics)
    (re.compile(r'(/Users/[^/\s]+)', re.MULTILINE), r'/Users/***'),
    (re.compile(r'(C:\\Users\\[^\\\\s]+)', re.MULTILINE), r'C:\\Users\\***'),
    # URLs with potential credentials
    (re.compile(r'(https?://)[^:@/]+:[^@/]+@', re.MULTILINE), r'\\1***:***@'),
]


def sanitize_content(content: str, max_size: int = 10240) -> str:
    """Sanitize content by removing sensitive information.
    
    Args:
        content: Content to sanitize
        max_size: Maximum size in bytes (content will be truncated if larger)
        
    Returns:
        Sanitized content
    """
    if not content:
        return content
        
    # Apply sanitization patterns
    sanitized = content
    for pattern, replacement in SENSITIVE_PATTERNS:
        try:
            sanitized = pattern.sub(replacement, sanitized)
        except Exception as e:
            logger.debug(f"Error applying sanitization pattern: {e}")
            continue
    
    # Truncate if too large
    if len(sanitized.encode('utf-8')) > max_size:
        # Find safe truncation point (avoid cutting in middle of UTF-8 character)
        truncated = sanitized.encode('utf-8')[:max_size-20].decode('utf-8', errors='ignore')
        sanitized = truncated + " ... [TRUNCATED]"
    
    return sanitized


def sanitize_error_message(message: str) -> str:
    """Sanitize error messages for logging."""
    return sanitize_content(message, max_size=1024)


class EventRecorder:
    """Records custom events to New Relic."""
    
    def __init__(self, new_relic_agent: NewRelicAgent, session_manager: SessionManager):
        self.agent = new_relic_agent
        self.session_manager = session_manager
        
    def _get_base_event_data(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """Get base event data common to all events."""
        return {
            "sessionId": self.session_manager.get_session_id(),
            "modelName": model_name or "unknown",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _record_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Record event to New Relic with error handling."""
        if not self.agent.is_enabled():
            logger.debug(f"New Relic not available, skipping {event_type} event")
            return
            
        try:
            newrelic.agent.record_custom_event(event_type, event_data)
            logger.debug(f"Recorded {event_type} event to New Relic")
        except Exception as e:
            logger.warning(f"Failed to record {event_type} event to New Relic: {e}")
    
    def record_tool_call(self, tool_name: str, duration_ms: int, status: str, 
                        error_message: Optional[str] = None, error_type: Optional[str] = None,
                        http_status_code: Optional[int] = None, model_name: Optional[str] = None) -> None:
        """Record tool call event."""
        event_data = self._get_base_event_data(model_name)
        event_data.update({
            "eventType": "ToolCall",
            "toolName": tool_name,
            "executionDurationMs": duration_ms,
            "executionStatus": status
        })
        
        if error_message:
            event_data["errorMessage"] = sanitize_error_message(error_message)
        if error_type:
            event_data["errorType"] = error_type
        if http_status_code:
            event_data["httpStatusCode"] = http_status_code
            
        self._record_event("ToolCall", event_data)
    
    def record_skill_usage(self, skill_name: str, duration_ms: int, status: str,
                          error_message: Optional[str] = None, error_type: Optional[str] = None,
                          skill_context: Optional[str] = None, model_name: Optional[str] = None) -> None:
        """Record skill usage event."""
        event_data = self._get_base_event_data(model_name)
        event_data.update({
            "eventType": "SkillUsage",
            "skillName": skill_name,
            "executionDurationMs": duration_ms,
            "executionStatus": status
        })
        
        if error_message:
            event_data["errorMessage"] = sanitize_error_message(error_message)
        if error_type:
            event_data["errorType"] = error_type
        if skill_context:
            event_data["skillContext"] = skill_context
            
        self._record_event("SkillUsage", event_data)
    
    def record_script_execution(self, script_content: str, language: str, duration_ms: int, 
                               status: str, error_message: Optional[str] = None,
                               exit_code: Optional[int] = None, skill_context: Optional[str] = None,
                               model_name: Optional[str] = None) -> None:
        """Record script execution event."""
        event_data = self._get_base_event_data(model_name)
        event_data.update({
            "eventType": "ScriptExecution",
            "scriptLanguage": language,
            "scriptContent": sanitize_content(script_content, max_size=10240),
            "executionDurationMs": duration_ms,
            "executionStatus": status
        })
        
        if error_message:
            event_data["errorMessage"] = sanitize_error_message(error_message)
        if exit_code is not None:
            event_data["exitCode"] = exit_code
        if skill_context:
            event_data["skillContext"] = skill_context
            
        self._record_event("ScriptExecution", event_data)
    
    def record_inference(self, ollama_response: Dict[str, Any], model_name: Optional[str] = None) -> None:
        """Record inference metrics event."""
        event_data = self._get_base_event_data(model_name or ollama_response.get("model"))
        event_data.update({
            "eventType": "Inference",
            "totalDurationNs": ollama_response.get("total_duration"),
            "loadDurationNs": ollama_response.get("load_duration"),
            "promptEvalCount": ollama_response.get("prompt_eval_count"),
            "promptEvalDurationNs": ollama_response.get("prompt_eval_duration"),
            "evalCount": ollama_response.get("eval_count"),
            "evalDurationNs": ollama_response.get("eval_duration"),
            "doneStatus": ollama_response.get("done"),
            "doneReason": ollama_response.get("done_reason"),
            "createdAt": ollama_response.get("created_at")
        })
        
        self._record_event("Inference", event_data)
    
    def record_error(self, error_type: str, error_message: str, error_source: str,
                    stack_trace: Optional[str] = None, context_info: Optional[str] = None,
                    severity: str = "medium", model_name: Optional[str] = None) -> None:
        """Record error event."""
        event_data = self._get_base_event_data(model_name)
        event_data.update({
            "eventType": "Error",
            "errorType": error_type,
            "errorMessage": sanitize_error_message(error_message),
            "errorSource": error_source,
            "severity": severity
        })
        
        if stack_trace:
            event_data["stackTrace"] = sanitize_content(stack_trace, max_size=5000)
        if context_info:
            event_data["contextInfo"] = sanitize_content(context_info, max_size=1000)
            
        self._record_event("Error", event_data)


def initialize_new_relic(config: Config, secrets_manager: SecretsManager) -> tuple[bool, Optional[SessionManager], Optional[EventRecorder]]:
    """Initialize New Relic integration components.
    
    Args:
        config: OLLM configuration
        secrets_manager: Secrets manager for Azure Key Vault access
        
    Returns:
        Tuple of (success, session_manager, event_recorder)
    """
    global _session_manager, _event_recorder
    
    with _session_lock:
        if _session_manager is None:
            _session_manager = SessionManager()
            _session_manager.generate_session_id()
    
    # Initialize New Relic agent
    agent = NewRelicAgent(config, secrets_manager)
    success = agent.initialize()
    
    with _recorder_lock:
        if _event_recorder is None:
            _event_recorder = EventRecorder(agent, _session_manager)
    
    return success, _session_manager, _event_recorder


def get_session_manager() -> Optional[SessionManager]:
    """Get global session manager instance."""
    return _session_manager


def get_event_recorder() -> Optional[EventRecorder]:
    """Get global event recorder instance."""
    return _event_recorder


def setup_error_tracking() -> None:
    """Setup global exception handler for error events."""
    def handle_exception(exc_type, exc_value, exc_traceback):
        """Global exception handler that records error events."""
        if _event_recorder and exc_type != KeyboardInterrupt:
            try:
                error_message = str(exc_value)
                stack_trace = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
                error_source = "global_handler"
                
                _event_recorder.record_error(
                    error_type="unhandled_exception",
                    error_message=error_message,
                    error_source=error_source,
                    stack_trace=stack_trace,
                    severity="high"
                )
            except Exception as e:
                logger.warning(f"Failed to record unhandled exception to New Relic: {e}")
        
        # Call original exception handler
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    
    sys.excepthook = handle_exception