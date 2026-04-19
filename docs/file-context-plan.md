# File Context Implementation Plan

## Overview

This document outlines the step-by-step implementation plan for adding file attachment capability to `ollm`. The plan includes development phases, testing strategies, and validation criteria.

## Implementation Phases

### Phase 1: Core CLI Implementation

**Estimated Time:** 2-3 hours

#### 1.1 Update CLI Parameter Parsing

**File:** `src/ollm/cli.py`

**Changes:**
- Add `files` parameter to main() function
- Add validation for file parameter combinations
- Implement `_append_file_attachments()` function
- Add comprehensive error handling

```python
files: Annotated[
    Optional[List[Path]], 
    typer.Option("-f", "--file", help="Attach text/markdown files to context")
] = None,
```

#### 1.2 File Processing Logic

**New Function:** `_append_file_attachments()`

**Requirements:**
- Read multiple files sequentially
- Validate file types and encoding
- Build formatted attachment string
- Handle errors gracefully
- Log file processing activities

**Error Scenarios to Handle:**
- File not found
- Permission denied
- Unicode decode errors
- Unsupported file types
- Empty files

#### 1.3 Integration with Existing Flow

**Modification Points:**
- `_get_prompt_content()` flow
- Call `_append_file_attachments()` after getting base prompt
- Pass enhanced prompt to `app.process_prompt()`

### Phase 2: Testing Infrastructure

**Estimated Time:** 3-4 hours

#### 2.1 Unit Test Implementation

**File:** `tests/test_file_attachment.py`

**Test Functions:**
```python
def test_append_file_attachments_single_file()
def test_append_file_attachments_multiple_files()
def test_append_file_attachments_empty_file()
def test_append_file_attachments_missing_file()
def test_append_file_attachments_permission_denied()
def test_append_file_attachments_unsupported_type()
def test_append_file_attachments_unicode_error()
def test_append_file_attachments_formatting()
```

#### 2.2 Integration Test Implementation

**File:** `tests/test_cli_integration.py`

**Test Functions:**
```python
def test_cli_single_file_attachment()
def test_cli_multiple_files()
def test_cli_files_with_output()
def test_cli_files_with_model()
def test_cli_files_with_verbose()
def test_cli_files_error_handling()
def test_cli_files_with_skills()
```

#### 2.3 Test Data Setup

**Directory:** `tests/fixtures/file_attachment/`

**Test Files:**
- `sample.txt` - Basic text file
- `sample.md` - Markdown with formatting
- `sample.json` - Valid JSON configuration
- `sample.yaml` - YAML configuration
- `empty.txt` - Empty file for edge case testing
- `large_file.txt` - Large file for performance testing
- `binary.pdf` - Binary file for type validation
- `unicode.txt` - File with Unicode characters

### Phase 3: End-to-End Validation

**Estimated Time:** 2-3 hours

#### 3.1 Skills Integration Testing

**Test Scenarios:**
- File attachment with research skill
- File attachment with writing skill
- File attachment with data analysis skill
- File attachment with no skill selected

**Validation Points:**
- Skills receive complete context
- File content is accessible in skill instructions
- Script execution can reference file content
- Tool calls work correctly with file context

#### 3.2 Performance Testing

**Test Cases:**
- Single small file (< 1KB)
- Multiple small files (5-10 files)
- Single large file (> 100KB)
- Multiple large files
- Memory usage monitoring
- Processing time measurement

#### 3.3 Error Recovery Testing

**Test Cases:**
- Mixed valid/invalid files
- Network drive files
- Symbolic links
- Files modified during processing
- Permission changes during processing

## Automated Testing Plan

### Test Environment Setup

```bash
# Create virtual environment and install dependencies
python -m venv .test-env
source .test-env/bin/activate
pip install -e .
pip install pytest pytest-cov

# Setup test fixtures
mkdir -p tests/fixtures/file_attachment
```

### Test Execution Strategy

```bash
# Unit tests only
pytest tests/test_file_attachment.py -v

# Integration tests only  
pytest tests/test_cli_integration.py -v

# All file attachment tests
pytest tests/ -k "file_attachment" -v

# Coverage reporting
pytest tests/ -k "file_attachment" --cov=ollm.cli --cov-report=html
```

### Continuous Integration

**GitHub Actions Workflow:**

```yaml
name: File Attachment Tests
on:
  pull_request:
    paths:
      - 'src/ollm/cli.py'
      - 'tests/test_file_attachment.py'
      - 'tests/test_cli_integration.py'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v3
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -e .[test]
      - name: Run file attachment tests
        run: pytest tests/ -k "file_attachment" --cov=ollm.cli
```

### Automated Test Checklist

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Code coverage > 90% for new code
- [ ] Error handling tests validate all scenarios
- [ ] Performance tests complete within acceptable time
- [ ] Memory usage stays within reasonable bounds

## Manual Testing Plan

### Test Environment Requirements

- Python virtual environment with ollm installed
- Ollama server running locally
- Test files prepared in various formats
- Different terminal environments (bash, zsh, PowerShell)

### Manual Test Cases

#### TC1: Basic Single File Attachment

**Objective:** Verify single file attachment works correctly

**Steps:**
1. Create test file: `echo "Test content" > test.txt`
2. Run: `ollm -p "Summarize this content" -f test.txt`
3. Verify output contains prompt and file content
4. Check formatting matches specification

**Expected Result:**
```text
Summarizing: Test content

---

**Attached Files:**

**test.txt:**
```
Test content
```
```

**Pass Criteria:**
- File content appears correctly formatted
- Prompt processing completes successfully
- Output is coherent and references file content

#### TC2: Multiple File Attachments

**Objective:** Verify multiple files can be attached and processed

**Steps:**
1. Create multiple test files with different content
2. Run: `ollm -p "Compare these files" -f file1.txt -f file2.md -f config.json`
3. Verify all files appear in correct format
4. Check processing handles multiple files correctly

**Pass Criteria:**
- All files appear with correct formatting
- Files maintain proper separation
- Content is processed coherently

#### TC3: File Types Validation

**Objective:** Verify supported and unsupported file types

**Steps:**
1. Test supported types: `.txt`, `.md`, `.json`, `.yaml`
2. Test unsupported types: `.pdf`, `.jpg`, `.exe`
3. Verify warnings for unsupported types
4. Verify processing continues with supported files

**Pass Criteria:**
- Supported files process correctly
- Unsupported files generate warnings
- Processing continues with valid files

#### TC4: Error Handling

**Objective:** Verify error scenarios are handled gracefully

**Steps:**
1. Test non-existent file: `ollm -p "test" -f nonexistent.txt`
2. Test permission denied (create protected file)
3. Test binary file with invalid UTF-8
4. Verify appropriate error messages

**Pass Criteria:**
- Clear error messages for each scenario
- Application exits gracefully with appropriate codes
- No crashes or undefined behavior

#### TC5: Integration with Skills

**Objective:** Verify file attachments work with skills system

**Steps:**
1. Run: `ollm -p "Research this topic" -f research-data.md`
2. Verify research skill is activated
3. Verify skill can reference attached file content
4. Check that skill instructions use file context

**Pass Criteria:**
- Appropriate skill is selected
- Skill references file content accurately
- Processing completes successfully
- Output demonstrates file context usage

#### TC6: Large File Handling

**Objective:** Test performance with larger files

**Steps:**
1. Create large test file (>100KB): `base64 /dev/urandom | head -c 100000 > large.txt`
2. Run: `ollm -p "Analyze this data" -f large.txt`
3. Monitor memory usage and processing time
4. Verify successful completion

**Pass Criteria:**
- Processing completes without errors
- Memory usage remains reasonable
- Response time is acceptable (<30 seconds)
- Output quality is maintained

#### TC7: Command Line Parameter Combinations

**Objective:** Verify file attachments work with other parameters

**Test Matrix:**
```bash
# With output file
ollm -p "test" -f test.txt -o output.md

# With model selection
ollm -p "test" -f test.txt -m qwen3-coder:30b

# With verbose logging
ollm -p "test" -f test.txt -v

# With config file
ollm -p "test" -f test.txt -c custom-config.json

# Multiple combinations
ollm -p "test" -f file1.txt -f file2.md -o result.txt -v
```

**Pass Criteria:**
- All parameter combinations work correctly
- No conflicts between parameters
- Expected behavior for each combination

### Manual Testing Checklist

#### Pre-Testing Setup
- [ ] Virtual environment activated
- [ ] ollm installed in development mode
- [ ] Test files created with various content types
- [ ] Ollama server running and accessible

#### Basic Functionality
- [ ] Single file attachment works
- [ ] Multiple file attachments work
- [ ] File content appears in correct format
- [ ] Prompt processing completes successfully

#### File Type Validation
- [ ] Text files (.txt) process correctly
- [ ] Markdown files (.md) process correctly
- [ ] JSON files (.json) process correctly
- [ ] YAML files (.yaml, .yml) process correctly
- [ ] Unsupported files generate appropriate warnings
- [ ] Binary files are rejected gracefully

#### Error Scenarios
- [ ] Non-existent files produce proper error messages
- [ ] Permission denied errors handled correctly
- [ ] Unicode decode errors handled properly
- [ ] Application exits gracefully on errors

#### Integration Testing
- [ ] Works with research skill
- [ ] Works with writing skill
- [ ] Works with no skill selected
- [ ] Skills can reference file content
- [ ] Tool calls work with file context

#### Performance Testing
- [ ] Small files process quickly
- [ ] Large files complete within reasonable time
- [ ] Memory usage stays within bounds
- [ ] Multiple files don't cause performance issues

#### Parameter Combinations
- [ ] Works with -o/--output
- [ ] Works with -m/--model
- [ ] Works with -v/--verbose
- [ ] Works with -c/--config
- [ ] Works with prompt from stdin
- [ ] Works with -pf/--prompt-file

#### Edge Cases
- [ ] Empty files handled correctly
- [ ] Files with Unicode characters work
- [ ] Very long filenames work
- [ ] Files in subdirectories work
- [ ] Relative and absolute paths work

## Validation Criteria

### Functional Requirements
- [ ] All supported file types can be attached
- [ ] Multiple files can be attached simultaneously
- [ ] File content is correctly formatted in prompt
- [ ] Error handling works for all error scenarios
- [ ] Integration with skills system is seamless

### Performance Requirements
- [ ] Single file attachment adds <100ms overhead
- [ ] Multiple files scale linearly
- [ ] Memory usage is reasonable for expected file sizes
- [ ] No memory leaks during file processing

### Quality Requirements
- [ ] Code coverage >90% for new functionality
- [ ] All automated tests pass
- [ ] Manual testing checklist completed
- [ ] Documentation is accurate and complete
- [ ] Error messages are clear and actionable

### Security Requirements
- [ ] Only text files are processed
- [ ] No path traversal vulnerabilities
- [ ] File permissions are respected
- [ ] No arbitrary code execution risks

## Release Readiness Checklist

### Code Quality
- [ ] Implementation complete and reviewed
- [ ] All tests passing (unit + integration)
- [ ] Code coverage meets requirements
- [ ] Documentation updated
- [ ] Error handling comprehensive

### Testing Complete
- [ ] All automated tests pass
- [ ] Manual testing checklist completed
- [ ] Performance testing acceptable
- [ ] Edge cases validated
- [ ] Integration testing successful

### User Experience
- [ ] CLI interface intuitive
- [ ] Error messages helpful
- [ ] File format output clear
- [ ] Skills integration seamless
- [ ] Documentation accurate

### Deployment Ready
- [ ] No breaking changes to existing functionality
- [ ] Backward compatibility maintained
- [ ] Configuration requirements documented
- [ ] Installation instructions updated
- [ ] Release notes prepared

## Post-Implementation Tasks

### Monitoring
- Track usage patterns of file attachment feature
- Monitor performance impact on typical workflows
- Collect user feedback on file format and experience

### Future Enhancements
- Evaluate adding binary file support
- Consider remote file URL support
- Assess need for file size configuration limits
- Plan directory attachment feature

### Maintenance
- Regular testing with new Ollama versions
- Update supported file type list based on usage
- Performance optimization based on real-world usage patterns