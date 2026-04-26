# Telemetry Requirements.md

When Ollama sends its responses to Ollm, I want Ollm to push the telemetry to  New Relic's OpenTelemetry API so I can track activity.  Additionally, I'd like ollm to push its own telemetry data including:
- prompt size
- tool calls
- skill usage
- response size
- end to end timing

Ollama provides the following fields in its responses:
{
  "model": "gemma3",
  "created_at": "2025-10-17T23:14:07.414671Z",
  "response": "Hello! How can I help you today?",
  "done": true,
  "done_reason": "stop",
  "total_duration": 174560334,
  "load_duration": 101397084,
  "prompt_eval_count": 11,
  "prompt_eval_duration": 13074791,
  "eval_count": 18,
  "eval_duration": 52479709
}
we want the following:
- total_duration
- load_duration
- prompt_eval_count
- prompt_eval_duration
- eval_count
- eval_duration
to be sent to New Relic

Ollm will get the New Relic API key from the Azure Key Vault (name of the key vault is in config.json as keyvault).  The secret name is NewRelicAPIKey.  The New Relic Account id will be in the secret namec NewRelicAccountId

- Use https://otlp.nr-data.net/v1/logs for custom events
- use port 443 for standard HTTPS
- Use custom events to track everything
- we want to use "logs-as-events" so we can produce dashboards showing total token usage and look at individual inference sessions
- We'll create 3 types of custom events in New Relic by setting newrelic.event.typ to the following:
    - AIAgentInference for main Ollama inference data
    - AIAgentToolCall for tool call events
    - AIAgentSkillUsage for skill usage events
- We'll want to create a request id for each ollm session so all 3 event types can be correlated.
    - Use a UUID4
    - Generate per user session so it will potentially go across prompts.
        - OLLM is a cli tool that will usually just have 1 prompt, but as we grow it and it becomes more agentic it will potentially begin creating sub-prompts to help it complete a larger prompt.
- Each tool or skill use should be a separate event
- attach the API Key as api-key in the HTTP headers.
- Measure prompt size and response size in tokens
- Use OLLM as the service identification and append the hostname of the machine.  
    - for example OLLM running on skyline should set service.name to "OLLM - skyline"
- end-to-end timing should be from initial user request until final response
- Use custom events for tool calls and skill usage
- include tool and skill names
- track success and failure
    - success or failure from a tool will be determined by the following:
        - return code/response
        - absense of an exception
- do not include tool call parameters - potential PHI or PII date would be revealed.
- Missing Ollama data - send null values for missing data.
- If calls to new relic fail - log the error in the local log and continue
- do not worry about retry logic at this time.
- timeout handling: make it configurable ("NewRelicTimeOut" in config.json) and use a 3 second default if the config value is missing
- configuration: just provide an enable/disable toggle for now
    - add "SendTelemetry" to config.json.  True means it is enabled, false means turn it off.
- data sensitivity - don't send actual prompt or response content to New Relic.
- use asynchronous methods to send telemetry to New Relic
    - for simplicity just send events individually as they occur
- token counting:
    - use Ollama's token counts when available.
    - fall back to tiktoken when necessary.  Use gpt-4 to count tokens

    