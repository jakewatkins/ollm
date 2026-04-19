#!/usr/bin/env python3
"""
Alternative build script using setuptools directly (fallback approach)
"""
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
    
    import ast
    with open(init_file, "r") as f:
        tree = ast.parse(f.read())
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__version__":
                    return ast.literal_eval(node.value)
    
    raise ValueError("Could not find __version__ in __init__.py")

def clean_build():
    """Clean previous build artifacts"""
    dirs_to_clean = ["build", "dist", "src/ollm.egg-info", "*.egg-info"]
    for pattern in dirs_to_clean:
        if '*' in pattern:
            # Handle glob patterns
            import glob
            for path in glob.glob(pattern):
                if os.path.isdir(path):
                    shutil.rmtree(path)
                    print(f"Cleaned {path}")
        elif os.path.exists(pattern):
            if os.path.isdir(pattern):
                shutil.rmtree(pattern)
            else:
                os.remove(pattern)
            print(f"Cleaned {pattern}")

def build_setuptools():
    """Build using setuptools directly"""
    print("Building with setuptools...")
    
    try:
        # Build source distribution
        print("Building source distribution...")
        result = subprocess.run([
            sys.executable, "setup.py", "sdist"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print(f"sdist failed: {result.stderr}")
            # Try alternative approach
            print("Trying pip wheel...")
            return build_with_pip()
        
        # Build wheel
        print("Building wheel...")
        result = subprocess.run([
            sys.executable, "setup.py", "bdist_wheel"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print(f"bdist_wheel failed: {result.stderr}")
            return build_with_pip()
        
        print("Build completed with setuptools")
        return True
        
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("setuptools approach failed, trying pip...")
        return build_with_pip()

def build_with_pip():
    """Build using pip wheel"""
    print("Building with pip wheel...")
    
    try:
        # Install current package in development mode first
        result = subprocess.run([
            sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "-w", "dist"
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode != 0:
            print(f"pip wheel failed: {result.stderr}")
            return False
        
        print("Build completed with pip wheel")
        return True
        
    except subprocess.TimeoutExpired:
        print("pip wheel timed out")
        return False

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

def main():
    """Main alternative build process"""
    try:
        print("🔧 Alternative Build Process")
        print("=" * 40)
        
        # Get version
        version = get_version()
        print(f"Version: {version}")
        
        # Clean previous builds
        clean_build()
        
        # Create setup.py if needed
        create_setup_py()
        
        # Try building
        success = False
        
        # Method 1: Try setuptools directly  
        if build_setuptools():
            success = True
        # Method 2: Already tried in build_setuptools if it failed
        
        if not success:
            print("❌ All build methods failed")
            print("\nManual build steps you can try:")
            print("1. pip install -e .")
            print("2. python -m pip wheel . --no-deps -w dist")
            print("3. Check for conflicting packages")
            return False
        
        # Check if files were created
        dist_dir = Path("dist")
        if not dist_dir.exists() or not list(dist_dir.glob("*")):
            print("❌ No files created in dist/")
            return False
        
        print(f"\n✅ Build successful!")
        print("Created files:")
        for file in dist_dir.iterdir():
            print(f"  📦 {file.name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Build failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)