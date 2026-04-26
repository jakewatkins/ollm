# Queries for New Relic

Event Types Being Sent
Your OLLM application sends three types of telemetry events to New Relic as logs:

AIAgentInference - LLM inference events
AIAgentToolCall - Tool/MCP call events
AIAgentSkillUsage - Skill usage events
New Relic Query Examples
1. View All OLLM Events (Last Hour)
    SELECT * FROM Log 
    WHERE service.name = 'ollm' 
    SINCE 1 hour ago

2. AI Inference Events
    SELECT timestamp, model, prompt_tokens, response_tokens, end_to_end_duration_ms, session_id
    FROM Log 
    WHERE service.name = 'ollm' 
    AND message LIKE '%AIAgentInference%'
    SINCE 1 hour ago
    ORDER BY timestamp DESC

3. Tool Call Events
    SELECT timestamp, tool_name, success, duration_ms, session_id
    FROM Log 
    WHERE service.name = 'ollm' 
    AND message LIKE '%AIAgentToolCall%' 
    SINCE 1 hour ago
    ORDER BY timestamp DESC

4. Skill Usage Events
    SELECT timestamp, skill_name, success, duration_ms, session_id
    FROM Log 
    WHERE service.name = 'ollm' 
    AND message LIKE '%AIAgentSkillUsage%'
    SINCE 1 hour ago
    ORDER BY timestamp DESC

5. Performance Analysis
    SELECT average(end_to_end_duration_ms) as avg_inference_time,
        count(*) as total_inferences,
        model
    FROM Log 
    WHERE service.name = 'ollm' 
    AND message LIKE '%AIAgentInference%'
    SINCE 1 day ago
    FACET model

6. Error Analysis
    SELECT timestamp, tool_name, error_message, session_id
    FROM Log 
    WHERE service.name = 'ollm' 
    AND success = false
    AND message LIKE '%AIAgentToolCall%'
    SINCE 1 day ago
    ORDER BY timestamp DESC

7. Session Analysis
    SELECT session_id, count(*) as event_count, 
        sum(CASE WHEN message LIKE '%AIAgentInference%' THEN 1 ELSE 0 END) as inferences,
        sum(CASE WHEN message LIKE '%AIAgentToolCall%' THEN 1 ELSE 0 END) as tool_calls,
        sum(CASE WHEN message LIKE '%AIAgentSkillUsage%' THEN 1 ELSE 0 END) as skill_usage
    FROM Log 
    WHERE service.name = 'ollm'
    SINCE 1 day ago
    FACET session_id
    ORDER BY event_count DESC

