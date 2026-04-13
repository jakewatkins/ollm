"""Error definitions for ollm."""


class OllmError(Exception):
    """Base exception for ollm errors."""
    pass


class InstallDirectoryError(OllmError):
    """Raised when install directory cannot be resolved or is invalid."""
    pass


class ConfigurationError(OllmError):
    """Raised when configuration is invalid or cannot be loaded."""
    pass


class OllamaError(OllmError):
    """Raised when Ollama API requests fail."""
    pass


class MCPError(OllmError):
    """Raised when MCP server operations fail."""
    pass


class SkillError(OllmError):
    """Raised when skill operations fail."""
    pass