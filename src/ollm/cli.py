"""Command line interface for ollm."""

import sys
from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from .app import get_app
from .errors import OllmError

app = typer.Typer(
    name="ollm",
    help="A command line tool that wraps Ollama HTTP endpoint with MCP servers and skills",
    no_args_is_help=False,  # Allow running without args to read from stdin
)


@app.command()
def main(
    prompt: Annotated[
        Optional[str],
        typer.Option("-p", "--prompt", help="Prompt text to send to the model")
    ] = None,
    prompt_file: Annotated[
        Optional[Path],
        typer.Option("-pf", "--prompt-file", help="File containing the prompt text")
    ] = None,
    output: Annotated[
        Optional[Path],
        typer.Option("-o", "--output", help="Output file path (default: stdout)")
    ] = None,
    model: Annotated[
        Optional[str],
        typer.Option("-m", "--model", help="Ollama model name to use")
    ] = None,
    config_file: Annotated[
        Optional[Path],
        typer.Option("-c", "--config", help="Configuration file path")
    ] = None,
    list_models: Annotated[
        bool,
        typer.Option("--listModels", help="List available Ollama models (one per line)")
    ] = False,
) -> None:
    """Process a prompt using Ollama with MCP tools and skills support."""
    
    # Initialize the application
    ollm_app = get_app()
    # Set custom config file if provided
    if config_file:
        ollm_app.config_file = config_file
    ollm_app.initialize()
    
    # Handle list models mode
    if list_models:
        # Validate that only -o can be combined with --listModels
        if prompt is not None or prompt_file is not None or model is not None:
            print("Error: --listModels can only be combined with -o/--output flag.", file=sys.stderr)
            raise typer.Exit(1)
        
        try:
            ollm_app.list_models(output)
        except OllmError as e:
            print(f"Error: {e}", file=sys.stderr)
            raise typer.Exit(1)
        finally:
            ollm_app.cleanup()
        return
    
    # Validate mutually exclusive prompt options
    if prompt is not None and prompt_file is not None:
        print("Error: -p/--prompt and -pf/--prompt-file are mutually exclusive.", file=sys.stderr)
        raise typer.Exit(1)
    
    # Get prompt content
    prompt_content = _get_prompt_content(prompt, prompt_file)
    
    # Process the prompt
    try:
        ollm_app.process_prompt(prompt_content, model, output)
    except OllmError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)
    finally:
        # Cleanup resources
        ollm_app.cleanup()


def _get_prompt_content(prompt: Optional[str], prompt_file: Optional[Path]) -> str:
    """Get prompt content from command line arg, file, or stdin."""
    if prompt is not None:
        return prompt
    elif prompt_file is not None:
        try:
            return prompt_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            print(f"Error: Prompt file not found: {prompt_file}", file=sys.stderr)
            raise typer.Exit(1)
        except PermissionError:
            print(f"Error: Permission denied reading prompt file: {prompt_file}", file=sys.stderr)
            raise typer.Exit(1)
        except Exception as e:
            print(f"Error reading prompt file {prompt_file}: {e}", file=sys.stderr)
            raise typer.Exit(1)
    else:
        # Read from stdin
        try:
            if sys.stdin.isatty():
                print("Reading prompt from stdin (press Ctrl+D when done):", file=sys.stderr)
            return sys.stdin.read()
        except KeyboardInterrupt:
            print("\nOperation cancelled.", file=sys.stderr)
            raise typer.Exit(130)
        except Exception as e:
            print(f"Error reading from stdin: {e}", file=sys.stderr)
            raise typer.Exit(1)