"""Main entry point for the ollm CLI tool."""

import sys
from typing import Optional

import typer

from .cli import app


def main() -> None:
    """Main entry point for the ollm command."""
    try:
        app()
    except KeyboardInterrupt:
        print("\nOperation cancelled.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()