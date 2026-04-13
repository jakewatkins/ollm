"""Output handling for ollm."""

import sys
from pathlib import Path
from typing import Optional

import typer

from .logging_setup import get_logger

logger = get_logger(__name__)


def write_output(content: str, output_file: Optional[Path]) -> None:
    """Write content to file or stdout.
    
    Args:
        content: Content to write
        output_file: Optional output file path
        
    Raises:
        typer.Exit: On output errors
    """
    if output_file is not None:
        try:
            logger.info(f"Writing output to file: {output_file}")
            output_file.write_text(content, encoding="utf-8")
            logger.debug(f"Successfully wrote {len(content)} characters to {output_file}")
        except PermissionError:
            logger.error(f"Permission denied writing to output file: {output_file}")
            print(f"Error: Permission denied writing to output file: {output_file}", file=sys.stderr)
            raise typer.Exit(1)
        except Exception as e:
            logger.error(f"Error writing to output file {output_file}: {e}")
            print(f"Error writing to output file {output_file}: {e}", file=sys.stderr)
            raise typer.Exit(1)
    else:
        logger.debug("Writing output to stdout")
        print(content)