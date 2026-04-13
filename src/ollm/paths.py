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
            # We're in development mode or venv, check for ollm script
            # Look for ollm in the same bin directory
            bin_dir = executable_path.parent
            ollm_script = bin_dir / "ollm"
            if ollm_script.exists():
                # We're in a venv with ollm installed, use venv parent
                install_dir = bin_dir.parent.resolve()
            else:
                # Development mode, use current working directory
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
    """Get path to config.json file.
    
    Resolution order:
    1. Use OLLM_CONFIG environment variable if set
    2. Use install directory + config.json
    3. Fall back to home directory + config.json
    4. Use packaged default config
    """
    import os
    
    # Check OLLM_CONFIG environment variable first
    ollm_config = os.environ.get("OLLM_CONFIG")
    if ollm_config:
        config_path = Path(ollm_config).expanduser().resolve()
        if config_path.exists():
            return config_path
    
    # Try install directory
    try:
        install_dir = resolve_install_directory()
        config_path = install_dir / "config.json"
        if config_path.exists():
            return config_path
    except InstallDirectoryError:
        pass
    
    # Fall back to home directory
    home_config = Path.home() / "config.json"
    if home_config.exists():
        return home_config
    
    # Try packaged default config
    try:
        import pkg_resources
        default_config = Path(pkg_resources.resource_filename("ollm", "data/default-config.json"))
        if default_config.exists():
            return default_config
    except (ImportError, FileNotFoundError):
        pass
        
    # Return the preferred path (OLLM_CONFIG or install dir) for error messages
    if ollm_config:
        return Path(ollm_config).expanduser().resolve()
    
    try:
        return resolve_install_directory() / "config.json"
    except InstallDirectoryError:
        return Path.home() / "config.json"


def get_mcp_config_path() -> Path:
    """Get path to mcp.json file."""
    return resolve_install_directory() / "mcp.json"


def get_skills_directory() -> Path:
    """Get path to skills directory."""
    return resolve_install_directory() / "skills"


def get_logs_directory() -> Path:
    """Get path to logs directory."""
    return resolve_install_directory() / "logs"