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
        # Check if we can determine location from sys.argv[0] (ollm script path)
        argv0_path = Path(sys.argv[0]).resolve()
        if argv0_path.name == "ollm" and argv0_path.exists():
            # Running from ollm launcher script
            script_parent = argv0_path.parent
            
            # Check if we're in a venv structure (e.g., ~/apps/ollm/venv/bin/ollm)
            if (script_parent.name == "bin" and 
                script_parent.parent.name == "venv" and 
                (script_parent.parent / "pyvenv.cfg").exists()):
                # We're in installation/venv/bin/ - go up to installation directory
                install_dir = script_parent.parent.parent.resolve()
            else:
                # Regular ollm script - use its parent directory
                install_dir = script_parent.resolve()
        else:
            # Use parent directory of running executable
            executable_path = Path(sys.executable).resolve()
            if executable_path.name == "python" or executable_path.stem.startswith("python"):
                # We're in development mode or venv, check for ollm script
                # Look for ollm in the same bin directory first
                bin_dir = executable_path.parent
                ollm_script = bin_dir / "ollm"
                if ollm_script.exists():
                    # We're in a venv with ollm installed, use venv parent
                    install_dir = bin_dir.parent.resolve()
                else:
                    # Check if we're in a venv and ollm is in the venv's parent directory
                    if bin_dir.name == "bin" and (bin_dir.parent / "pyvenv.cfg").exists():
                        # We're in a venv, check parent directory for ollm script
                        venv_parent = bin_dir.parent.parent
                        ollm_script = venv_parent / "ollm"
                        if ollm_script.exists():
                            install_dir = venv_parent.resolve()
                        else:
                            # Try standard installation location as last resort
                            standard_install = Path.home() / "apps" / "ollm"
                            if standard_install.exists() and (standard_install / "ollm").exists():
                                install_dir = standard_install.resolve()
                            else:
                                # Development mode fallback - use source directory if available
                                cwd = Path.cwd().resolve()
                                if (cwd / "src" / "ollm").exists() and (cwd / "pyproject.toml").exists():
                                    install_dir = cwd
                                else:
                                    # Final fallback to current working directory
                                    install_dir = cwd
                    else:
                        # Not in a venv, try standard paths
                        standard_install = Path.home() / "apps" / "ollm"
                        if standard_install.exists() and (standard_install / "ollm").exists():
                            install_dir = standard_install.resolve()
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
    """Get path to skills directory.
    
    Resolution order:
    1. Use OLLM_SKILLS_DIR environment variable if set
    2. Use install directory + skills
    """
    # Check OLLM_SKILLS_DIR environment variable first
    skills_dir_env = os.environ.get("OLLM_SKILLS_DIR")
    if skills_dir_env:
        return Path(skills_dir_env).expanduser().resolve()
    
    # Use install directory + skills
    return resolve_install_directory() / "skills"


def get_logs_directory() -> Path:
    """Get path to logs directory."""
    return resolve_install_directory() / "logs"