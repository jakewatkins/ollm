# ollm

A command line tool that wraps Ollama HTTP endpoint with MCP servers and skills support.

## Quick Start

### Installation

```bash
# Install in development mode
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

### Basic Usage

```bash
# Using prompt from command line
ollm -p "What is the capital of France?"

# Using prompt from file
echo "What is the capital of France?" > prompt.txt
ollm -pf prompt.txt

# Using stdin
echo "What is the capital of France?" | ollm

# Save output to file
ollm -p "What is the capital of France?" -o output.txt

# Specify model
ollm -p "What is the capital of France?" -m llama2
```

### Command Options

- `-p, --prompt`: Prompt text to send to the model
- `-pf, --prompt-file`: File containing the prompt text  
- `-o, --output`: Output file path (default: stdout)
- `-m, --model`: Ollama model name to use
- `--help`: Show help message

Note: `-p` and `-pf` are mutually exclusive.

## Development

This is currently in early development. The tool will eventually support:

- MCP (Model Context Protocol) server integration
- Skills-based workflow automation
- Configurable timeouts and limits
- Comprehensive logging

See [requirements.md](requirements.md) for full specification and [plan.md](plan.md) for implementation roadmap.

## Current Status

✅ **Phase 1**: Basic CLI scaffold (current milestone)  
⏳ **Phase 2**: Configuration and logging  
⏳ **Phase 3**: Ollama integration  
⏳ **Phase 4**: MCP integration  
⏳ **Phase 5**: Skills system  
⏳ **Phase 6**: Packaging and docs  
⏳ **Phase 7**: Testing and release