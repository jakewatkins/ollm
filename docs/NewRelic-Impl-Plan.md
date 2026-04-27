# New Relic Integration Implementation Plan

## Overview
This document outlines the detailed implementation plan for integrating New Relic observability into OLLM. The implementation will add comprehensive telemetry including logging, custom events, and performance metrics as specified in the NewRelic-requirements.md document.

## Architecture Analysis

### Current OLLM Architecture
- **Configuration Management**: Pydantic-based config system in `config.py`
- **Logging**: Custom logging setup in `logging_setup.py` with secure formatters
- **Secrets Management**: Azure Key Vault integration in `secrets.py` 
- **Application Flow**: 
  - Entry: `__main__.py` → `cli.py` → `app.py`
  - MCP Integration: `mcp/client.py` for tool calls
  - Skills Framework: `skills/loader.py`, `skills/selector.py` for skill execution
  - Script Execution: `script_execution/` for LLM-generated script execution
  - Ollama Communication: `ollama_client.py` for inference
- **Current Version**: 1.2.0 (needs update to 1.3.0)

## Implementation Phases

### Phase 1: Foundation & Configuration (Priority 1)
**Estimated Time**: 2-3 hours

#### 1.1 Update Dependencies & Version
- **File**: `pyproject.toml`
  - Add `newrelic>=9.0.0` to dependencies
  - Update version from "1.2.0" to "1.3.0"

#### 1.2 Update Application Version  
- **File**: `src/ollm/__init__.py`
  - Update `__version__ = "1.3.0"`

#### 1.3 Configuration Schema Updates
- **File**: `src/ollm/config.py`
  - Add `LoggingConfig.log_filename: Optional[str]` field
  - Add `Config.enable_new_relic: bool` field (default: True)
  - Add `Config.environment: str` field (default: "dev")
  - Update config loading to handle missing fields gracefully

#### 1.4 New Relic Integration Module
- **New File**: `src/ollm/newrelic_integration.py`
  - Session ID management (UUID generation and global access)
  - New Relic agent initialization and configuration
  - Custom event recording functions
  - Content sanitization utilities
  - Error handling for New Relic failures

### Phase 2: Core New Relic Integration (Priority 1)
**Estimated Time**: 4-5 hours

#### 2.1 Session Management
- **File**: `src/ollm/newrelic_integration.py`
  ```python
  class SessionManager:
      def __init__(self):
          self.session_id: Optional[str] = None
      
      def generate_session_id(self) -> str:
          """Generate new UUID session ID"""
          
      def get_session_id(self) -> str:
          """Get current session ID"""
  ```

#### 2.2 New Relic Agent Setup
- **File**: `src/ollm/newrelic_integration.py` 
  ```python
  class NewRelicAgent:
      def __init__(self, config: Config, secrets_manager: SecretsManager):
          """Initialize New Relic agent with config and secrets"""
      
      def initialize(self) -> bool:
          """Setup New Relic agent, return success status"""
      
      def is_enabled(self) -> bool:
          """Check if New Relic is enabled and working"""
  ```

#### 2.3 Content Sanitization
- **File**: `src/ollm/newrelic_integration.py`
  ```python
  def sanitize_content(content: str) -> str:
      """Sanitize content by replacing sensitive patterns with ***"""
      
  def sanitize_error_message(message: str) -> str:
      """Sanitize error messages for logging"""
  ```

#### 2.4 Application Integration
- **File**: `src/ollm/app.py`
  - Add New Relic initialization after config loading but before MCP/skills setup
  - Initialize session manager and make session ID globally accessible
  - Integration point: After `setup_logging()` call in `initialize()` method

### Phase 3: Logging Integration (Priority 1) 
**Estimated Time**: 3-4 hours

#### 3.1 Enhanced Logging Configuration
- **File**: `src/ollm/logging_setup.py`
  - Add date-based log file rollover with format: `logfile-YYYYMMDD.log`
  - Add New Relic logging handler integration
  - Maintain existing secure formatters
  - Support absolute path log filenames from config

#### 3.2 Log File Management
- **File**: `src/ollm/logging_setup.py`
  ```python
  def get_log_filename(config: LoggingConfig) -> str:
      """Generate date-based log filename"""
      
  def setup_file_logging(config: LoggingConfig) -> logging.Handler:
      """Setup file logging with date rollover"""
      
  def setup_newrelic_logging() -> Optional[logging.Handler]:
      """Setup New Relic log forwarding"""
  ```

#### 3.3 Updated Logging Setup
- **File**: `src/ollm/logging_setup.py`
  - Modify `setup_logging()` to include New Relic handler when enabled
  - Ensure all log levels are forwarded to New Relic
  - Maintain backward compatibility with existing log format options

### Phase 4: Custom Events Implementation (Priority 2)
**Estimated Time**: 6-8 hours

#### 4.1 Event Recording Framework
- **File**: `src/ollm/newrelic_integration.py`
  ```python
  class EventRecorder:
      def record_tool_call(self, tool_name: str, duration_ms: int, status: str, 
                          error_message: str = None, **kwargs):
          """Record tool call event"""
      
      def record_skill_usage(self, skill_name: str, duration_ms: int, status: str,
                            error_message: str = None, **kwargs):
          """Record skill usage event"""
      
      def record_script_execution(self, script_content: str, language: str,
                                 duration_ms: int, status: str, **kwargs):
          """Record script execution event"""
      
      def record_inference(self, ollama_response: Dict, **kwargs):
          """Record inference metrics event"""
      
      def record_error(self, error_type: str, error_message: str, 
                      error_source: str, **kwargs):
          """Record error event"""
  ```

#### 4.2 Tool Call Event Integration
- **Files**: `src/ollm/mcp/client.py`, `src/ollm/mcp/tool_adapter.py`
  - Add timing instrumentation around MCP tool calls
  - Capture success/failure status and error information
  - Integration points: Where tool calls are executed and results processed

#### 4.3 Skills Event Integration  
- **Files**: `src/ollm/skills/loader.py`, `src/ollm/skills/selector.py`
  - Add timing instrumentation around skill loading and execution
  - Capture skill name, execution duration, and status
  - Integration points: Skill discovery, loading, and execution phases

#### 4.4 Script Execution Event Integration
- **Files**: `src/ollm/script_execution/` (all relevant files)
  - Add timing instrumentation around script generation and execution
  - Capture script content (sanitized), language, duration, and status  
  - Integration points: Where LLM signals script execution and where execution completes

#### 4.5 Inference Event Integration
- **File**: `src/ollm/ollama_client.py`
  - Capture Ollama response metrics and timing
  - Map Ollama response fields to New Relic event schema
  - Integration point: Where Ollama responses are received and processed

### Phase 5: Error Handling & Event Integration (Priority 2)
**Estimated Time**: 3-4 hours

#### 5.1 Global Error Handler
- **File**: `src/ollm/newrelic_integration.py`
  ```python
  def setup_error_tracking():
      """Setup global exception handler for error events"""
      
  def handle_unhandled_exception(exc_type, exc_value, exc_traceback):
      """Global exception handler that records error events"""
  ```

#### 5.2 Application Error Integration
- **Files**: Multiple (error handling locations)
  - Add error event recording to existing exception handlers
  - Integrate with current error handling in `errors.py`
  - Capture error context, stack traces (sanitized), and severity levels

#### 5.3 Graceful Degradation
- **File**: `src/ollm/newrelic_integration.py`
  - Implement warning logging for New Relic initialization failures
  - Implement warning logging for individual event recording failures
  - Ensure core OLLM functionality continues if New Relic fails

### Phase 6: Configuration File Updates (Priority 3)
**Estimated Time**: 1-2 hours

#### 6.1 Update Example Configuration
- **Files**: `config.json.example`, `config.json` 
  ```json
  {
    "baseUrl": "http://localhost:11434",
    "logging": {
      "level": "info",
      "format": "jsonl",
      "maxFileSizeMB": 10,
      "maxFiles": 5,
      "log_filename": "/absolute/path/to/logfile.log"
    },
    "EnableNewRelic": true,
    "environment": "dev",
    // ... existing configuration
  }
  ```

#### 6.2 Update Deploy Script
- **File**: `deploy.sh`
  - Add sed command to update environment from "dev" to "PRD"
  - Target line: Update `"environment": "dev"` to `"environment": "PRD"`
  - Example: `sed -i 's/"environment": "dev"/"environment": "PRD"/g' config.json`

### Phase 7: Testing & Validation (Priority 3)
**Estimated Time**: 4-5 hours

#### 7.1 Test Harness Enhancement
- **Files**: Test files in `tests/` directory
  - Add New Relic integration tests
  - Test secret retrieval from Azure Key Vault
  - Test event recording functionality
  - Test error handling and graceful degradation

#### 7.2 Build Script Integration
- **File**: `build.sh`
  - Add optional switch for running test harness with New Relic validation
  - Test against real New Relic account using secrets from Key Vault
  - Validate that logs and events are delivered to New Relic

#### 7.3 Integration Validation
  - Manual testing of all event types
  - Verification via New Relic GraphQL API queries
  - Performance impact assessment

## Implementation Details

### Event Schema Mappings

#### Tool Call Event
```python
{
    "eventType": "ToolCall",
    "sessionId": session_manager.get_session_id(),
    "modelName": get_current_model(),
    "toolName": tool_name,
    "executionDurationMs": duration,
    "executionStatus": "success|failure",
    "errorMessage": sanitize_error_message(error) if error else None,
    "errorType": error_type,
    "httpStatusCode": status_code if applicable,
    "timestamp": datetime.utcnow().isoformat()
}
```

#### Skills Usage Event  
```python
{
    "eventType": "SkillUsage", 
    "sessionId": session_manager.get_session_id(),
    "modelName": get_current_model(),
    "skillName": skill_name,
    "executionDurationMs": duration,
    "executionStatus": "success|failure",
    "errorMessage": sanitize_error_message(error) if error else None,
    "errorType": error_type,
    "skillContext": context_info,
    "timestamp": datetime.utcnow().isoformat()
}
```

#### Script Execution Event
```python
{
    "eventType": "ScriptExecution",
    "sessionId": session_manager.get_session_id(), 
    "modelName": get_current_model(),
    "scriptLanguage": language,
    "scriptContent": sanitize_content(script_content)[:10240],  # 10KB limit
    "executionDurationMs": duration,
    "executionStatus": "success|failure", 
    "errorMessage": sanitize_error_message(error) if error else None,
    "exitCode": exit_code,
    "skillContext": skill_name if applicable,
    "timestamp": datetime.utcnow().isoformat()
}
```

#### Inference Event
```python
{
    "eventType": "Inference",
    "sessionId": session_manager.get_session_id(),
    "modelName": response.get("model"),
    "totalDurationNs": response.get("total_duration"),
    "loadDurationNs": response.get("load_duration"), 
    "promptEvalCount": response.get("prompt_eval_count"),
    "promptEvalDurationNs": response.get("prompt_eval_duration"),
    "evalCount": response.get("eval_count"),
    "evalDurationNs": response.get("eval_duration"),
    "doneStatus": response.get("done"),
    "doneReason": response.get("done_reason"),
    "createdAt": response.get("created_at"),
    "timestamp": datetime.utcnow().isoformat()
}
```

#### Error Event
```python
{
    "eventType": "Error",
    "sessionId": session_manager.get_session_id(),
    "modelName": get_current_model(),
    "errorType": error_type,
    "errorMessage": sanitize_error_message(str(error)),
    "errorSource": f"{module}.{function}",
    "stackTrace": sanitize_content(formatted_traceback)[:5000],  # 5KB limit
    "contextInfo": additional_context,
    "severity": severity_level,
    "timestamp": datetime.utcnow().isoformat()
}
```

### Integration Points

#### Application Initialization Flow
1. **Config Loading** (`app.py:initialize()`)
2. **Logging Setup** (`logging_setup.py:setup_logging()`)
3. **🔄 NEW: New Relic Initialization** (after logging, before MCP/skills)
4. **🔄 NEW: Session ID Generation** 
5. **MCP Client Setup** 
6. **Skills System Setup**
7. **Script Execution Setup**

#### Event Recording Integration Points

| Component | File | Integration Point | Event Type |
|-----------|------|------------------|------------|
| MCP Tools | `mcp/client.py` | Tool call execution wrapper | ToolCall |
| Skills | `skills/loader.py` | Skill execution wrapper | SkillUsage |  
| Scripts | `script_execution/` | Script execution wrapper | ScriptExecution |
| Ollama | `ollama_client.py` | Response processing | Inference |
| Global | Multiple | Exception handlers | Error |

### Security & Privacy Implementation

#### Content Sanitization Patterns
```python
SENSITIVE_PATTERNS = [
    (r'(?i)(api[_-]?key|password|token|secret)["\s]*[:=]["\s]*([^\s"]+)', r'\1: ***'),
    (r'(?i)(bearer|authorization)["\s]*[:=]["\s]*([^\s"]+)', r'\1: ***'),
    # Add more patterns as needed - framework for future extension
]

def sanitize_content(content: str) -> str:
    """Apply sanitization patterns to content."""
    for pattern, replacement in SENSITIVE_PATTERNS:
        content = re.sub(pattern, replacement, content)
    return content
```

#### Size Limits
- **Script Content**: 10KB limit (truncate with "... [TRUNCATED]")
- **Error Messages**: 1KB limit  
- **Stack Traces**: 5KB limit

### Error Handling Strategy

#### New Relic Initialization Failure
```python
try:
    newrelic_agent.initialize()
except Exception as e:
    logger.warning(f"New Relic initialization failed: {e}. Continuing without telemetry.")
    return False
```

#### Event Recording Failure  
```python
try:
    newrelic.agent.record_custom_event(event_type, event_data)
except Exception as e:
    logger.warning(f"Failed to record {event_type} event: {e}")
    # Continue execution - don't break core functionality
```

### Performance Considerations

#### Asynchronous Event Recording
- Use background threads for event recording to avoid blocking main execution
- Implement event queuing with size limits to prevent memory issues
- Graceful degradation if event queue is full

#### Timing Instrumentation
- Use high-precision timing (`time.perf_counter()`) for duration measurements
- Minimize overhead of timing instrumentation
- Record timing even if event recording fails

## File Modification Summary

### New Files
- `src/ollm/newrelic_integration.py` - Core New Relic integration

### Modified Files
- `pyproject.toml` - Add newrelic dependency, version update
- `src/ollm/__init__.py` - Version update to 1.3.0
- `src/ollm/config.py` - Add New Relic configuration fields
- `src/ollm/app.py` - New Relic initialization integration 
- `src/ollm/logging_setup.py` - Add New Relic log forwarding and date-based rollover
- `src/ollm/mcp/client.py` - Add tool call event recording
- `src/ollm/skills/loader.py` - Add skill usage event recording
- `src/ollm/script_execution/` - Add script execution event recording
- `src/ollm/ollama_client.py` - Add inference event recording
- `config.json.example` - Add new configuration fields
- `config.json` - Add new configuration fields  
- `deploy.sh` - Add environment update logic
- `build.sh` - Add test harness integration (optional)

## Testing Strategy

### Validation Approach
1. **Unit Tests**: Test individual event recording functions
2. **Integration Tests**: Test end-to-end event flow 
3. **Real Account Validation**: Use actual New Relic account for validation
4. **Performance Testing**: Ensure minimal impact on OLLM performance

### New Relic Validation Queries
```graphql
# Validate events are being received
{
  actor {
    account(id: NEW_RELIC_ACCOUNT_ID) {
      nrql(query: "SELECT count(*) FROM ToolCall WHERE sessionId = 'SESSION_ID' SINCE 1 hour ago") {
        results
      }
    }
  }
}
```

### Success Criteria
- [ ] All 5 event types successfully recorded in New Relic
- [ ] Logs successfully forwarded to New Relic  
- [ ] Session correlation works across all events
- [ ] Secrets successfully retrieved from Azure Key Vault
- [ ] Graceful degradation when New Relic is unavailable
- [ ] Performance impact < 5% on typical OLLM operations
- [ ] Date-based log rollover working correctly
- [ ] Environment updates correctly during deployment

## Risk Mitigation

### Potential Risks
1. **New Relic Agent Overhead** - Monitor performance impact
2. **Event Volume** - New Relic may have rate limits  
3. **Secret Availability** - Azure Key Vault may be inaccessible
4. **Content Sanitization Gaps** - May miss sensitive patterns

### Mitigation Strategies
1. **Performance Monitoring** - Add timing measurements around New Relic calls
2. **Rate Limiting** - Let New Relic agent handle rate limiting as specified
3. **Graceful Degradation** - Continue operation without New Relic when needed
4. **Extensible Sanitization** - Framework allows easy addition of new patterns

## Timeline

**Total Estimated Time**: 20-25 hours

- **Week 1 (Phases 1-2)**: Foundation & Core Integration (6-8 hours)
- **Week 2 (Phases 3-4)**: Logging & Events (9-12 hours) 
- **Week 3 (Phases 5-7)**: Error Handling, Config & Testing (5-7 hours)

## Success Metrics

### Immediate Success Criteria  
- ✅ OLLM builds and runs with New Relic integration
- ✅ All 5 event types appear in New Relic dashboard
- ✅ Logs successfully forwarded to New Relic
- ✅ Session IDs correlate events across single OLLM run
- ✅ Environment correctly updates during deployment

### Operational Success Criteria
- ✅ Zero impact on OLLM core functionality if New Relic fails
- ✅ Performance degradation < 5%
- ✅ Sensitive content properly sanitized
- ✅ Error events provide actionable troubleshooting information
- ✅ Deploy script successfully updates environment to PRD

This implementation plan provides a structured approach to implementing New Relic observability while maintaining OLLM's reliability and performance characteristics.