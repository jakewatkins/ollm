#!/bin/bash
#
# Uninstall script for ollm
# Removes ollm from ~/apps/ollm and cleans up PATH entries
#

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APPS_DIR="$HOME/apps"
INSTALL_DIR="$APPS_DIR/ollm"

# Function to print colored output
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

# Function to remove PATH entries
remove_from_path() {
    local shell_configs=()
    
    # Common shell configuration files
    [[ -f "$HOME/.zshrc" ]] && shell_configs+=("$HOME/.zshrc")
    [[ -f "$HOME/.bash_profile" ]] && shell_configs+=("$HOME/.bash_profile")
    [[ -f "$HOME/.bashrc" ]] && shell_configs+=("$HOME/.bashrc")
    [[ -f "$HOME/.profile" ]] && shell_configs+=("$HOME/.profile")
    
    local removed_from_files=0
    
    for config_file in "${shell_configs[@]}"; do
        if grep -q "export PATH.*$INSTALL_DIR" "$config_file" 2>/dev/null; then
            print_info "Removing PATH entry from $config_file"
            
            # Create a temporary file without the ollm PATH entry
            grep -v "export PATH.*$INSTALL_DIR" "$config_file" > "$config_file.tmp"
            
            # Also remove the comment line if it exists
            grep -v "# ollm installation" "$config_file.tmp" > "$config_file.tmp2"
            mv "$config_file.tmp2" "$config_file"
            rm -f "$config_file.tmp"
            
            removed_from_files=$((removed_from_files + 1))
        fi
    done
    
    if [[ $removed_from_files -gt 0 ]]; then
        print_success "Removed PATH entries from $removed_from_files file(s)"
        print_info "Please restart your shell or run 'source <shell_config_file>' to update PATH"
    else
        print_info "No PATH entries found to remove"
    fi
}

# Function to confirm uninstallation
confirm_uninstall() {
    echo
    print_warning "This will completely remove ollm from your system:"
    echo "  - Delete: $INSTALL_DIR"
    echo "  - Remove PATH entries from shell configuration files"
    echo
    
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Uninstallation cancelled"
        exit 0
    fi
}

# Main uninstall function
main() {
    print_info "ollm Uninstaller"
    echo
    
    # Check if ollm is installed
    if [[ ! -d "$INSTALL_DIR" ]]; then
        print_warning "ollm is not installed at $INSTALL_DIR"
        
        # Check if there are any PATH entries to clean up
        local has_path_entries=false
        for config in "$HOME/.zshrc" "$HOME/.bash_profile" "$HOME/.bashrc" "$HOME/.profile"; do
            if [[ -f "$config" ]] && grep -q "export PATH.*$INSTALL_DIR" "$config" 2>/dev/null; then
                has_path_entries=true
                break
            fi
        done
        
        if [[ "$has_path_entries" == "true" ]]; then
            print_info "Found PATH entries to clean up"
            remove_from_path
        else
            print_info "Nothing to uninstall"
        fi
        
        exit 0
    fi
    
    # Show current installation info
    if [[ -f "$INSTALL_DIR/ollm" ]]; then
        print_info "Current installation found at: $INSTALL_DIR"
        
        # Try to get version
        if version_output=$("$INSTALL_DIR/ollm" --version 2>/dev/null); then
            print_info "Version: $version_output"
        fi
    fi
    
    # Confirm before proceeding
    confirm_uninstall
    
    # Remove installation directory
    print_info "Removing installation directory: $INSTALL_DIR"
    if rm -rf "$INSTALL_DIR"; then
        print_success "Installation directory removed"
    else
        print_error "Failed to remove installation directory"
        exit 1
    fi
    
    # Remove PATH entries
    remove_from_path
    
    # Remove parent apps directory if it's empty
    if [[ -d "$APPS_DIR" ]] && [[ -z "$(ls -A "$APPS_DIR")" ]]; then
        print_info "Removing empty apps directory: $APPS_DIR"
        rmdir "$APPS_DIR"
    fi
    
    print_success "ollm has been successfully uninstalled!"
    print_info ""
    print_info "To complete the removal:"
    print_info "1. Restart your terminal or run 'source <shell_config>' to update PATH"
    print_info "2. Run 'hash -r' to clear command cache"
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi