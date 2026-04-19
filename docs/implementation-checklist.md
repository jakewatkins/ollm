# ollm Implementation Checklist

**Status: 7/7 Milestones Complete ✅ - Ready for v1 Release!**

Use this as the execution board for v1. Each phase can be tracked as one issue or milestone.

## Milestone 1: CLI Foundation ✅ COMPLETE

### Issue 1.1: Project scaffold and entrypoint
- [x] Create pyproject packaging with Python 3.11+ target.
- [x] Add console entry point named ollm.
- [x] Add initial src package structure under src/ollm.
- [x] Add basic README with quick run command.

Acceptance:
- [x] Running ollm --help works from local environment.

### Issue 1.2: CLI arguments and prompt input
- [x] Implement -p and -pf as mutually exclusive.
- [x] Implement optional -o and -m.
- [x] Implement stdin fallback when -p and -pf are absent.
- [x] Read stdin until EOF.
- [x] Add clear error for invalid argument combinations.

Acceptance:
- [x] -p path works.
- [x] -pf path works.
- [x] stdin pipeline works.
- [x] invalid flag combinations fail with non-zero exit.

### Issue 1.3: Output behavior
- [x] Write final response to stdout when -o is not provided.
- [x] Write final response to file when -o is provided.
- [x] Handle output file write failures with clear errors.

Acceptance:
- [x] stdout path verified.
- [x] file output path verified.

## Milestone 2: Runtime Environment ✅ COMPLETE

### Issue 2.1: Install directory resolution
- [x] Implement install directory precedence:
- [x] OLLM_HOME when set.
- [x] Else parent directory of running executable.
- [x] Validate install directory is under user home.
- [x] Fail with clear error when invalid.

Acceptance:
- [x] install root resolves deterministically.
- [x] invalid root outside home fails.

### Issue 2.2: config.json loading and validation
- [x] Load config.json from install directory.
- [x] Validate required baseUrl.
- [x] Apply defaults for missing optional values.
- [x] For invalid optional values, warn and use defaults.

Acceptance:
- [x] missing/invalid baseUrl fails clearly.
- [x] optional values fall back to defaults.

### Issue 2.3: API key precedence
- [x] Implement precedence:
- [x] OLLM_OLLAMA_API_KEY if non-empty.
- [x] Else config.json apiKey if non-empty.
- [x] Else unauthenticated requests.
- [x] Redact key values from logs and errors.

Acceptance:
- [x] precedence works in tests.
- [x] no secret leakage in logs.

### Issue 2.4: logging setup
- [x] Create logs directory under install directory.
- [x] Support level and format config.
- [x] Implement rotation defaults: 10 MB, 5 files.
- [x] Use stable log naming pattern.

Acceptance:
- [x] logs created on startup.
- [x] rotation works under forced rollover test.

## Milestone 3: Ollama Core ✅ COMPLETE

### Issue 3.1: Ollama HTTP client
- [x] Implement list models call.
- [x] Implement chat call.
- [x] Support optional auth header.
- [x] Support request timeout from config.

Acceptance:
- [x] successful chat without tools.
- [x] 401/403 handled with clear error.
- [x] timeout handled with clear error.

### Issue 3.2: model selection behavior
- [x] Use -m model when provided.
- [x] Otherwise list models and select lexical-first by name.
- [x] Fail clearly when model list is empty.

Acceptance:
- [x] deterministic default model selection verified.

## Milestone 4: MCP and Tool Loop ✅ COMPLETE

### Issue 4.1: MCP config and server startup
- [x] Load mcp.json when present.
- [x] Continue without tools when mcp.json is absent.
- [x] Start/connect configured MCP servers.
- [x] Discover tools from loaded servers.

Acceptance:
- [x] no-mcp mode works.
- [x] one-server mode discovers tools.

### Issue 4.2: MCP tool adapter to Ollama
- [x] Convert discovered MCP tools to Ollama tool definitions.
- [x] Keep mapping from Ollama tool name to MCP tool call target.

Acceptance:
- [x] mapped tool calls execute correctly.

### Issue 4.3: bounded agent loop
- [x] Implement maxTurns guard.
- [x] Implement per-tool timeout guard.
- [x] Implement per-request timeout guard.
- [x] Return tool errors/timeouts back as tool results.

Acceptance:
- [x] success path completes.
- [x] maxTurns path exits cleanly.
- [x] tool timeout path exits cleanly.

## Milestone 5: Skills and Script Execution ✅ COMPLETE

### Issue 5.1: skill discovery and parsing
- [x] Scan skills/<name>/SKILL.md.
- [x] Parse frontmatter and markdown body.
- [x] Enforce required fields name and description.
- [x] Parse scriptExecution boolean flag.
- [x] Skip malformed skills with warnings.

Acceptance:
- [x] valid skills load.
- [x] malformed skills are skipped and logged.
- [x] scriptExecution flag is parsed correctly.

### Issue 5.2: deterministic scoring and selection
- [x] Implement lexical scoring:
- [x] phrase score weight 0.50
- [x] token overlap weight 0.35
- [x] fuzzy token similarity weight 0.15
- [x] normalize score 0..1
- [x] apply minScore threshold
- [x] apply lexical tie-break by skill name
- [x] enforce topK = 1 for v1

Acceptance:
- [x] top-1 only behavior verified.
- [x] tie-break behavior verified.

### Issue 5.3: skill runtime context and resource limits
- [x] Verify requiredMcpServers before applying selected skill.
- [x] Load declared resources within maxFileSizeKB.
- [x] Enforce maxTotalSizeKB across resources.
- [x] If resource limits exceeded, skip skill and log warning.
- [x] Inject skill body and resources as hidden/system context.

Acceptance:
- [x] selected skill changes request context.
- [x] oversize skill is skipped with warning.

### Issue 5.4: script execution infrastructure
- [x] Implement Docker client wrapper.
- [x] Build or configure ollm-runner container image.
- [x] Implement execute_script tool with parameters:
  - [x] script (content)
  - [x] language (python3, bash, shell)
  - [x] timeout (default 30s, max 300s)
  - [x] workdir (default /workspace)
  - [x] network (default false)
- [x] Capture stdout, stderr, exit code.
- [x] Apply security restrictions:
  - [x] no network by default
  - [x] resource limits (512M memory, 1 CPU)
  - [x] fresh containers only
  - [x] non-root execution user

Acceptance:
- [x] execute_script tool executes safely in containers.
- [x] Docker unavailable gracefully disables script execution.
- [x] security restrictions are enforced.

### Issue 5.5: script execution integration
- [x] Only expose execute_script when skill has scriptExecution: true.
- [x] Add execute_script to tool list alongside MCP tools.
- [x] Configure script execution settings via config.json.
- [x] Log script executions (duration, exit code, not content).
- [x] Handle container failures gracefully.

Acceptance:
- [x] skills without scriptExecution don't see execute_script.
- [x] skills with scriptExecution can use execute_script tool.
- [x] script execution is properly configured and logged.

## Milestone 6: Packaging and Documentation ✅ COMPLETE

### Issue 6.1: deployment readiness
- [x] Confirm install under user home subdirectory.
- [x] Ensure runtime paths (config, mcp, skills, logs) are relative to install root.
- [x] Validate startup behavior in deployed layout.

Acceptance:
- [x] end-to-end run from ~/apps/ollm passes.

### Issue 6.2: docs and examples
- [x] Document install and run paths in README.
- [x] Document config.json and defaults.
- [x] Document mcp.json behavior and examples.
- [x] Document skill format and examples.
- [x] Document troubleshooting and logs.

Acceptance:
- [x] a new user can run first prompt from docs only.

## Milestone 7: Test Completion and Release Gate ✅ COMPLETE

### Issue 7.1: unit test suite
- [x] Config defaults and invalid-value fallback.
- [x] Install dir resolution.
- [x] API key precedence.
- [x] Model selection logic.
- [x] Skill parsing and scoring.
- [x] Resource limit enforcement.
- [x] Secret redaction.

Acceptance:
- [x] unit tests pass in CI/local.

### Issue 7.2: integration test suite
- [x] no mcp.json and no skills.
- [x] mcp.json with one reachable server.
- [x] tool loop success path.
- [x] tool timeout path.
- [x] maxTurns path.
- [x] stdout and file output paths.

Acceptance:
- [x] integration tests pass in CI/local.

### Issue 7.3: Manual smoke tests
- [x] Install under ~/apps/ollm.
- [x] Run with -p.
- [x] Run with -pf.
- [x] Run with stdin pipe.
- [x] Verify logs and rotation.
- [x] Verify top-1 skill selection appears in debug logs.
- [x] Manual test plan documented in tests/manual_test_plan.md

Acceptance:
- [x] smoke checklist fully complete.

## Release Checklist
- [x] All milestone acceptance boxes complete. (7/7 milestones complete ✅)
- [x] No open high-severity bugs.
- [x] requirements.md and implementation behavior match.
- [x] Comprehensive test suite implemented with unit, integration, and manual tests.
- [ ] Tag and package v1 release.
