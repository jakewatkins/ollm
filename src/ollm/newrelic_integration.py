"""New Relic integration for OLLM observability using direct HTTP APIs."""

import json
import logging
import os
import re
import socket
import sys
import traceback
import uuid
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Dict, Optional, Any, Union
from threading import Lock

# Remove agent dependency since we're using direct APIs
NEW_RELIC_AVAILABLE = True

from .config import Config
from .paths import get_logs_directory
from .secrets import SecretsManager
from .logging_setup import set_newrelic_agent

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
    """Direct New Relic HTTP API client for CLI applications."""
    
    def __init__(self, config: Config, secrets_manager: SecretsManager):
        self.config = config
        self.secrets_manager = secrets_manager
        self.initialized = False
        self.enabled = config.enable_new_relic
        self.api_key = None
        self.account_id = None
        
        # New Relic API endpoints
        self.events_url = "https://insights-collector.newrelic.com/v1/accounts/{}/events"
        self.logs_url = "https://log-api.newrelic.com/log/v1"
        
    def initialize(self) -> bool:
        """Initialize New Relic direct API client.
        
        Returns:
            True if successfully initialized, False otherwise
        """
        if not self.enabled:
            logger.info("New Relic integration disabled in configuration")
            return False
            
        try:
            # Get secrets from Azure Key Vault
            self.api_key = self.secrets_manager.get_secret("NewRelicAPIKey")
            self.account_id = self.secrets_manager.get_secret("NewRelicAccountId")
            
            if not self.api_key or not self.account_id:
                missing = []
                if not self.api_key:
                    missing.append("NewRelicAPIKey")
                if not self.account_id:
                    missing.append("NewRelicAccountId")
                logger.warning(f"New Relic secrets unavailable: {', '.join(missing)}. Continuing without New Relic.")
                return False
            
            print("🚀 Using New Relic Direct HTTP APIs (bypassing agent registration)")
            print(f"🔑 API Key: {self.api_key[:4]}...{self.api_key[-4:]} ({len(self.api_key)} chars)")
            print(f"🏢 Account ID: {self.account_id}")
            
            # Test connectivity to New Relic APIs
            self._test_connectivity()
            
            # Configure log handler to use this agent
            set_newrelic_agent(self)
            
            self.initialized = True
            logger.info(f"New Relic HTTP API client initialized (account: {self.account_id})")
            return True
            
        except Exception as e:
            logger.warning(f"New Relic initialization failed: {e}. Continuing without New Relic.")
            return False
    
    def is_enabled(self) -> bool:
        """Check if New Relic is enabled and working."""
        return self.enabled and self.initialized
    
    def _test_connectivity(self) -> None:
        """Test connectivity to New Relic APIs."""
        try:
            print("🌍 Testing New Relic API connectivity...")
            
            # Test Events API
            events_url = self.events_url.format(self.account_id)
            test_event = [{
                'eventType': 'ConnectivityTest',
                'testTimestamp': int(datetime.utcnow().timestamp() * 1000),
                'success': True
            }]
            
            self._send_events(test_event)
            print("✅ Events API connectivity test successful")
            
            # Test Logs API  
            test_log = [{
                'message': 'New Relic connectivity test log',
                'timestamp': int(datetime.utcnow().timestamp() * 1000),
                'level': 'INFO',
                'service': 'OLLM'
            }]
            
            self._send_logs(test_log)
            print("✅ Logs API connectivity test successful")
            
        except Exception as e:
            print(f"⚠️  API connectivity test failed: {e}")
            # Don't fail initialization on connectivity test failure
    
    def _send_events(self, events: list) -> None:
        """Send events to New Relic Events API."""
        if not self.initialized:
            return
            
        events_url = self.events_url.format(self.account_id)
        headers = {
            'Content-Type': 'application/json',
            'X-Insert-Key': self.api_key
        }
        
        data = json.dumps(events).encode('utf-8')
        
        req = urllib.request.Request(
            events_url,
            data=data,
            headers=headers,
            method='POST'
        )
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.getcode() == 200:
                    print(f"📡 Successfully sent {len(events)} events to New Relic")
                else:
                    print(f"⚠️  Events API returned status: {response.getcode()}")
        except Exception as e:
            print(f"❌ Failed to send events: {e}")
    
    def _send_logs(self, logs: list) -> None:
        """Send logs to New Relic Logs API."""
        if not self.initialized:
            return
            
        headers = {
            'Content-Type': 'application/json',
            'X-License-Key': self.api_key
        }
        
        # Logs API expects a specific format
        payload = {
            'logs': logs
        }
        
        data = json.dumps(payload).encode('utf-8')
        
        req = urllib.request.Request(
            self.logs_url,
            data=data,
            headers=headers,
            method='POST'
        )
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.getcode() == 202:  # Logs API returns 202 Accepted
                    print(f"📋 Successfully sent {len(logs)} logs to New Relic")
                else:
                    print(f"⚠️  Logs API returned status: {response.getcode()}")
        except Exception as e:
            print(f"❌ Failed to send logs: {e}")
    
    def send_custom_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Send a single custom event to New Relic."""
        event = dict(event_data)
        event['eventType'] = event_type
        event['timestamp'] = int(datetime.utcnow().timestamp() * 1000)
        
        # Debug: Print the event being sent
        print(f"🔍 Sending {event_type} event: {json.dumps(event, default=str, indent=2)}")
        
        self._send_events([event])
    
    def send_log_event(self, log_data: Dict[str, Any]) -> None:
        """Send a single log event to New Relic."""
        self._send_logs([log_data])


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
        """Record event to New Relic using direct HTTP API."""
        if not self.agent.is_enabled():
            logger.debug(f"New Relic not available, skipping {event_type} event")
            return
            
        try:
            print(f"📡 Recording {event_type} event: {event_data}")
            self.agent.send_custom_event(event_type, event_data)
            
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
        
        # Only include fields that have valid values (not None) and proper types
        inference_fields = {
            "totalDurationNs": ollama_response.get("total_duration"),
            "loadDurationNs": ollama_response.get("load_duration"),
            "promptEvalCount": ollama_response.get("prompt_eval_count"),
            "promptEvalDurationNs": ollama_response.get("prompt_eval_duration"),
            "evalCount": ollama_response.get("eval_count"),
            "evalDurationNs": ollama_response.get("eval_duration"),
            "doneStatus": ollama_response.get("done"),
            "doneReason": ollama_response.get("done_reason"),
            "createdAt": ollama_response.get("created_at")
        }
        
        # Filter out None values and ensure proper data types
        for field_name, field_value in inference_fields.items():
            if field_value is not None:
                # Convert numeric fields to proper types
                if field_name.endswith('Ns') or field_name.endswith('Count'):
                    try:
                        event_data[field_name] = int(field_value)
                    except (ValueError, TypeError):
                        # Skip invalid numeric values
                        continue
                elif field_name == "doneStatus":
                    event_data[field_name] = bool(field_value)
                else:
                    # String fields
                    event_data[field_name] = str(field_value)
        
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
    
    # Test the integration if successful
    if success and _event_recorder:
        print("🔧 Testing New Relic integration with sample events...")
        try:
            # Test custom event
            _event_recorder._record_event("TestEvent", {
                "testType": "initialization_test", 
                "success": True, 
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Test logging
            test_logger = logging.getLogger("newrelic_test")
            test_logger.info("🧪 New Relic integration test log message")
            
            print("✅ New Relic integration test completed successfully")
        except Exception as e:
            print(f"⚠️ New Relic integration test failed: {e}")
    
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