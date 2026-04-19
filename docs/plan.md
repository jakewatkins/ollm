# ollm Implementation Plan

## 1. Objective

Implement a Python CLI tool that wraps Ollama HTTP chat, integrates MCP servers from mcp.json, auto-selects one best-matching skill from skills, provides sandboxed script execution capabilities, and executes a bounded tool-calling loop with safe logging and configuration defaults.

## 2. Delivery Strategy

Use phased delivery so we get a working CLI early, then add MCP, skills, and hardening in layers.

- Phase 1: Project scaffold and CLI shell
- Phase 2: Config, install-dir resolution, and logging
- Phase 3: Ollama client and core prompt flow
- Phase 4: MCP client integration and tool loop
- Phase 5: Skills discovery, scoring, and top-1 selection
- Phase 6: Integration hardening, packaging, and docs
- Phase 7: Test completion and release readiness

## 3. Proposed Project Layout

```text
ollm/
  pyproject.toml
  README.md
  requirements.md
  plan.md
  config.json.example
  mcp.json.example
  skills/
  src/
    ollm/
      __init__.py
      __main__.py
      cli.py
      app.py
      paths.py
      config.py
      logging_setup.py
      model_selection.py
      ollama_client.py
      mcp/
        __init__.py
        config_schema.py
        client.py
        server_runtime.py
        tool_adapter.py
      skills/
        __init__.py
        schema.py
        loader.py
        selector.py
        context_builder.py
      script_execution/
        __init__.py
        docker_client.py
        executor.py
        container_manager.py
        script_tool.py
      loop/
        __init__.py
        agent_loop.py
        timeouts.py
      output.py
      errors.py
  tests/
    unit/
    integration/
    fixtures/
```

## 4. Phase Plan

## Phase 1: Scaffold and CLI shell

Goal: executable ollm command with argument parsing and no MCP/skills yet.

Tasks:
- Create pyproject with console entry point ollm.
- Implement argument parsing:
  - prompt source: -p or -pf (mutually exclusive)
  - optional -o
  - optional -m
  - stdin fallback when prompt flags are absent
- Implement prompt loading:
  - -p uses argument text
  - -pf reads full file
  - stdin reads until EOF
- Implement output handling:
  - writes to file when -o is set
  - otherwise writes to stdout

Done criteria:
- ollm runs and prints placeholder output from parsed prompt.
- Invalid prompt flag combinations fail with clear message.

## Phase 2: Config, install-dir, and logging

Goal: reliable runtime environment and observable behavior.

Tasks:
- Implement install directory resolver:
  - OLLM_HOME first
  - else parent directory of running executable
  - fail if outside user home
- Implement config loader for config.json with defaults and validation.
- Implement API key precedence:
  - OLLM_OLLAMA_API_KEY if non-empty
  - else config apiKey if non-empty
  - else unauthenticated
- Implement log setup:
  - logs directory under install root
  - level/format from config
  - rotation defaults: 10 MB, 5 files
  - redact secret fields

Done criteria:
- startup resolves install root and loads config reliably.
- logs are written and rotated.

## Phase 3: Ollama core client

Goal: complete non-tool chat flow to Ollama endpoint.

Tasks:
- Implement Ollama HTTP client:
  - list models
  - chat request/response
- Implement model choice:
  - use -m when provided
  - otherwise list models and select lexical-first model
  - fail clearly when no models exist
- Implement request timeout handling (requestTimeoutSeconds).

Done criteria:
- prompt sends successfully to Ollama and returns model output.
- authentication and timeout failures produce clear errors.

## Phase 4: MCP integration and tool loop

Goal: enable tool-calling loop through MCP servers.

Tasks:
- Parse mcp.json (optional; missing means no tools).
- Start/connect configured MCP servers.
- Discover MCP tools and adapt to Ollama tools format.
- Implement agent loop with limits:
  - maxTurns
  - toolCallTimeoutSeconds
  - requestTimeoutSeconds
- On tool failures/timeouts, return tool error result back to model instead of crashing.

Done criteria:
- tool-capable model can request MCP tools and receive results.
- loop exits safely on no tool calls, max turns, or request timeout.

## Phase 5: Skills discovery, selection, and script execution

Goal: automatic single-skill selection with deterministic scoring and sandboxed script execution capabilities.

Tasks:
- Load skills from skills/<name>/SKILL.md.
- Parse frontmatter and markdown body.
- Validate required fields: name, description.
- Implement scoring:
  - exact phrase 0.50
  - token overlap 0.35
  - fuzzy token similarity 0.15
  - normalize to 0..1
  - threshold minScore
  - tie-break by lexical skill name
- Enforce topK = 1 for v1.
- Check requiredMcpServers availability before applying selected skill.
- Load skill resources with limits:
  - maxFileSizeKB
  - maxTotalSizeKB
  - oversize skill is skipped and logged
- Inject selected skill body and resources as hidden/system context in chat request.
- Implement `execute_script` built-in tool:
  - Docker container execution
  - Support for python3, bash, shell languages
  - Capture stdout, stderr, exit code
  - Security isolation (no network by default, resource limits)
  - Configurable timeouts and container image
- Skills can opt-in to script execution via `scriptExecution: true` frontmatter.
- Build or pull `ollm-runner` Docker image with common tools.

Done criteria:
- one best skill is selected or none selected.
- selected skill affects context and tool usage behavior.
- skills with scriptExecution: true expose execute_script tool.
- script execution works in isolated Docker containers.

## Phase 6: Hardening, packaging, and docs

Goal: production-ready packaging and operator documentation.

Tasks:
- Add robust error taxonomy and user-friendly messages.
- Ensure all secrets are redacted in logs and errors.
- Add README sections:
  - install
  - config
  - mcp.json
  - skills
  - examples
  - troubleshooting
- Add mcp.json.example matching requirements.
- Verify install behavior under home subdirectory deployment.

Done criteria:
- package install yields runnable ollm command.
- deployment under ~/apps/ollm works end-to-end.

## Phase 7: Test completion and release readiness

Goal: confidence for first usable release.

Tasks:
- Unit tests:
  - config defaults/fallback
  - install-dir resolution
  - model selection behavior
  - skill parsing/scoring/tie-break
  - resource limits
  - secret redaction
- Integration tests:
  - no mcp.json and no skills
  - one reachable MCP server
  - tool loop success path
  - tool timeout path
  - max turns path
  - stdout and file output paths
- Manual smoke tests in local install directory.

Done criteria:
- acceptance scenarios in requirements pass.
- known limitations documented.

## 5. Cross-Cutting Design Decisions

- Keep modules small and pure where possible, especially config validation, skill scoring, and prompt construction.
- Use strict schemas for config and SKILL frontmatter validation.
- Keep MCP runtime isolated from prompt/skills logic so it can be tested independently.
- Make selection and loop behavior deterministic for easier debugging.

## 6. Suggested Execution Order

1. Phase 1 + Phase 2
2. Phase 3
3. Phase 4
4. Phase 5
5. Phase 6 + Phase 7

This order gives a working non-tool CLI first, then progressively adds MCP and skills.

## 7. Risks and Mitigations

- MCP server startup variance across environments
  - Mitigation: defensive startup errors, retries where safe, detailed logs.
- Prompt/context growth from skills
  - Mitigation: enforce resource limits and skip oversize skills.
- Timeout tuning may be workload-specific
  - Mitigation: keep timeouts configurable with safe defaults.
- Docker availability and container security
  - Mitigation: graceful fallback when Docker unavailable, strict container isolation.
- Script execution security risks
  - Mitigation: no network by default, resource limits, fresh containers only.
- Packaging path assumptions
  - Mitigation: centralize install-dir resolution and test under real deployment path.

## 8. Definition of Ready to Start Coding

- Requirements are frozen for v1 behavior (especially top-1 selection).
- config.json.example and SKILL template are present.
- This plan is accepted as implementation order.

## 9. Definition of Done for v1

- CLI works for -p, -pf, and stdin.
- Config defaults and precedence rules are enforced.
- Ollama chat works with model fallback behavior.
- MCP tools execute in bounded loop with timeout handling.
- Skills auto-select top-1 deterministically and inject context.
- Logging is rotated and secret-safe.
- Unit and integration tests cover defined acceptance scenarios.
- Package installs and runs from home subdirectory deployment.
