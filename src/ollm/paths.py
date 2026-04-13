"""Install directory resolution for ollm."""

import os
import sys
from pathlib import Path
from typing import Optional

from .errors import InstallDirectoryError


def resolve_install_directory() -> Path:
    """Resolve the ollm install directory.
    
    Resolution order:
    1. Use OLLM_HOME if set
    2. Otherwise use parent directory of running executable
    3. Validate the path is under user's home directory
    
    Returns:
        Path to the install directory
        
    Raises:
        InstallDirectoryError: If directory cannot be resolved or is invalid
    """
    install_dir: Optional[Path] = None
    
    # Try OLLM_HOME first
    ollm_home = os.environ.get("OLLM_HOME")
    if ollm_home:
        install_dir = Path(ollm_home).resolve()
    else:
        # Use parent directory of running executable
        executable_path = Path(sys.executable).resolve()
        if executable_path.name == "python" or executable_path.stem.startswith("python"):
            # We're in development mode, use current working directory
            install_dir = Path.cwd().resolve()
        else:
            # Production - use parent of executable
            install_dir = executable_path.parent.resolve()
    
    if install_dir is None:
        raise InstallDirectoryError("Could not determine install directory")
    
    # Validate install directory is under user's home
    home_path = Path.home().resolve()
    try:
        install_dir.relative_to(home_path)
    except ValueError:
        raise InstallDirectoryError(
            f"Install directory {install_dir} is not under user home directory {home_path}. "
            f"Please install ollm under your home directory or set OLLM_HOME to a valid path."
        )
    
    return install_dir


def get_config_path() -> Path:
    """Get path to config.json file."""
    return resolve_install_directory() / "config.json"


def get_mcp_config_path() -> Path:
    """Get path to mcp.json file."""
    return resolve_install_directory() / "mcp.json"


def get_skills_directory() -> Path:
    """Get path to skills directory."""
    return resolve_install_directory() / "skills"


def get_logs_directory() -> Path:
    """Get path to logs directory."""
    return resolve_install_directory() / "logs"