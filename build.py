#!/usr/bin/env python3
"""
Build script for ollm package.
Builds the package and stores it in Releases/ollm-{version}/
"""

import ast
import os
import shutil
import subprocess
import sys
from pathlib import Path


def get_version():
    """Extract version from src/ollm/__init__.py"""
    init_file = Path("src/ollm/__init__.py")
    if not init_file.exists():
        raise FileNotFoundError(f"Cannot find {init_file}")
    
    with open(init_file, "r") as f:
        tree = ast.parse(f.read())
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__version__":
                    return ast.literal_eval(node.value)
    
    raise ValueError("Could not find __version__ in __init__.py")


def update_pyproject_version(version):
    """Update version in pyproject.toml to match __init__.py"""
    pyproject_file = Path("pyproject.toml")
    if not pyproject_file.exists():
        raise FileNotFoundError("Cannot find pyproject.toml")
    
    content = pyproject_file.read_text()
    lines = content.split("\n")
    
    for i, line in enumerate(lines):
        if line.startswith('version = "'):
            lines[i] = f'version = "{version}"'
            break
    
    pyproject_file.write_text("\n".join(lines))
    print(f"Updated pyproject.toml version to {version}")


def ensure_build_dependencies():
    """Ensure required build dependencies are installed"""
    print("Checking build dependencies...")
    
    # Required packages for building
    required_packages = ["setuptools", "wheel"]
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} is available")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package} is missing")
    
    if missing_packages:
        print(f"Installing missing packages: {', '.join(missing_packages)}")
        try:
            cmd = [sys.executable, "-m", "pip", "install", "--upgrade"] + missing_packages
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                print(f"Failed to install dependencies: {result.stderr}")
                return False
            print("Dependencies installed successfully")
        except subprocess.TimeoutExpired:
            print("Timeout while installing dependencies")
            return False
        except Exception as e:
            print(f"Error installing dependencies: {e}")
            return False
    
    return True


def create_setup_py():
    """Create a simple setup.py if it doesn't exist"""
    if Path("setup.py").exists():
        return
    
    setup_content = '''#!/usr/bin/env python3
from setuptools import setup

if __name__ == "__main__":
    setup()
'''
    
    with open("setup.py", "w") as f:
        f.write(setup_content)
    print("Created setup.py")


def build_package():
    """Build the Python package using reliable setuptools approach"""
    print("Building package...")
    
    # Clean previous builds
    dirs_to_clean = ["build", "dist", "src/ollm.egg-info"]
    for dir_path in dirs_to_clean:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
            print(f"Cleaned {dir_path}")
    
    # Ensure build dependencies
    if not ensure_build_dependencies():
        return False
    
    # Create setup.py if needed
    create_setup_py()
    
    print("Building using setuptools (faster and more reliable)...")
    
    try:
        # Build source distribution
        print("Building source distribution...")
        result = subprocess.run([
            sys.executable, "setup.py", "sdist"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print(f"Source distribution build failed: {result.stderr}")
            # Try pip wheel fallback
            return build_with_pip_wheel()
        
        # Build wheel
        print("Building wheel...")
        result = subprocess.run([
            sys.executable, "setup.py", "bdist_wheel"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print(f"Wheel build failed: {result.stderr}")
            return build_with_pip_wheel()
        
        print("Package built successfully with setuptools")
        return True
        
    except subprocess.TimeoutExpired:
        print("⏰ Build timed out, trying pip wheel...")
        return build_with_pip_wheel()
    except Exception as e:
        print(f"Build error: {e}, trying pip wheel...")
        return build_with_pip_wheel()


def build_with_pip_wheel():
    """Fallback: Build using pip wheel"""
    print("Using pip wheel as fallback...")
    try:
        result = subprocess.run([
            sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "-w", "dist"
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode != 0:
            print(f"Pip wheel failed: {result.stderr}")
            return False
        
        print("Package built successfully with pip wheel")
        return True
        
    except subprocess.TimeoutExpired:
        print("Pip wheel timed out")
        return False
    except Exception as e:
        print(f"Pip wheel error: {e}")
        return False


def create_release(version):
    """Create release directory and copy built package"""
    print(f"Creating release for version {version}...")
    
    release_dir = Path(f"Releases/ollm-{version}")
    release_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy the entire built package structure
    dist_dir = Path("dist")
    if not dist_dir.exists():
        raise FileNotFoundError("No dist directory found after build")
    
    # Verify we have expected files
    dist_files = list(dist_dir.iterdir())
    if not dist_files:
        raise FileNotFoundError("No files found in dist directory")
    
    print(f"Found {len(dist_files)} files in dist directory")
    
    # Copy dist contents to release directory
    for item in dist_dir.iterdir():
        if item.is_file():
            shutil.copy2(item, release_dir)
            print(f"✓ Copied {item.name} to {release_dir}")
    
    # Copy source code for deployment
    src_release_dir = release_dir / "src"
    if src_release_dir.exists():
        shutil.rmtree(src_release_dir)
    shutil.copytree("src", src_release_dir)
    print(f"✓ Copied source code to {src_release_dir}")
    
    # Copy important files
    important_files = ["README.md", "pyproject.toml"]
    for file_name in important_files:
        if Path(file_name).exists():
            shutil.copy2(file_name, release_dir)
            print(f"✓ Copied {file_name} to {release_dir}")
    
    # Copy configuration files
    config_files = ["config.json", "mcp.json", "config.json.example", "mcp.json.example"]
    for config_file in config_files:
        if Path(config_file).exists():
            shutil.copy2(config_file, release_dir)
            print(f"✓ Copied {config_file} to {release_dir}")
        else:
            print(f"⚠️  {config_file} not found (skipping)")
    
    # Copy skills directory if it exists
    skills_dir = Path("skills")
    if skills_dir.exists() and skills_dir.is_dir():
        skills_release_dir = release_dir / "skills"
        if skills_release_dir.exists():
            shutil.rmtree(skills_release_dir)
        shutil.copytree(skills_dir, skills_release_dir)
        print(f"✓ Copied skills directory to {skills_release_dir}")
    else:
        print(f"⚠️  skills/ directory not found (skipping)")
    
    # Show release contents
    print(f"\nRelease contents:")
    for item in sorted(release_dir.iterdir()):
        if item.is_file():
            size = item.stat().st_size
            print(f"  📄 {item.name} ({size} bytes)")
        else:
            file_count = len(list(item.rglob("*"))) if item.is_dir() else 0
            print(f"  📁 {item.name}/ ({file_count} files)")
    
    print(f"\n✓ Release created at {release_dir}")
    return release_dir


def validate_environment():
    """Validate the build environment"""
    print("Validating build environment...")
    
    # Check Python version
    if sys.version_info < (3, 11):
        print(f"✗ Python 3.11+ required, found {sys.version_info.major}.{sys.version_info.minor}")
        return False
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # Check if we're in the right directory
    required_files = ["src/ollm/__init__.py", "pyproject.toml"]
    for file_path in required_files:
        if not Path(file_path).exists():
            print(f"✗ Required file not found: {file_path}")
            return False
        print(f"✓ Found {file_path}")
    
    # Check virtual environment status
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    venv_path = Path(".venv")
    
    if in_venv:
        print(f"✓ Running in virtual environment: {sys.prefix}")
    elif venv_path.exists():
        print(f"⚠️  Virtual environment found at .venv but not activated")
        print(f"💡 Run: source .venv/bin/activate")
        return False
    else:
        print(f"⚠️  Not in virtual environment")
        print(f"💡 Create one with: python3 -m venv .venv && source .venv/bin/activate")
        return False
    
    return True


def main():
    """Main build process"""
    try:
        print("Starting ollm build process...")
        print("=" * 50)
        
        # Validate environment
        if not validate_environment():
            print("\n❌ Environment validation failed")
            print("\n🔧 To fix this:")
            print("1. Make sure you're in the project directory")
            print("2. Activate your virtual environment:")
            print("   source .venv/bin/activate")
            print("3. If no virtual environment exists, create one:")
            print("   python3 -m venv .venv")
            print("   source .venv/bin/activate")
            print("   pip install --upgrade pip setuptools wheel")
            sys.exit(1)
        
        print("\n" + "=" * 50)
        
        # Get version from source
        version = get_version()
        print(f"Building version {version}")
        
        # Update pyproject.toml version to match
        update_pyproject_version(version)
        
        print("\n" + "-" * 30)
        
        # Build the package
        if not build_package():
            print("\n❌ Build failed - check error messages above")
            print("\nTroubleshooting tips:")
            print("1. Make sure you're in a virtual environment")
            print("2. Check internet connectivity for dependency downloads")
            print("3. Try: pip install --upgrade pip setuptools wheel build")
            print("4. Check pyproject.toml for syntax errors")
            sys.exit(1)
        
        print("\n" + "-" * 30)
        
        # Create release
        release_dir = create_release(version)
        
        print("\n" + "=" * 50)
        print(f"✅ Build completed successfully!")
        print(f"📦 Package: {release_dir}")
        print(f"🏷️  Version: {version}")
        print(f"\nNext steps:")
        print(f"  Deploy:    ./deploy.sh")
        print(f"  Uninstall: ./uninstall.sh")
        print("=" * 50)
        
    except KeyboardInterrupt:
        print("\n\n❌ Build interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
