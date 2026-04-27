"""Command line interface for ollm."""

import sys
import traceback
from pathlib import Path
from typing import Optional, List

import typer
from typing_extensions import Annotated

from . import __version__
from .app import get_app
from .errors import OllmError
from .newrelic_integration import get_event_recorder

app = typer.Typer(
    name="ollm",
    help="A command line tool that wraps Ollama HTTP endpoint with MCP servers and skills",
    no_args_is_help=False,  # Allow running without args to read from stdin
)


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        print(f"ollm version {__version__}")
        raise typer.Exit()


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
    verbose: Annotated[
        bool,
        typer.Option("-v", "--verbose", help="Enable verbose output (shows secret warnings)")
    ] = False,
    files: Annotated[
        Optional[List[Path]],
        typer.Option("-f", "--file", help="Attach text/markdown files to context")
    ] = None,
    version: Annotated[
        Optional[bool],
        typer.Option("--version", callback=version_callback, help="Show version and exit")
    ] = None,
) -> None:
    """Process a prompt using Ollama with MCP tools and skills support."""
    
    # Initialize the application
    ollm_app = get_app()
    # Set custom config file if provided
    if config_file:
        ollm_app.config_file = config_file
    ollm_app.verbose = verbose  # Pass verbose flag to app
    ollm_app.initialize()
    
    # Handle list models mode
    if list_models:
        # Validate that only -o can be combined with --listModels
        if prompt is not None or prompt_file is not None or model is not None or files is not None:
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
    
    # Append file attachments if provided
    if files:
        prompt_content = _append_file_attachments(prompt_content, files)
    
    # Process the prompt
    try:
        ollm_app.process_prompt(prompt_content, model, output)
    except OllmError as e:
        # Record error event
        event_recorder = get_event_recorder()
        if event_recorder:
            event_recorder.record_error(
                error_type=type(e).__name__,
                error_message=str(e),
                error_source="CLI",
                stack_trace=traceback.format_exc()
            )
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)
    except Exception as e:
        # Record unexpected error event
        event_recorder = get_event_recorder()
        if event_recorder:
            event_recorder.record_error(
                error_type=type(e).__name__,
                error_message=str(e),
                error_source="CLI",
                stack_trace=traceback.format_exc()
            )
        print(f"Unexpected error: {e}", file=sys.stderr)
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


def _append_file_attachments(prompt_content: str, files: List[Path]) -> str:
    """Append file attachments to prompt content.
    
    Args:
        prompt_content: Original user prompt
        files: List of file paths to attach
        
    Returns:
        Enhanced prompt with file attachments
        
    Raises:
        typer.Exit: On file reading errors
    """
    if not files:
        return prompt_content
    
    # Define supported file extensions
    supported_extensions = {".txt", ".md", ".markdown", ".json", ".yaml", ".yml"}
    
    # Start building the enhanced prompt
    enhanced_prompt = prompt_content
    
    # Add separator and header
    enhanced_prompt += "\n\n---\n\n**Attached Files:**\n\n"
    
    # Process each file
    processed_files = 0
    for file_path in files:
        try:
            # Validate file type
            if file_path.suffix.lower() not in supported_extensions:
                print(f"Warning: Skipping unsupported file type: {file_path}", file=sys.stderr)
                continue
            
            # Check if file exists and is readable
            if not file_path.exists():
                print(f"Error: File not found: {file_path}", file=sys.stderr)
                raise typer.Exit(1)
            
            if not file_path.is_file():
                print(f"Error: Path is not a file: {file_path}", file=sys.stderr)
                raise typer.Exit(1)
            
            # Read file content
            content = file_path.read_text(encoding="utf-8")
            
            # Add file section
            enhanced_prompt += f"**{file_path.name}:**\n```\n{content}\n```\n\n"
            processed_files += 1
            
        except FileNotFoundError:
            print(f"Error: File not found: {file_path}", file=sys.stderr)
            raise typer.Exit(1)
        except PermissionError:
            print(f"Error: Permission denied reading file: {file_path}", file=sys.stderr)
            raise typer.Exit(1)
        except UnicodeDecodeError:
            print(f"Error: File is not valid UTF-8 text: {file_path}", file=sys.stderr)
            raise typer.Exit(1)
        except Exception as e:
            print(f"Error reading file {file_path}: {e}", file=sys.stderr)
            raise typer.Exit(1)
    
    # If no files were processed, return original prompt
    if processed_files == 0:
        print("Warning: No supported files were attached", file=sys.stderr)
        return prompt_content
    
    return enhanced_prompt