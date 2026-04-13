# ollm Implementation Checklist

Use this as the execution board for v1. Each phase can be tracked as one issue or milestone.

## Milestone 1: CLI Foundation

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

## Milestone 2: Runtime Environment

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

## Milestone 5: Skills Top-1 Selection

### Issue 5.1: skill discovery and parsing
- [ ] Scan skills/<name>/SKILL.md.
- [ ] Parse frontmatter and markdown body.
- [ ] Enforce required fields name and description.
- [ ] Skip malformed skills with warnings.

Acceptance:
- [ ] valid skills load.
- [ ] malformed skills are skipped and logged.

### Issue 5.2: deterministic scoring and selection
- [ ] Implement lexical scoring:
- [ ] phrase score weight 0.50
- [ ] token overlap weight 0.35
- [ ] fuzzy token similarity weight 0.15
- [ ] normalize score 0..1
- [ ] apply minScore threshold
- [ ] apply lexical tie-break by skill name
- [ ] enforce topK = 1 for v1

Acceptance:
- [ ] top-1 only behavior verified.
- [ ] tie-break behavior verified.

### Issue 5.3: skill runtime context and resource limits
- [ ] Verify requiredMcpServers before applying selected skill.
- [ ] Load declared resources within maxFileSizeKB.
- [ ] Enforce maxTotalSizeKB across resources.
- [ ] If resource limits exceeded, skip skill and log warning.
- [ ] Inject skill body and resources as hidden/system context.

Acceptance:
- [ ] selected skill changes request context.
- [ ] oversize skill is skipped with warning.

## Milestone 6: Packaging and Documentation

### Issue 6.1: deployment readiness
- [ ] Confirm install under user home subdirectory.
- [ ] Ensure runtime paths (config, mcp, skills, logs) are relative to install root.
- [ ] Validate startup behavior in deployed layout.

Acceptance:
- [ ] end-to-end run from ~/apps/ollm passes.

### Issue 6.2: docs and examples
- [ ] Document install and run paths in README.
- [ ] Document config.json and defaults.
- [ ] Document mcp.json behavior and examples.
- [ ] Document skill format and examples.
- [ ] Document troubleshooting and logs.

Acceptance:
- [ ] a new user can run first prompt from docs only.

## Milestone 7: Test Completion and Release Gate

### Issue 7.1: unit test suite
- [ ] Config defaults and invalid-value fallback.
- [ ] Install dir resolution.
- [ ] API key precedence.
- [ ] Model selection logic.
- [ ] Skill parsing and scoring.
- [ ] Resource limit enforcement.
- [ ] Secret redaction.

Acceptance:
- [ ] unit tests pass in CI/local.

### Issue 7.2: integration test suite
- [ ] no mcp.json and no skills.
- [ ] mcp.json with one reachable server.
- [ ] tool loop success path.
- [ ] tool timeout path.
- [ ] maxTurns path.
- [ ] stdout and file output paths.

Acceptance:
- [ ] integration tests pass in CI/local.

### Issue 7.3: manual smoke tests
- [ ] Install under ~/apps/ollm.
- [ ] Run with -p.
- [ ] Run with -pf.
- [ ] Run with stdin pipe.
- [ ] Verify logs and rotation.
- [ ] Verify top-1 skill selection appears in debug logs.

Acceptance:
- [ ] smoke checklist fully complete.

## Release Checklist
- [ ] All milestone acceptance boxes complete.
- [ ] No open high-severity bugs.
- [ ] requirements.md and implementation behavior match.
- [ ] Tag and package v1 release.
