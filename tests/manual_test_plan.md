# Manual Smoke Test Plan

This document provides a comprehensive manual testing checklist for verifying ollm functionality before release. These tests should be run manually after automated tests pass.

## Prerequisites

1. Install ollm in development mode:
   ```bash
   # Make sure you're in the ollm project root directory
   cd /path/to/ollm  # or wherever you cloned the repository
   
   # Install in editable/development mode with dev dependencies
   # Note: Use single quotes for zsh shell compatibility
   pip install -e '.[dev]'
   
   # Alternative commands if the above fails:
   pip install -e .                    # Install without dev deps
   pip install -r requirements-dev.txt # Then install dev deps separately (if file exists)
   ```

2. **Configuration Setup** (automatic with improved path resolution):
   - ollm now automatically finds config files via environment variables or fallbacks
   - Set `OLLM_CONFIG=path/to/config.json` for custom config location
   - Falls back to install directory, home directory, then packaged defaults
   
3. Ensure Ollama is running: `ollama serve`
4. Have at least one model available: `ollama pull llama3.2:latest`

## Test Suite

### 1. Basic CLI Functionality

#### 1.1 Command Help and Model Listing
```bash
# Test help output
ollm --help

# Test model listing
ollm --listModels
```

**Expected**: Help shows all CLI options, model listing shows available Ollama models

#### 1.2 Interactive Input (-p flag)
```bash
# Test interactive prompt
ollm -p "What is 2 + 2?"
```

**Expected**: Response about 2+2=4, conversation flows naturally

#### 1.3 Prompt File Input (-pf flag)
```bash
# Create test prompt file
echo "Explain quantum computing in simple terms" > prompt.txt

# Test file input
ollm -pf prompt.txt
```

**Expected**: Loads prompt from file, provides quantum computing explanation

#### 1.4 Stdin Input
```bash
# Test stdin input
echo "What is the capital of France?" | ollm
```

**Expected**: Reads from stdin, responds with Paris

### 2. Configuration and Model Selection

#### 2.1 Model Selection
```bash
# Test explicit model selection
ollm -m llama3.2:latest -p "Hello world"
```

**Expected**: Uses specified model, confirms model in verbose output

#### 2.2 Config File Loading and Resolution
```bash
# Test automatic config resolution (should work without explicit config)
ollm --listModels

# Test with explicit config file
ollm -c /path/to/config.json -p "Test custom config"

# Test OLLM_CONFIG environment variable
export OLLM_CONFIG=/path/to/my-config.json
ollm -p "Test environment variable config"

# Test config file in home directory
cp config.json ~/config.json
unset OLLM_CONFIG  
ollm -p "Test home directory config"
```

**Expected**: Config loading works in all scenarios, with proper fallback order

### 3. Skills System

#### 3.1 Skill Discovery and Selection
```bash
# Test with skills that should trigger
ollm -p "I need help analyzing this CSV data" -v
```

**Expected**: Verbose output shows skill selection (data-analysis skill if available)

#### 3.2 No Skills Available Scenario
```bash
# Test with skills disabled
OLLM_SKILLS_DIR=/nonexistent ollm -p "Hello world"
```

**Expected**: Works normally without skills, no skill-related errors

### 4. Script Execution

#### 4.1 Script Writing Capability  
```bash
# Test script generation request
ollm -p "Write a Python script that calculates the factorial of 10"
```

**Expected**: Generates Python script, potentially executes if script execution skill available

#### 4.2 Script Execution with Docker
```bash
# Test script execution (requires Docker)
ollm -p "Run this Python code: print('Hello from Docker!')"
```

**Expected**: If script execution available, runs code in Docker and shows output

### 5. Output and Logging

#### 5.1 Output File Creation
```bash
# Test output file
ollm -p "Explain machine learning" -o output.txt

# Verify output file
cat output.txt
```

**Expected**: Creates output.txt with full conversation

#### 5.2 Verbose Logging
```bash
# Test verbose mode
ollm -p "Simple question" -v
```

**Expected**: Shows detailed logging including model selection, skill scoring, turn counts

#### 5.3 Log File Generation
```bash
# Test log file 
ollm -p "Test logging" --log-file debug.log

# Check log file
tail debug.log
```

**Expected**: Creates debug.log with detailed debugging information

### 6. Error Handling and Edge Cases

#### 6.1 Invalid Model Handling
```bash
# Test invalid model
ollm -m nonexistent-model -p "Hello"
```

**Expected**: Clear error message about model not available

#### 6.2 Ollama Connection Error
```bash
# Stop Ollama temporarily
ollama stop

# Test connection error
ollm -p "Test connection"

# Restart Ollama
ollama serve
```

**Expected**: Clear error about inability to connect to Ollama

#### 6.3 Resource Limits
```bash
# Test very long conversation to hit limits
ollm -p "Let's have a very long conversation about everything"
# Continue responding until max turns hit
```

**Expected**: Stops at maxTurns limit with clear message

### 7. Cross-Platform Compatibility

#### 7.1 Path Handling (Windows/macOS/Linux)
```bash
# Test path resolution
ollm -p "What is my install directory?" -v
```

**Expected**: Shows correct install path for current platform

#### 7.2 Docker Integration
```bash
# Verify Docker connectivity
docker ps
ollm -p "Can you run a simple Python calculation?"
```

**Expected**: Docker commands work, script execution uses Docker if available

### 8. Performance and Stability

#### 8.1 Memory Usage
```bash
# Monitor memory during execution
top -p $(pgrep ollm) &
ollm -p "Generate a long story about space exploration"
```

**Expected**: Memory usage remains reasonable, no memory leaks

#### 8.2 Concurrent Usage
```bash
# Test multiple instances (in separate terminals)
ollm -p "Question 1" &
ollm -p "Question 2" &
wait
```

**Expected**: Both instances work without interference

### 9. Integration with External Tools

#### 9.1 MCP Server Integration (if available)
```bash
# Test with MCP server if configured
ollm -p "Help me search for something" -v
```

**Expected**: Shows MCP server detection in verbose output

#### 9.2 Development vs Production Install
```bash
# Test development install  
pip install -e .
which ollm

# Test production install
pip install ollm  
which ollm
```

**Expected**: Both installation methods work, command available in both cases

## Checklist for Each Test

For each test above, verify:

- [ ] **No Python exceptions or stack traces**
- [ ] **Clear error messages for failures**  
- [ ] **Reasonable response times (<30s for simple queries)**
- [ ] **Proper cleanup of temporary files**
- [ ] **Consistent behavior across multiple runs**

## Success Criteria

All tests must pass with:
✅ No crashes or unhandled exceptions  
✅ Appropriate error messages for expected failures
✅ Consistent performance and behavior
✅ Proper resource cleanup
✅ Cross-platform compatibility confirmed

## Failure Response

If any test fails:
1. Document the exact failure mode
2. Check relevant logs for details
3. Verify prerequisites are met
4. Re-run test to confirm reproducibility
5. File bug report with reproduction steps

---

*This test plan should be executed in full before each release to ensure ollm works correctly across all supported scenarios.*