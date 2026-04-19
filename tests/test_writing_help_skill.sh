#!/bin/bash

# Test script for ollm writing-help skill with file attachment
# Tests the writing-help skill using the peptide blog post
# 
# This script runs the DEVELOPMENT version of ollm directly from source
# without requiring installation or deployment

set -e  # Exit on any error

echo "🧪 Testing ollm writing-help skill with file attachment"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Test configuration
TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$TEST_DIR")"
TEST_FILE="$TEST_DIR/peptide-trap.md"
OUTPUT_FILE="$TEST_DIR/writing_test_output.txt"
LOG_FILE="$TEST_DIR/writing_test.log"

# Setup command to run development version directly
# This bypasses any installed version by running from source directory  
run_ollm() {
    # Force use of development version by removing site-packages from path
    (cd "$PROJECT_ROOT" && python -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT/src')

# Remove any site-packages paths that might contain ollm
filtered_path = []
for p in sys.path:
    if 'site-packages' in p or 'dist-packages' in p:
        continue
    filtered_path.append(p)
sys.path = filtered_path

# Import and run the main function
from ollm.__main__ import main
main()
" "$@")
}

OLLM_CMD="run_ollm"

# Function to print status
print_status() {
    local status=$1
    local message=$2
    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✅ $message${NC}"
    elif [ "$status" = "FAIL" ]; then
        echo -e "${RED}❌ $message${NC}"
        exit 1
    elif [ "$status" = "INFO" ]; then
        echo -e "${YELLOW}ℹ️  $message${NC}"
    fi
}

# Function to cleanup test files (optional)
cleanup() {
    print_status "INFO" "Test completed. Output files preserved for review:"
    echo "  Output: $OUTPUT_FILE"
    echo "  Logs: $LOG_FILE" 
    echo ""
    echo "To clean up manually, run:"
    echo "  rm -f \"$OUTPUT_FILE\" \"$LOG_FILE\""
}

# Note: Not automatically cleaning up output files for debugging
# trap cleanup EXIT

print_status "INFO" "Starting ollm writing-help skill test"

# Verify prerequisites
print_status "INFO" "Checking prerequisites..."

if [ ! -f "$TEST_FILE" ]; then
    print_status "FAIL" "Test file not found: $TEST_FILE"
fi

# Check if we can run the development version
# First, test if we can import the development version correctly
DEV_VERSION_CHECK=$(cd "$PROJECT_ROOT" && python -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT/src')

# Remove any site-packages paths that might contain ollm
filtered_path = []
for p in sys.path:
    if 'site-packages' in p or 'dist-packages' in p:
        continue
    filtered_path.append(p)
sys.path = filtered_path

import ollm
print(ollm.__version__)
" 2>/dev/null || echo "unknown")

if [ "$DEV_VERSION_CHECK" != "1.2.0" ]; then
    print_status "FAIL" "Cannot load development version correctly. Got version: $DEV_VERSION_CHECK"
    print_status "INFO" "This might be due to an installed ollm package conflicting."
    print_status "INFO" "Consider running: pip uninstall ollm"
    exit 1
fi

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/version &> /dev/null; then
    print_status "FAIL" "Ollama server not reachable. Please start Ollama:"
    echo "  ollama serve"
    exit 1
fi

# Check if models are available
echo "Available models:"
run_ollm --listModels || {
    print_status "FAIL" "No models available. Please pull a model:"
    echo "  ollama pull llama3.2:latest"
    exit 1
}

print_status "PASS" "Prerequisites verified"

# Debug info: Show which version we're testing
print_status "INFO" "Debug: Testing ollm development version..."
echo "  Project root: $PROJECT_ROOT"
echo "  Command function: run_ollm"

# Get version from development code using the same method
DEV_VERSION=$(cd "$PROJECT_ROOT" && python -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT/src')
filtered_path = []
for p in sys.path:
    if 'site-packages' in p or 'dist-packages' in p:
        continue
    filtered_path.append(p)
sys.path = filtered_path
import ollm
print(ollm.__version__)
" 2>/dev/null || echo "unknown")

echo "  Expected version: 1.2.0"
echo "  Development version: $DEV_VERSION"

# Verify we're using the right version
if [ "$DEV_VERSION" != "1.2.0" ]; then
    print_status "FAIL" "Development version mismatch! Expected 1.2.0, got $DEV_VERSION"
fi

# Test the run function
FUNCTION_VERSION=$(run_ollm --version 2>/dev/null | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' || echo "unknown")
echo "  Function command version: $FUNCTION_VERSION"

if [ "$FUNCTION_VERSION" != "1.2.0" ]; then
    print_status "FAIL" "Function command still using wrong version! Expected 1.2.0, got $FUNCTION_VERSION"
fi

print_status "PASS" "Using development version 1.2.0"
echo ""

# Test 1: Verify writing-help skill exists
print_status "INFO" "Test 1: Verifying writing-help skill discovery..."

if [ ! -f "$PROJECT_ROOT/skills/writing-help/SKILL.md" ]; then
    print_status "FAIL" "writing-help skill not found at: $PROJECT_ROOT/skills/writing-help/SKILL.md"
fi

print_status "PASS" "writing-help skill found"

# Test 2: Basic writing-help prompt (should trigger skill)
print_status "INFO" "Test 2: Testing skill triggering with writing prompt..."

run_ollm -p "Help me improve my writing" -v 2>&1 | grep -q "writing-help" || {
    print_status "FAIL" "writing-help skill not triggered by writing prompt"
}

print_status "PASS" "writing-help skill triggers correctly"

# Test 3: File attachment with writing prompt (main test)
print_status "INFO" "Test 3: Testing file attachment with writing-help skill..."

echo "Command: run_ollm -p \"Please proofread and edit this blog post for grammar, clarity, and flow\" -f \"$TEST_FILE\" -o \"$OUTPUT_FILE\" -v"

# Run the main test
run_ollm -p "Please proofread and edit this blog post for grammar, clarity, and flow" \
     -f "$TEST_FILE" \
     -o "$OUTPUT_FILE" \
     -v 2> "$LOG_FILE" || {
    print_status "FAIL" "ollm command failed. Check log: $LOG_FILE"
    cat "$LOG_FILE"
    exit 1
}

print_status "PASS" "ollm executed successfully"

# Test 4: Verify output file was created
print_status "INFO" "Test 4: Verifying output file creation..."

if [ ! -f "$OUTPUT_FILE" ]; then
    print_status "FAIL" "Output file not created: $OUTPUT_FILE"
fi

if [ ! -s "$OUTPUT_FILE" ]; then
    print_status "FAIL" "Output file is empty: $OUTPUT_FILE"
fi

print_status "PASS" "Output file created successfully"

# Test 5: Verify file attachment was processed
print_status "INFO" "Test 5: Verifying file attachment was processed..."

# Check if the original content appears in logs (indicating file was attached)
if grep -q "Attached Files" "$LOG_FILE" 2>/dev/null; then
    print_status "PASS" "File attachment processed (found attachment marker in logs)"
elif grep -q "peptide" "$OUTPUT_FILE"; then
    print_status "PASS" "File content processed (found peptide content in output)"
else
    print_status "FAIL" "File attachment may not have been processed"
fi

# Test 6: Check for writing-related improvements
print_status "INFO" "Test 6: Checking for writing improvements in output..."

# Look for common writing improvement indicators
if grep -i -E "(grammar|spelling|clarity|flow|improve|edit|suggest)" "$OUTPUT_FILE" &> /dev/null; then
    print_status "PASS" "Output contains writing improvement suggestions"
else
    print_status "FAIL" "Output doesn't appear to contain writing improvements"
fi

# Test 7: Verify skill selection in logs
print_status "INFO" "Test 7: Verifying skill selection in verbose logs..."

if grep -q "writing-help" "$LOG_FILE" 2>/dev/null; then
    print_status "PASS" "writing-help skill was selected (found in logs)"
else
    print_status "FAIL" "writing-help skill selection not found in logs"
fi

# Display results summary
echo ""
print_status "INFO" "Test Results Summary"
echo "===================="
echo "Test file: $TEST_FILE"
echo "Output file: $OUTPUT_FILE"
echo "Log file: $LOG_FILE"
echo ""
echo "Output preview (first 3 lines):"
head -3 "$OUTPUT_FILE" 2>/dev/null || echo "(No output file)"
echo ""
echo "File sizes:"
echo "  Original: $(wc -c < "$TEST_FILE" 2>/dev/null || echo "0") bytes"
echo "  Output: $(wc -c < "$OUTPUT_FILE" 2>/dev/null || echo "0") bytes"
echo ""

print_status "PASS" "All tests completed successfully! 🎉"

# Show cleanup info
cleanup

echo ""
echo "To review the full output:"
echo "  cat $OUTPUT_FILE"
echo ""
echo "To review the logs:"
echo "  cat $LOG_FILE"