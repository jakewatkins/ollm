#!/bin/bash
#
# Deploy script for ollm
# Deploys the built package to ~/apps/ollm and ensures it's in PATH
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

# Function to get version from source
get_version() {
    python3 -c "
import ast
with open('src/ollm/__init__.py', 'r') as f:
    tree = ast.parse(f.read())
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == '__version__':
                print(ast.literal_eval(node.value))
                break
"
}

# Function to check if ollm is in PATH
check_path() {
    local shell_config=""
    
    # Determine shell configuration file
    case $SHELL in
        */zsh)
            shell_config="$HOME/.zshrc"
            ;;
        */bash)
            if [[ -f "$HOME/.bash_profile" ]]; then
                shell_config="$HOME/.bash_profile"
            else
                shell_config="$HOME/.bashrc"
            fi
            ;;
        *)
            shell_config="$HOME/.profile"
            ;;
    esac
    
    # Check if PATH modification exists
    if grep -q "export PATH.*$INSTALL_DIR" "$shell_config" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to add to PATH
add_to_path() {
    local shell_config=""
    
    # Determine shell configuration file
    case $SHELL in
        */zsh)
            shell_config="$HOME/.zshrc"
            ;;
        */bash)
            if [[ -f "$HOME/.bash_profile" ]]; then
                shell_config="$HOME/.bash_profile"
            else
                shell_config="$HOME/.bashrc"
            fi
            ;;
        *)
            shell_config="$HOME/.profile"
            ;;
    esac
    
    print_info "Adding $INSTALL_DIR to PATH in $shell_config"
    
    # Add PATH export if it doesn't exist
    echo "" >> "$shell_config"
    echo "# ollm installation" >> "$shell_config"
    echo "export PATH=\"\$PATH:$INSTALL_DIR\"" >> "$shell_config"
    
    print_success "Added to PATH. Please run 'source $shell_config' or restart your shell."
}

# Main deployment function
main() {
    print_info "Starting ollm deployment..."
    
    # Check if we're in the right directory
    if [[ ! -f "src/ollm/__init__.py" ]]; then
        print_error "Must run from ollm project root directory"
        exit 1
    fi
    
    # Get version
    VERSION=$(get_version)
    if [[ -z "$VERSION" ]]; then
        print_error "Could not determine version"
        exit 1
    fi
    
    print_info "Deploying ollm version $VERSION"
    
    # Check if release exists
    RELEASE_DIR="Releases/ollm-$VERSION"
    if [[ ! -d "$RELEASE_DIR" ]]; then
        print_error "Release directory $RELEASE_DIR not found. Run ./build.py first."
        exit 1
    fi
    
    # Create apps directory if it doesn't exist
    mkdir -p "$APPS_DIR"
    
    # Remove existing installation
    if [[ -e "$INSTALL_DIR" ]]; then
        print_warning "Removing existing ollm installation at $INSTALL_DIR"
        rm -rf "$INSTALL_DIR"
        print_success "Removed existing installation"
    fi
    
    # Create installation directory
    mkdir -p "$INSTALL_DIR"
    print_success "Created installation directory: $INSTALL_DIR"
    
    # Copy release to installation directory
    print_info "Copying files to $INSTALL_DIR"
    cp -r "$RELEASE_DIR"/* "$INSTALL_DIR/"
    
    # Copy config files to user-accessible location if they exist
    if [[ -f "$INSTALL_DIR/config.json" ]]; then
        print_success "Configuration files available at $INSTALL_DIR"
        print_info "  - config.json (main configuration)"
        [[ -f "$INSTALL_DIR/config.json.example" ]] && print_info "  - config.json.example (template)"
    fi
    
    if [[ -f "$INSTALL_DIR/mcp.json" ]]; then
        print_info "  - mcp.json (MCP server configuration)"
        [[ -f "$INSTALL_DIR/mcp.json.example" ]] && print_info "  - mcp.json.example (template)"
    fi
    
    if [[ -d "$INSTALL_DIR/skills" ]]; then
        skill_count=$(find "$INSTALL_DIR/skills" -type f -name "*.md" | wc -l | tr -d ' ')
        print_info "  - skills/ directory ($skill_count skills available)"
    fi
    
    # Create virtual environment in installation directory
    print_info "Setting up virtual environment..."
    python3 -m venv "$INSTALL_DIR/venv"
    
    # Activate virtual environment and install
    source "$INSTALL_DIR/venv/bin/activate"
    
    # Find and install the wheel file
    WHEEL_FILE=$(find "$INSTALL_DIR" -name "*.whl" | head -1)
    if [[ -z "$WHEEL_FILE" ]]; then
        print_error "No wheel file found in release"
        exit 1
    fi
    
    print_info "Installing wheel: $(basename $WHEEL_FILE)"
    pip install --quiet --upgrade pip
    pip install --quiet "$WHEEL_FILE"
    
    # Create launcher script
    print_info "Creating launcher script..."
    cat > "$INSTALL_DIR/ollm" << EOF
#!/bin/bash
# ollm launcher script
source "$INSTALL_DIR/venv/bin/activate"
exec python -m ollm "\$@"
EOF
    
    chmod +x "$INSTALL_DIR/ollm"
    
    # Check and add to PATH if needed
    if ! check_path; then
        add_to_path
    else
        print_success "ollm is already in PATH"
    fi
    
    # Test installation
    print_info "Testing installation..."
    if "$INSTALL_DIR/ollm" --help > /dev/null 2>&1; then
        print_success "Installation test passed"
    else
        print_warning "Installation test failed, but files were copied"
    fi
    
    print_success "Deployment completed!"
    print_info "Installation location: $INSTALL_DIR"
    print_info "Version: $VERSION"
    print_info ""
    print_info "Usage: ollm --help"
    print_info ""
    print_info "Configuration files available at:"
    print_info "  $INSTALL_DIR/config.json"
    print_info "  $INSTALL_DIR/mcp.json" 
    [[ -d "$INSTALL_DIR/skills" ]] && print_info "  $INSTALL_DIR/skills/"
    print_info ""
    print_info "If 'ollm' command is not found, please run:"
    print_info "  source ~/.zshrc  (or your shell config file)"
    print_info "Or restart your terminal."
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi