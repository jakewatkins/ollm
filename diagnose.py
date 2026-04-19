#!/usr/bin/env python3
"""
Diagnostic script to troubleshoot ollm build issues
"""
import subprocess
import sys
from pathlib import Path

def check_python_environment():
    print("=== Python Environment ===")
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Virtual environment: {hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)}")
    if hasattr(sys, 'prefix'):
        print(f"Python prefix: {sys.prefix}")
    print()

def check_required_files():
    print("=== Required Files ===")
    required_files = ["src/ollm/__init__.py", "pyproject.toml", "README.md"]
    for file_path in required_files:
        exists = Path(file_path).exists()
        print(f"{'✓' if exists else '✗'} {file_path}")
    print()

def check_dependencies():
    print("=== Build Dependencies ===")
    required_packages = ["setuptools", "wheel", "build"]
    
    for package in required_packages:
        try:
            result = subprocess.run([sys.executable, "-c", f"import {package}; print({package}.__version__)"], 
                                 capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"✓ {package}: {version}")
            else:
                print(f"✗ {package}: not found")
        except Exception as e:
            print(f"✗ {package}: error - {e}")
    print()

def check_pip():
    print("=== Pip Status ===")
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "--version"], 
                             capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✓ pip: {result.stdout.strip()}")
        else:
            print(f"✗ pip: error - {result.stderr}")
    except Exception as e:
        print(f"✗ pip: error - {e}")
    print()

def check_network():
    print("=== Network Connectivity ===")
    try:
        result = subprocess.run([sys.executable, "-c", 
                               "import urllib.request; urllib.request.urlopen('https://pypi.org', timeout=10)"],
                             capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            print("✓ PyPI connectivity: OK")
        else:
            print("✗ PyPI connectivity: Failed")
    except Exception as e:
        print(f"✗ PyPI connectivity: error - {e}")
    print()

def main():
    print("🔍 OLLM Build Diagnostics")
    print("=" * 50)
    
    check_python_environment()
    check_required_files()
    check_dependencies()
    check_pip()
    check_network()
    
    print("=== Recommendations ===")
    print("If build is hanging, try:")
    print("1. Upgrade pip: python -m pip install --upgrade pip")
    print("2. Install build tools: pip install --upgrade setuptools wheel build")
    print("3. Clear pip cache: pip cache purge")
    print("4. Check firewall/proxy settings")
    print("5. Run build with timeout: timeout 300 python build.py")

if __name__ == "__main__":
    main()