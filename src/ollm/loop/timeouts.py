"""Timeout utilities for agent loop and tool calls."""

import asyncio
import time
from typing import TypeVar, Callable, Any, Awaitable

from ..errors import OllmError

T = TypeVar('T')


class TimeoutError(OllmError):
    """Raised when an operation times out."""
    pass


async def with_timeout(
    coroutine: Awaitable[T],
    timeout_seconds: float,
    operation_name: str = "operation"
) -> T:
    """Execute a coroutine with a timeout.
    
    Args:
        coroutine: The coroutine to execute
        timeout_seconds: Timeout in seconds  
        operation_name: Name for error messages
        
    Returns:
        Result of the coroutine
        
    Raises:
        TimeoutError: If timeout is exceeded
    """
    try:
        return await asyncio.wait_for(coroutine, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        raise TimeoutError(f"{operation_name} timed out after {timeout_seconds}s")


class Timer:
    """Simple timer for measuring elapsed time."""
    
    def __init__(self):
        self.start_time = time.time()
    
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        return time.time() - self.start_time
    
    def reset(self) -> None:
        """Reset the timer."""
        self.start_time = time.time()