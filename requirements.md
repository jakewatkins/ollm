# ollm

I want to create a command line tool that wraps Ollama's http endpoint.  I'd like the tool to provide mcp servers and skills to Ollama so that it can perform work beyond infrencing.

Usage of the tool will look like:
ollm [-p "promt goes here" | -pf prompt-file-path] [-o output-file-path] [-m model-name]
-p is for a prompt on the command line
-pf the tool will get the prompt from the file's contents
-o the file where the final response will be written
-m is the name of the model hosted by ollama

if -o isnt providednthe tool will write the final response to stdout so the output can be redirected.

`-p` and `-pf` are mutually exclusive. if both are provided print an error message and exit.

if -p and -pf are missing read stdin until eof is reached. the idea is that the user could redirect a file to ollm like this:
cat my-prompt.txt | ollm > output.txt

if -m is not provided, ollm will get the list of models from ollama and choose the first model by ascending lexical sort of model name. if there are no models, print an error and exit.

the tool will use the mcp.json file in the directory where ollm is installed.
if mcp.json is missing run without tools.

install directory requirements:
- ollm must be installed in the user's home directory or a subdirectory of the user's home directory.
- valid examples include `~/ollm` and `~/apps/ollm`.
- on startup, ollm will resolve its install directory and fail with a clear error if the resolved path is outside the user's home directory.
- ollm will read `config.json`, `mcp.json`, and `skills/` from this install directory.
- ollm will write `logs/` under this install directory.
- install directory resolution order:
	1. use `OLLM_HOME` if set.
	2. otherwise use the parent directory of the running `ollm` executable.
	3. if neither resolves to a valid path under the user's home directory, fail with a clear error.

ollm will act as an MCP client.

MCP client requirements:
- ollm will read mcp.json at startup and use it to determine which MCP servers are available.
- ollm will start local MCP servers or connect to configured MCP servers as defined in mcp.json.
- ollm will discover the tools exposed by those MCP servers.
- ollm will translate discovered MCP tools into the tool definitions sent to Ollama's HTTP chat endpoint.
- when Ollama returns tool calls, ollm will map each requested tool call back to the matching MCP tool and execute it through the MCP server.
- ollm will send each MCP tool result back to Ollama in the follow-up chat messages so Ollama can continue the conversation.
- ollm will continue this request and tool-execution loop until Ollama returns a final response with no further tool calls.
- if an MCP server is unavailable, fails to start, or a tool call fails, ollm will capture the error and return that failure to Ollama as the tool result instead of crashing.
- ollm will only expose tools from MCP servers that were successfully loaded from mcp.json.

mcp.json schema:
- ollm will use the same top-level mcp.json structure that VS Code uses.
- the file will contain a `servers` object that maps server names to server configuration objects.
- the file may contain an optional `inputs` array for sensitive values that can be referenced from server configuration.

top-level structure:

```json
{
	"servers": {
		"serverName": {
			"type": "stdio",
			"command": "npx",
			"args": ["-y", "@example/mcp-server"]
		}
	},
	"inputs": [
		{
			"type": "promptString",
			"id": "api-key",
			"description": "API key",
			"password": true
		}
	]
}
```

server schema:
- each key under `servers` is the MCP server name.
- server names should be unique and stable.
- ollm will support the same server types VS Code supports in mcp.json: `stdio`, `http`, and `sse`.

stdio server fields:
- `type`: required, must be `stdio`.
- `command`: required, the executable to start.
- `args`: optional array of command-line arguments.
- `env`: optional object of environment variables.
- `envFile`: optional path to an environment file.
- `sandboxEnabled`: optional boolean.
- `sandbox`: optional object with sandbox rules.
- `dev`: optional object for development settings.

http or sse server fields:
- `type`: required, must be `http` or `sse`.
- `url`: required, the MCP server endpoint.
- `headers`: optional object of HTTP headers.
- `dev`: optional object for development settings.

input schema:
- `type`: required, must be `promptString`.
- `id`: required unique identifier used by `${input:name}` references.
- `description`: required prompt text shown to the user.
- `password`: optional boolean to hide entered values.

sandbox schema:
- `filesystem.allowWrite`: optional array of writable paths.
- `filesystem.denyRead`: optional array of paths that cannot be read.
- `filesystem.denyWrite`: optional array of paths that cannot be written.
- `network.allowedDomains`: optional array of allowed domains.
- `network.deniedDomains`: optional array of denied domains.

development schema:
- `dev.watch`: optional file glob used to restart the server when files change.
- `dev.debug`: optional debug configuration.

variable handling:
- ollm does not need to support VS Code workspace or editor variables.
- ollm should support `${input:name}` references in mcp.json.
- if `inputs` are present, ollm should prompt for missing values at runtime and substitute them before starting or connecting to the server.

example mcp.json:

```json
{
	"servers": {
		"github": {
			"type": "http",
			"url": "https://api.githubcopilot.com/mcp",
			"headers": {
				"Authorization": "Bearer ${input:github-token}"
			}
		},
		"playwright": {
			"type": "stdio",
			"command": "npx",
			"args": ["-y", "@microsoft/mcp-server-playwright"],
			"sandboxEnabled": true,
			"sandbox": {
				"network": {
					"allowedDomains": ["*.example.com"]
				}
			}
		}
	},
	"inputs": [
		{
			"type": "promptString",
			"id": "github-token",
			"description": "GitHub token",
			"password": true
		}
	]
}
```

logging requirements:
- ollm will write log files to a `logs` directory in the directory where ollm is installed.
- ollm will create the `logs` directory if it does not already exist.
- ollm will write application logs for startup, configuration loading, MCP server startup and connection, tool discovery, tool execution, Ollama requests, Ollama responses, and error conditions.
- ollm will avoid writing secrets such as API keys, bearer tokens, or prompt input variable values to logs.
- ollm should log enough request and response metadata to troubleshoot failures without exposing sensitive values.

configuration requirements:
- ollm will read `config.json` from the directory where ollm is installed.
- `config.json` will contain the base URL for the Ollama server.
- `config.json` may contain an optional API key for Ollama.
- if the API key is present, ollm will send it in requests to the configured Ollama endpoint.
- if `config.json` is missing, unreadable, or invalid, ollm will fail with a clear error message.

config.json schema:

```json
{
	"baseUrl": "http://localhost:11434",
	"apiKey": "optional-api-key",
	"agentLoop": {
		"maxTurns": 8,
		"toolCallTimeoutSeconds": 60,
		"requestTimeoutSeconds": 300
	},
	"logging": {
		"level": "info",
		"format": "jsonl",
		"maxFileSizeMB": 10,
		"maxFiles": 5
	},
	"skills": {
		"selection": {
			"topK": 1,
			"minScore": 0.35,
			"fuzzyMatch": true
		},
		"resources": {
			"maxFileSizeKB": 64,
			"maxTotalSizeKB": 256
		}
	}
}
```

config.json field definitions:
- `baseUrl`: required string. The base URL of the Ollama server.
- `apiKey`: optional string. The API key used when the Ollama endpoint requires authentication.
- `agentLoop.maxTurns`: optional integer. Maximum assistant/tool loop turns per request. Default is `8`.
- `agentLoop.toolCallTimeoutSeconds`: optional integer. Timeout for one MCP tool call. Default is `60`.
- `agentLoop.requestTimeoutSeconds`: optional integer. Overall timeout for one ollm request. Default is `300`.
- `logging.level`: optional string. Log level. Allowed values: `debug`, `info`, `warn`, `error`. Default is `info`.
- `logging.format`: optional string. Allowed values: `jsonl`, `text`. Default is `jsonl`.
- `logging.maxFileSizeMB`: optional integer. Max size of one log file before rotation. Default is `10`.
- `logging.maxFiles`: optional integer. Number of rotated log files to keep. Default is `5`.
- `skills.selection.topK`: optional integer. Number of skills selected per request. In v1 this must be `1`.
- `skills.selection.minScore`: optional number from `0` to `1`. Minimum score required to select a skill. Default is `0.35`.
- `skills.selection.fuzzyMatch`: optional boolean. Enables fuzzy token matching in scoring. Default is `true`.
- `skills.resources.maxFileSizeKB`: optional integer. Maximum size for a single skill resource file. Default is `64`.
- `skills.resources.maxTotalSizeKB`: optional integer. Maximum combined size of loaded resource files per skill. Default is `256`.

defaults behavior:
- if any optional configuration value is missing, ollm will use the documented default.
- if a configuration value is present but invalid, ollm will log a warning and use the default value.
- if `baseUrl` is missing or invalid, ollm will fail with a clear error message.

mcp/ollama agent loop requirements:
- loop and timeout controls will be configured through `config.json` under `agentLoop`.
- ollm will stop the loop when no more tool calls are returned, when `maxTurns` is reached, or when `requestTimeoutSeconds` is exceeded.
- if `maxTurns` is reached, ollm will end processing and return a clear error message.
- if a tool call exceeds `toolCallTimeoutSeconds`, ollm will treat that tool call as failed and return the failure to Ollama as a tool result.
- if loop settings are not configured, ollm will use defaults from this document.

### Ollama API Key Authentication

Some Ollama deployments require an API key.

- Config field: apiKey (optional)
- Recommended source: environment variable OLLM_OLLAMA_API_KEY
- Fallback source: config.json apiKey

API key precedence:
- use `OLLM_OLLAMA_API_KEY` when it is set and not empty.
- otherwise use `config.json` field `apiKey` when set and not empty.
- otherwise send unauthenticated requests.

Client behavior:
- When apiKey is set, the client includes the authentication header expected by the Ollama deployment (commonly Authorization: Bearer <apiKey>).
- When apiKey is not set, the client sends requests without authentication.

Failure behavior:
- If authentication fails (HTTP 401 or 403), the client exits with:
  "Authentication to Ollama failed. Check your API key and endpoint configuration."

Security notes:
- Do not commit API keys to source control.
- Do not store plaintext keys in shared config files.
- Do not log or echo keys in terminal output.

skills requirements:
- ollm will support skills as reusable workflow packages that guide how Ollama should use available MCP tools and context.
- skills are not sent to Ollama as a separate API field.
- ollm will expose skills to Ollama by converting selected skill content into prompt context and by exposing the MCP tools needed by the skill.
- ollm will look for skills in a `skills` directory in the directory where ollm is installed.
- each skill will live in its own subdirectory under `skills`.
- each skill directory must contain a `SKILL.md` file.
- a skill directory may also contain supporting Markdown files, templates, or other read-only assets referenced by `SKILL.md`.

skills discovery requirements:
- ollm will scan the `skills` directory at startup or before processing a request.
- ollm will treat each `skills/<skill-name>/SKILL.md` file as one skill definition.
- ollm will parse each `SKILL.md` file into frontmatter metadata and Markdown body content.
- ollm will ignore skill directories that do not contain a valid `SKILL.md` file.
- if a skill cannot be parsed, ollm will log the error and continue loading other skills.

SKILL.md requirements:
- ollm will use a VS Code style skill layout based on a `SKILL.md` file with YAML frontmatter followed by Markdown instructions.
- the frontmatter will provide metadata used for discovery and selection.
- the Markdown body will contain the workflow instructions that ollm injects into the request sent to Ollama.

required SKILL.md frontmatter fields:
- `name`: required string. The skill name.
- `description`: required string. A concise description of when the skill should be used.

optional SKILL.md frontmatter fields:
- `requiredMcpServers`: optional array of MCP server names that should be available before the skill is used.
- `preferredTools`: optional array of MCP tool names that the skill expects or prefers.
- `resources`: optional array of relative file paths within the skill directory that should be loaded as additional context.

example SKILL.md:

```markdown
---
name: github-review
description: Use when reviewing pull requests, summarizing repository changes, or preparing review feedback.
requiredMcpServers:
	- github
preferredTools:
	- github.list_pull_requests
	- github.get_pull_request
resources:
	- checklist.md
---

# GitHub Review Skill

Use this skill when the user asks to review a pull request or summarize repository changes.

- Inspect pull request metadata first.
- Review changed files before drafting conclusions.
- Report concrete risks and missing tests before general commentary.
```

skills selection requirements:
- ollm will select skills on demand rather than loading every skill into every request.
- ollm will use the `description` field as the primary discovery surface for deciding whether a skill is relevant to the user's prompt.
- in v1, ollm will use automatic selection only and select at most one skill per request (`top-1`).
- in v1, ollm will not support a manual skill override CLI flag.
- if a selected skill declares `requiredMcpServers`, ollm will only use that skill if those MCP servers were successfully loaded.
- if a skill's required MCP servers are unavailable, ollm will skip that skill and log the reason.

skills auto-selection scoring requirements (reasonable defaults for v1):
- ollm will score each discovered skill against the user prompt using lexical matching.
- scoring inputs will include skill `name`, `description`, and optional `preferredTools` values.
- default score weights:
	- exact phrase matches: `0.50`
	- token overlap: `0.35`
	- fuzzy token similarity: `0.15`
- ollm will normalize final scores to a `0..1` range.
- ollm will select only the highest-scoring skill when score is greater than or equal to `minScore`.
- if no skill meets `minScore`, ollm will continue without a skill.
- if two skills have equal scores, ollm will break ties deterministically by skill name in ascending lexical order.
- ollm will log selected skill name, score, and rejection reasons for non-selected skills at debug level.

skills runtime requirements:
- when a skill is selected, ollm will inject the skill's Markdown instructions into the Ollama request as additional system or hidden context.
- if a skill declares `resources`, ollm will load those files from the skill directory and include their contents as additional hidden context.
- when a skill is selected, ollm will make available the MCP-derived tools needed for that request.
- Ollama will continue to interact only through normal messages and tool calls.
- skill execution will not bypass the Ollama tool-calling loop.
- actual external actions will continue to be performed through MCP tools, not by the skill definition itself.
- skill resource loading limits will be configurable through `config.json` under `skills.resources`.
- if a resource file exceeds `maxFileSizeKB`, ollm will not load that skill and will log a warning.
- if combined resource files exceed `maxTotalSizeKB`, ollm will not load that skill and will log a warning.
- if resource limits are not configured, ollm will use documented defaults.

skills safety requirements:
- skills are instruction and asset bundles, not executable programs.
- ollm will not execute arbitrary scripts from a skill directory as part of skill loading.
- ollm will treat skill assets as local files that provide additional context only.
- if a skill references a missing resource file, ollm will log the error and continue unless that resource is required for the skill to function.

logging defaults and behavior (reasonable defaults):
- default log level is `info`.
- default log format is `jsonl` for easier troubleshooting and parsing.
- default rotation policy is `10 MB` per file with `5` retained files.
- log file names should use `ollm-YYYYMMDD.log` plus rotation suffixes.
- debug logs may include scoring and tool-call metadata but must not include secrets.

packaging and deployment requirements (python):
- ollm will target Python `3.11+`.
- ollm will be packaged using `pyproject.toml`.
- ollm will expose a console entry point named `ollm`.
- a deployed installation must include `config.json`, `mcp.json` (optional), `skills/` (optional), and `logs/`.
- if `skills/` does not exist, ollm will run without skills.
- if `mcp.json` does not exist, ollm will run without MCP tools.

acceptance and test requirements (initial):
- unit tests:
	- config loading, defaults, and invalid value fallback
	- skill discovery and SKILL.md parsing
	- top-1 skill scoring and deterministic tie-breaks
	- resource-size limit enforcement
	- log redaction for secrets
- integration tests:
	- run with no mcp.json and no skills
	- run with mcp.json and one reachable MCP server
	- tool-call loop success path
	- tool timeout path and max-turns path
	- output to stdout and output to file
- manual smoke tests:
	- install under `~/apps/ollm`
	- run prompt from `-p`, `-pf`, and stdin redirection
	- verify logs are created and rotated in `logs/`
	- verify top-1 auto-selected skill is logged at debug level


