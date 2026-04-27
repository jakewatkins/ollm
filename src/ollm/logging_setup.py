"""Logging setup for ollm."""

import json
import logging
import logging.handlers
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import newrelic.agent
    NEW_RELIC_AVAILABLE = True
except ImportError:
    NEW_RELIC_AVAILABLE = False

from .config import LoggingConfig
from .paths import get_logs_directory


class SecureFormatter(logging.Formatter):
    """Formatter that redacts sensitive information from log messages."""
    
    # Patterns to redact sensitive information
    REDACTION_PATTERNS = [
        (re.compile(r'("api[_-]?key"\s*:\s*")[^"]+(")', re.IGNORECASE), r'\1[REDACTED]\2'),
        (re.compile(r'("password"\s*:\s*")[^"]+(")', re.IGNORECASE), r'\1[REDACTED]\2'),
        (re.compile(r'("token"\s*:\s*")[^"]+(")', re.IGNORECASE), r'\1[REDACTED]\2'),
        (re.compile(r'("authorization"\s*:\s*")[^"]+(")', re.IGNORECASE), r'\1[REDACTED]\2'),
        (re.compile(r'(Authorization:\s*Bearer\s+)[^\s]+', re.IGNORECASE), r'\1[REDACTED]'),
        (re.compile(r'(api[_-]?key[=:]\s*)[^\s&]+', re.IGNORECASE), r'\1[REDACTED]'),
    ]
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with redaction."""
        formatted = super().format(record)
        
        # Apply redaction patterns
        for pattern, replacement in self.REDACTION_PATTERNS:
            formatted = pattern.sub(replacement, formatted)
        
        return formatted


class JSONLFormatter(SecureFormatter):
    """JSONL formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format as JSON line."""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, '__dict__'):
            extra = {k: v for k, v in record.__dict__.items() 
                    if k not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                                'pathname', 'filename', 'module', 'exc_info',
                                'exc_text', 'stack_info', 'lineno', 'funcName',
                                'created', 'msecs', 'relativeCreated', 'thread',
                                'threadName', 'processName', 'process', 'message']}
            if extra:
                log_data.update(extra)
        
        # Handle exception info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Apply redaction to JSON string
        json_str = json.dumps(log_data, ensure_ascii=False)
        for pattern, replacement in self.REDACTION_PATTERNS:
            json_str = pattern.sub(replacement, json_str)
        
        return json_str


class TextFormatter(SecureFormatter):
    """Text formatter for human-readable logging."""
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


def get_log_filename(config: LoggingConfig) -> Path:
    """Generate date-based log filename.
    
    Args:
        config: Logging configuration
        
    Returns:
        Path to log file with date
    """
    if config.log_filename:
        # Use configured absolute path
        base_path = Path(config.log_filename)
        # Ensure parent directory exists
        base_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        # Use default location in logs directory
        logs_dir = get_logs_directory()
        logs_dir.mkdir(exist_ok=True)
        base_path = logs_dir / "logfile.log"
    
    # Add date before extension
    date_str = datetime.now().strftime('%Y%m%d')
    if base_path.suffix:
        # Has extension: file.log -> file-20260426.log
        stem = base_path.stem
        suffix = base_path.suffix
        dated_name = f"{stem}-{date_str}{suffix}"
    else:
        # No extension: logfile -> logfile-20260426
        dated_name = f"{base_path.name}-{date_str}"
    
    return base_path.parent / dated_name


def setup_newrelic_logging() -> Optional[logging.Handler]:
    """Setup New Relic log forwarding.
    
    Returns:
        New Relic handler if available, None otherwise
    """
    if not NEW_RELIC_AVAILABLE:
        return None
        
    try:
        # Create New Relic log handler
        handler = newrelic.agent.NewRelicLogForwardingHandler()
        handler.setLevel(logging.DEBUG)  # Forward all log levels
        
        # Use secure formatter to sanitize logs
        formatter = SecureFormatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        return handler
    except Exception as e:
        # Log warning but don't fail
        logging.getLogger(__name__).warning(f"Failed to setup New Relic logging: {e}")
        return None


def setup_logging(config: LoggingConfig) -> None:
    """Setup logging configuration.
    
    Args:
        config: Logging configuration
    """
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.level.upper()))
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Create log file with date
    log_file = get_log_filename(config)
    
    # Create rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=config.max_file_size_mb * 1024 * 1024,  # Convert MB to bytes
        backupCount=config.max_files,
        encoding='utf-8'
    )
    
    # Configure formatter based on format setting
    if config.format == 'jsonl':
        formatter = JSONLFormatter()
    else:
        formatter = TextFormatter()
    
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Add New Relic logging handler if available
    newrelic_handler = setup_newrelic_logging()
    if newrelic_handler:
        root_logger.addHandler(newrelic_handler)
    
    # Also add console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console
    console_formatter = TextFormatter()
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)