# ollm

A command line tool that wraps Ollama HTTP endpoint with MCP servers and skills support for enhanced AI workflows.

## Features

✅ **Skills System**: VS Code-style skills for specialized workflows (writing help, code review, data analysis)  
✅ **Script Execution**: Secure Docker-based script execution for complex tasks  
✅ **MCP Integration**: Model Context Protocol support for external tools and services  
✅ **Multiple Models**: Support for all Ollama models with automatic selection  
✅ **Flexible Input**: Accept prompts via command line, files, or stdin  
✅ **Cross-Platform**: Works on macOS, Linux, and Windows with proper Docker integration

## Quick Start

### Prerequisites

- Python 3.11 or higher
- [Ollama](https://ollama.ai/) running locally or accessible via network
- [Docker](https://docs.docker.com/get-docker/) (optional, for script execution features)

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd ollm

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e .
```

> **Development Note:** After installation, use the `ollm` command directly. For uninstalled development, you can still use `python -m src.ollm` to run from source.

### Basic Usage

```bash
# Using prompt from command line
ollm -p "What is the capital of France?"

# List available models
ollm --listModels

# Using prompt from file
echo "What is the capital of France?" > prompt.txt
ollm -pf prompt.txt

# Using stdin
echo "What is the capital of France?" | ollm

# Save output to file
ollm -p "What is the capital of France?" -o output.txt

# Specify model and config
ollm -p "Help me code" -m llama3.2:latest -c config.json
```

### Skills Examples

The skills system automatically enhances prompts with specialized guidance:

```bash
# Writing assistance (uses writing-help skill)
ollm -p "Help me improve this email: 'Hey, can you fix the thing?'"

# Code review (uses github-review skill)  
ollm -p "Review this pull request for security issues"

# Data analysis (uses data-analysis skill)
ollm -p "Analyze this CSV data and find trends"
```

### Command Options

- `-p, --prompt`: Prompt text to send to the model
- `-pf, --prompt-file`: File containing the prompt text  
- `-o, --output`: Output file path (default: stdout)
- `-m, --model`: Ollama model name to use
- `-c, --config`: Configuration file path
- `--listModels`: List available Ollama models (can combine with -o)
- `--help`: Show help message

Note: `-p` and `-pf` are mutually exclusive.

## Configuration

Create a `config.json` file to customize behavior:

```json
{
  "baseUrl": "http://localhost:11434",
  "agentLoop": {
    "maxTurns": 8,
    "toolCallTimeoutSeconds": 60
  },
  "skills": {
    "selection": {
      "topK": 1,
      "minScore": 0.35,
      "fuzzyMatch": true
    }
  },
  "scriptExecution": {
    "enabled": true,
    "image": "python:3.11-slim",
    "executionTimeoutSeconds": 30
  }
}
```

## Skills System

Skills are VS Code-style workflow packages stored in the `skills/` directory:

```
skills/
  writing-help/
    SKILL.md          # Skill definition and instructions
  github-review/
    SKILL.md
    checklist.md      # Supporting resources
  data-analysis/
    SKILL.md
    templates/        # Script templates
```

Each skill contains:
- **Metadata**: Name, description, and optional MCP dependencies
- **Instructions**: Specialized guidance for the AI model  
- **Resources**: Supporting files, templates, or documentation

## Development

This project follows a milestone-based development approach with comprehensive skills and MCP integration.

- MCP (Model Context Protocol) server integration
- Skills-based workflow automation
- Configurable timeouts and limits
- Comprehensive logging

See [requirements.md](requirements.md) for full specification and [plan.md](plan.md) for implementation roadmap.

## Current Status

✅ **Phase 1**: Basic CLI scaffold - **COMPLETE**  
✅ **Phase 2**: Configuration and logging - **COMPLETE**  
✅ **Phase 3**: Ollama integration - **COMPLETE**  
✅ **Phase 4**: MCP integration - **COMPLETE**  
✅ **Phase 5**: Skills system - **COMPLETE**  
⏳ **Phase 6**: Packaging and docs  
⏳ **Phase 7**: Testing and release

### Recent Updates

- ✅ Full skills system with VS Code-style workflow packages
- ✅ Docker-based script execution with cross-platform compatibility  
- ✅ macOS Docker Desktop connectivity fixes
- ✅ Enhanced prompt processing with skill-based context injection
- ✅ Multi-model support with automatic selection
- ✅ Comprehensive error handling and logging

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CLI Interface │────│  Skills System  │────│ Script Executor │
└─────────────────┘    └─────────────────┘    └─────────────────┘
          │                       │                       │
          └───────────────────────┼───────────────────────┘
                                  │
          ┌─────────────────┐    ┌▼─────────────────┐    ┌─────────────────┐
          │  MCP Clients    │────│   Agent Loop     │────│ Ollama Client   │
          └─────────────────┘    └──────────────────┘    └─────────────────┘
                                           │
                                  ┌────────▼────────┐
                                  │ LLM (via Ollama)│
                                  └─────────────────┘
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Commit your changes: `git commit -m 'Add amazing feature'`
5. Push to the branch: `git push origin feature/amazing-feature`
6. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Troubleshooting

### Docker Connection Issues on macOS

If you see Docker connection errors, ensure Docker Desktop is running:

```bash
# Check Docker status
docker ps

# If needed, restart Docker Desktop
killall "Docker Desktop" && open -a "Docker Desktop"
```

### Skills Not Loading

Verify your skills directory structure:

```bash
ls -la skills/*/SKILL.md
```

Each skill should have a `SKILL.md` file with proper YAML frontmatter.