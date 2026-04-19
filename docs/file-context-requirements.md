# File Context Requirements

## Overview

This document outlines the requirements for adding file attachment capability to `ollm`, allowing users to include text and markdown files as context in their prompts.

## Feature Description

Users should be able to attach one or more text-based files to their prompts, providing additional context for the LLM to reference during processing. This feature enhances `ollm`'s capability to work with existing documents, configuration files, code, and other text-based assets.

## Command Line Interface

### Parameter Design

```bash
-f, --file PATH    Attach text/markdown files to context (can be used multiple times)
```

**Alternative considered:** `-a, --attach` (original proposal)
**Decision:** Using `-f, --file` for consistency with common CLI patterns

### Usage Examples

```bash
# Single file attachment
ollm -p "Please review my essay" -f essay.md

# Multiple files
ollm -p "Compare these configs" -f config1.yaml -f config2.yaml

# With output file
ollm -p "Analyze the data" -f data.txt -o analysis.md

# With specific model
ollm -p "Code review please" -f main.py -f utils.py -m qwen3-coder:30b

# Combined with other flags
ollm -p "Fix bugs in my code" -f src/main.py -f tests/test_main.py -v -o fix-report.md
```

### Parameter Validation

- Multiple `-f/--file` parameters are allowed and encouraged
- Files must exist and be readable
- Files must be text-based (see supported file types below)
- Can be combined with all existing parameters
- No conflicts with existing CLI parameters

## File Content Integration

### Format Structure

Attached files will be appended to the user's prompt using this format:

```text
{user_prompt}

---

**Attached Files:**

**{filename1}:**
```
{file1_content}
```

**{filename2}:**
```
{file2_content}
```
```

### Example Output

For command: `ollm -p "Review this code" -f utils.py -f config.yaml`

```text
Review this code

---

**Attached Files:**

**utils.py:**
```
def helper_function():
    return "Hello World"
```

**config.yaml:**
```
database:
  host: localhost
  port: 5432
```
```

### Design Rationale

1. **Clear Separation:** The `---` separator clearly distinguishes user prompt from attachments
2. **Multiple File Support:** Each file gets its own labeled section
3. **Filename Context:** Including filenames helps the LLM understand file relationships
4. **Code Block Format:** Using triple backticks maintains proper text formatting
5. **Extensible:** Format can accommodate future enhancements

## Integration with Existing Architecture

### Compatibility with Skills System

File attachments integrate seamlessly with the existing skills system:

1. **No Architecture Changes:** Files become part of the user message content
2. **Skills Can Reference Files:** Skills can reference attached files in their instructions
3. **Script Execution Works:** Skills with `scriptExecution: true` can access file content
4. **Context Preservation:** Full context (prompt + files) flows through skill selection

### Message Flow

```text
1. CLI parses -f parameters and reads file contents
2. CLI builds enhanced prompt (original + file attachments)
3. App.process_prompt() receives complete prompt string
4. Skills system selects appropriate skill based on enhanced prompt
5. AgentLoop.run() processes with full context
```

### Example with Skills

Command: `ollm -p "Research this competitor" -f competitor-info.md`

The research skill would receive:
```text
Research this competitor

---

**Attached Files:**

**competitor-info.md:**
```
[Full competitor info content]
```
```

The skill can then reference: "Based on the attached competitor-info.md file..." in its instructions.

## Supported File Types

### Initial Implementation

- `.txt` - Plain text files
- `.md`, `.markdown` - Markdown documents
- `.json` - JSON configuration/data files
- `.yaml`, `.yml` - YAML configuration files

### Potential Future Extensions

- `.py`, `.js`, `.ts`, `.cs` - Source code files
- `.log` - Log files
- `.sql` - SQL scripts
- `.xml` - XML configuration files

### File Type Validation

- Check file extension against allowed list
- Validate UTF-8 encoding
- Warn about unsupported types and skip them
- Continue processing with supported files

## Implementation Details

### File Processing Function

```python
def _append_file_attachments(prompt_content: str, files: List[Path]) -> str:
    """Append file attachments to prompt content.
    
    Args:
        prompt_content: Original user prompt
        files: List of file paths to attach
        
    Returns:
        Enhanced prompt with file attachments
        
    Raises:
        typer.Exit: On file reading errors
    """
```

### Error Handling

| Error Type | Behavior |
|------------|----------|
| File not found | Print error, exit with code 1 |
| Permission denied | Print error, exit with code 1 |
| Unicode decode error | Print error, exit with code 1 |
| Unsupported file type | Print warning, skip file, continue |
| Empty file | Process normally (empty content) |

### Memory Considerations

- No explicit file size limits in initial implementation
- Files are read entirely into memory
- Consider adding size warnings for large files (>1MB) in future
- Multiple large files could impact memory usage

## Testing Strategy

### Unit Tests

```python
# Test file attachment function
def test_append_file_attachments_single_file()
def test_append_file_attachments_multiple_files()
def test_append_file_attachments_empty_file()
def test_append_file_attachments_missing_file()
def test_append_file_attachments_unsupported_type()
```

### Integration Tests

```python
# Test CLI parameter parsing
def test_cli_multiple_files()
def test_cli_files_with_other_params()

# Test end-to-end flow
def test_file_attachment_with_skills()
def test_file_attachment_output_format()
```

### Manual Test Cases

1. Single text file attachment
2. Multiple files of different types
3. Large file handling
4. Non-existent file error
5. Permission denied error
6. Mixed valid/invalid files
7. Integration with research skill
8. Integration with writing skill

## Future Enhancements

### Phase 2 Considerations

1. **Binary File Support:** PDF, images via text extraction
2. **Size Limits:** Configurable maximum file size
3. **Remote Files:** HTTP/HTTPS URL support
4. **Archive Support:** ZIP file extraction
5. **Directory Support:** `-d/--directory` to attach all files in directory
6. **File Filtering:** Glob patterns for selective attachment
7. **Content Preprocessing:** Syntax highlighting, line numbers
8. **Caching:** Cache large files to avoid re-reading

### Configuration Options

Potential future config.json settings:

```json
{
  "fileAttachment": {
    "maxFileSize": "10MB",
    "maxTotalSize": "50MB",
    "allowedExtensions": [".txt", ".md", ".json", ".yaml"],
    "enableRemoteFiles": false,
    "enableBinaryExtraction": false
  }
}
```

## Security Considerations

### Current Implementation

- Only local file system access
- Read-only operations
- File type restrictions
- UTF-8 text validation

### Future Security Reviews

- Path traversal prevention (if relative paths added)
- Remote file validation (if URL support added)
- Content sanitization (if binary extraction added)
- File size limits (if large file support added)

## Performance Impact

### Expected Impact

- **Minimal for small files:** Text files <100KB should have negligible impact
- **Linear scaling:** Performance scales with total file size
- **Memory usage:** Files stored in memory during processing
- **I/O overhead:** File reading happens at CLI startup

### Monitoring Points

- Total prompt size after file attachment
- File reading time
- Memory usage with multiple large files
- Impact on model processing time

## Backward Compatibility

- **Fully backward compatible:** No changes to existing CLI behavior
- **Optional feature:** Files only attached when `-f/--file` is used
- **No config changes:** Works with existing configuration
- **Skills compatibility:** Existing skills continue to work unchanged

