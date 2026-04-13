"""Logging setup for ollm."""

import json
import logging
import logging.handlers
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

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


def setup_logging(config: LoggingConfig) -> None:
    """Setup logging configuration.
    
    Args:
        config: Logging configuration
    """
    # Create logs directory
    logs_dir = get_logs_directory()
    logs_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.level.upper()))
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Create log file with date
    log_file = logs_dir / f"ollm-{datetime.now().strftime('%Y%m%d')}.log"
    
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