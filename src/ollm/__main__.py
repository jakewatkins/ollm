"""Main entry point for the ollm CLI tool."""

import sys
import traceback
from typing import Optional

import typer

from .cli import app
from .newrelic_integration import get_event_recorder


def main() -> None:
    """Main entry point for the ollm command."""
    try:
        app()
    except KeyboardInterrupt:
        print("\nOperation cancelled.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        # Record error event for unhandled exceptions
        event_recorder = get_event_recorder()
        if event_recorder:
            event_recorder.record_error(
                error_type=type(e).__name__,
                error_message=str(e),
                error_source="main",
                stack_trace=traceback.format_exc()
            )
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()