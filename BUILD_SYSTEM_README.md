# OLLM Build System

This directory contains a local build system for the ollm package with the following components:

## Scripts

### Build Scripts
- **`build.py`** - Main Python build script that builds ollm into a deployable package
- **`build.sh`** - Shell wrapper that calls the Python build script

### Deployment Scripts
- **`deploy.sh`** - Deploys ollm to `~/apps/ollm` and ensures it's in your PATH
- **`uninstall.sh`** - Removes ollm installation and cleans up PATH entries

## Usage

### 1. Build the Package

```bash
# Using Python script (recommended)
./build.py

# Using shell wrapper
./build.sh
```

This will:
- Extract version from `src/ollm/__init__.py` (currently v1.2.0)
- Update `pyproject.toml` to match the version
- Build the Python package using the `build` tool
- Create a release in `Releases/ollm-{version}/` containing:
  - Built wheel file (`.whl`)
  - Source distribution (`.tar.gz`)
  - Source code copy
  - README and configuration files
  - Configuration files (`config.json`, `mcp.json` and examples)
  - Skills directory with all available skills

### 2. Deploy the Package

```bash
./deploy.sh
```

This will:
- Install ollm to `~/apps/ollm/`
- Remove any existing installation first
- Create a Python virtual environment
- Install the built package into the virtual environment
- Create a launcher script at `~/apps/ollm/ollm`
- Add `~/apps/ollm` to your PATH (in shell configuration file)
- Test the installation

### 3. Uninstall the Package

```bash
./uninstall.sh
```

This will:
- Remove the `~/apps/ollm` directory completely
- Clean up PATH entries from shell configuration files (.zshrc, .bashrc, etc.)
- Remove the empty `~/apps` directory if no other apps are installed

## Directory Structure After Build

```
Releases/
└── ollm-1.2.0/
    ├── ollm-1.2.0-py3-none-any.whl    # Built wheel
    ├── ollm-1.2.0.tar.gz              # Source distribution
    ├── README.md
    ├── pyproject.toml
    ├── config.json                    # Main configuration
    ├── config.json.example            # Configuration template
    ├── mcp.json                       # MCP server configuration
    ├── mcp.json.example               # MCP configuration template
    ├── skills/                        # Skills directory
    │   ├── data-analysis/
    │   ├── writing-help/
    │   └── ...
    └── src/                           # Source code copy
        └── ollm/
            └── ...
```

## Installation Directory Structure

```
~/apps/ollm/
├── ollm*                              # Executable launcher script
├── ollm-1.2.0-py3-none-any.whl      # Built package
├── venv/                              # Python virtual environment
│   └── ...
├── src/                               # Source code
├── config.json                       # Main configuration
├── config.json.example               # Configuration template  
├── mcp.json                          # MCP server configuration
├── mcp.json.example                  # MCP configuration template
├── skills/                            # Skills directory
│   ├── data-analysis/
│   ├── writing-help/
│   └── ...
└── README.md, pyproject.toml         # Documentation and config
```

## Requirements

- Python 3.11 or higher
- `build` package (automatically installed if missing)
- Standard Unix tools (bash, etc.)

## Features

- **Version Management**: Automatically extracts version from source code
- **Isolated Environment**: Uses virtual environment to avoid conflicts
- **PATH Management**: Automatically manages shell PATH configuration
- **Clean Uninstall**: Completely removes all traces of the installation
- **Error Handling**: Comprehensive error checking and user feedback
- **Cross-Shell Support**: Works with bash, zsh, and other shells
- **Safe Updates**: Removes old installations before deploying new ones

## Troubleshooting

### Command Not Found After Install

If `ollm` command is not found after installation:

1. Restart your terminal, or
2. Source your shell configuration:
   ```bash
   source ~/.zshrc    # For zsh
   source ~/.bashrc   # For bash
   ```
3. Clear command cache: `hash -r`

### Permission Issues

Make sure scripts are executable:
```bash
chmod +x build.py build.sh deploy.sh uninstall.sh
```

### Build Failures

1. Ensure you're in the project root directory
2. Check that `src/ollm/__init__.py` contains `__version__`
3. Verify Python 3.11+ is installed
4. Check network connectivity for package downloads