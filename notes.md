
I'm interested in having ollm be able to do skills but i'm not sure how to specify them or how they'd work here.
before going on - do they make sense for what we are building?
I'd want to implement skills in a similar fashion to how they are done in visual studio code.  We'd have a skills subdirectory in the directory where ollm is installed.  each skill we add would get a subdirectory in the skills subdirectory.
how would skills be exposed to ollama?  can you explain how it would discover them and then use them?  


I’m checking how VS Code skills are structured so I can answer whether they fit this CLI and describe a concrete discovery/use model without inventing one.

Read skill [agent-customization](file:///Users/jakewatkins/.vscode/extensions/github.copilot-chat-0.43.0/assets/prompts/skills/agent-customization/SKILL.md?vscodeLinkType%3Dskill)

I’ve loaded the customization guidance; next I’m checking the public VS Code docs for how skills are discovered and invoked so I can map that idea cleanly onto `ollm`.



Fetched 4 resources

Yes, skills make sense for what you’re building, but only if you define them as wrapper-side workflow packages, not as something Ollama natively understands.

The key boundary is this: Ollama’s HTTP API understands messages and tools. It does not have a first-class `skills` concept. So in `ollm`, a skill would be something your CLI discovers and applies before calling Ollama. In practice, that means a skill influences:
- what hidden instructions are sent to Ollama
- what MCP tools are made available for that request
- what supporting files or templates are added as context

That is very close to how VS Code skills work conceptually: they are on-demand bundles of instructions and assets for a specific task. For `ollm`, that is a good fit if your goal is reusable workflows like “debug a Python project”, “review a repo”, “write release notes”, or “query a service through MCP”. If all you want is static prompt presets, skills are probably too heavy and simple prompt files would be enough.

**How Skills Should Work In `ollm`**
A good design is:

- `ollm` has a `skills` directory in its install directory.
- Each skill lives in its own subdirectory.
- Each skill folder has a SKILL.md file as the entry point.
- The skill can also contain supporting assets such as prompt fragments, templates, or docs.

Example shape:

```text
ollm/
  skills/
    github-review/
      SKILL.md
      checklist.md
      prompt-template.md
    incident-response/
      SKILL.md
      runbook.md
```

For your CLI, I would define a skill as:

- a SKILL.md file with metadata plus instructions
- optional companion files in the same folder
- optional declared MCP dependencies, such as required servers or preferred tools

The important part is that skills should not be “exposed to Ollama” as API objects. They should be converted by `ollm` into prompt context and tool availability.

**How Discovery Should Work**
VS Code-style discovery maps well to a CLI if you keep it simple.

At startup or on first request, `ollm` should:

1. Scan `skills/*/SKILL.md`.
2. Parse each SKILL.md for metadata like `name` and `description`.
3. Build an in-memory skill catalog.
4. Use the `description` as the discovery surface for deciding whether a skill is relevant.

That description matters a lot. In VS Code, the description is what helps the agent decide to load a skill. The same principle should apply here.

A minimal metadata shape could be:

```yaml
---
name: github-review
description: Use when reviewing pull requests, summarizing code changes, or preparing review feedback for a GitHub repository.
requiredMcpServers:
  - github
preferredTools:
  - github.list_pull_requests
  - github.get_pull_request
---
```

Then the body of SKILL.md contains the actual workflow instructions for the model.

**How `ollm` Should Use Skills**
The best model is on-demand loading, not loading every skill into every request.

Recommended flow:

1. User sends a prompt.
2. `ollm` compares the prompt to the catalog of skill descriptions.
3. `ollm` selects zero, one, or a few relevant skills.
4. `ollm` loads the selected SKILL.md bodies and any referenced assets.
5. `ollm` turns that material into one or more hidden system messages.
6. `ollm` ensures the MCP servers required by those skills are loaded.
7. `ollm` exposes the corresponding MCP tools to Ollama in the `tools` field.
8. Ollama runs normally and emits `tool_calls`.
9. `ollm` executes those tool calls through MCP and continues the agent loop.

So the skill changes the behavior of the request, but the actual “action surface” still goes through Ollama tool calling.

A useful mental model is:

- MCP servers provide capabilities
- skills provide guidance on when and how to use those capabilities

**How Skills Are Exposed To Ollama**
Not as a separate API field. They are exposed indirectly in two ways:

1. Instruction context  
`ollm` injects the selected skill content into the prompt as hidden instructions.

Example:

```text
System:
You have access to repository tools.
When the task is a pull request review, follow the github-review skill:
- inspect the PR metadata
- review changed files
- summarize risk areas first
- keep findings concrete
```

2. Tool scope  
`ollm` includes the relevant MCP-derived tools in the `tools` list it sends to Ollama.

That means Ollama experiences a skill as:
- extra operating instructions
- a curated set of tools it can call

That is the right place for skills in this architecture.

**What I Would Recommend**
Yes, include skills, but define them narrowly.

For `ollm`, the cleanest version is:
- skills are instruction bundles with optional assets
- MCP remains the only execution mechanism
- skills do not directly run scripts or shell commands
- skills can declare MCP dependencies

That keeps the architecture clean. If you let skills execute arbitrary code directly, you start mixing skills, hooks, plugins, and MCP into one feature, which will get messy fast.

A good first version would support:
- `skills/<name>/SKILL.md`
- frontmatter with `name`, `description`, and optional `requiredMcpServers`
- automatic discovery by scanning the `skills` directory
- automatic selection by matching the prompt against skill descriptions
- injection of selected skill instructions into the Ollama request

A very useful CLI addition would be an explicit override such as `--skill github-review`, even if you also support automatic matching. That gives you deterministic behavior when the user wants it.

If you want, I can turn this into concrete requirements text for requirements.md, including a proposed SKILL.md schema and the runtime discovery/selection flow.


Let me perform some testing.  Before I do that, can you help me with these details:
- how do I run ollm from the command line right now?  do I need to be in the project directory?  Do I need to setup a python venv?  Please provide some directions.
- can we setup the playwright mcp server and configure it for ollm to use?


## We might want to add a flag to ollm so it can return a list of models available in ollama
## we also might want to modify the skills requirements so they can use cli stuff in addition to mcp

