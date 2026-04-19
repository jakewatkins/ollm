#!/bin/bash
#
# Build script for ollm (shell version)
# Alternative to build.py - calls the Python build script
#

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if in virtual environment
check_venv() {
    if [[ -z "$VIRTUAL_ENV" ]]; then
        if [[ -d ".venv" ]]; then
            print_error "Virtual environment found but not activated!"
            print_info "Run: source .venv/bin/activate"
        else
            print_error "No virtual environment detected!"
            print_info "Create one with: python3 -m venv .venv && source .venv/bin/activate"
        fi
        return 1
    else
        print_success "Virtual environment active: $VIRTUAL_ENV"
        return 0
    fi
}

# Check if Python build script exists
if [[ ! -f "build.py" ]]; then
    print_error "build.py not found!"
    exit 1
fi

print_info "Starting ollm build process (shell wrapper)..."

# Check virtual environment
if ! check_venv; then
    exit 1
fi

# Execute the Python build script
if python3 build.py; then
    print_success "Build completed successfully!"
else
    print_error "Build failed!"
    exit 1
fi