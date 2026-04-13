# Manual Smoke Test Plan

This document provides a comprehensive manual testing checklist for verifying ollm functionality before release. These tests should be run manually after automated tests pass.

## Prerequisites

1. Install ollm in clean environment: `pip install -e ".[dev]"`
2. Ensure Ollama is running: `ollama serve`
3. Have at least one model available: `ollama pull llama3.2:latest`
4. Create test directory: `mkdir -p ~/tmp/ollm-test && cd ~/tmp/ollm-test`

## Test Suite

### 1. Basic CLI Functionality

#### 1.1 Command Help and Version
```bash
# Test help output
ollm --help

# Test version display  
ollm --version
```

**Expected**: Help shows all options, version shows current version

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

#### 2.2 Config File Loading
```bash
# Create test config
cat > test-config.json << EOF
{
  "baseUrl": "http://localhost:11434",
  "agentLoop": {
    "maxTurns": 3
  }
}
EOF

# Test config loading
OLLM_CONFIG=test-config.json ollm -p "Test config loading" -v
```

**Expected**: Loads config, respects maxTurns=3 in verbose output

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