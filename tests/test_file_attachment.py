"""Tests for file attachment functionality."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch
from typer.testing import CliRunner
import typer

from ollm.cli import _append_file_attachments, app


class TestAppendFileAttachments:
    """Test the _append_file_attachments function."""
    
    def test_append_single_file(self):
        """Test appending a single text file."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content")
            temp_file = Path(f.name)
        
        try:
            result = _append_file_attachments("Original prompt", [temp_file])
            
            expected = (
                "Original prompt\n\n---\n\n**Attached Files:**\n\n"
                f"**{temp_file.name}:**\n```\nTest content\n```\n\n"
            )
            assert result == expected
        finally:
            temp_file.unlink()  # Clean up
    
    def test_append_multiple_files(self):
        """Test appending multiple files."""
        files_data = [
            ("file1.txt", "Content 1"),
            ("file2.md", "# Markdown content"),
            ("file3.json", '{"key": "value"}')
        ]
        
        temp_files = []
        try:
            # Create temporary files
            for filename, content in files_data:
                with tempfile.NamedTemporaryFile(mode='w', suffix=Path(filename).suffix, delete=False) as f:
                    f.write(content)
                    temp_file = Path(f.name)
                    temp_file = temp_file.rename(temp_file.parent / filename)
                    temp_files.append(temp_file)
            
            result = _append_file_attachments("Test prompt", temp_files)
            
            # Verify structure
            assert "Test prompt\n\n---\n\n**Attached Files:**\n\n" in result
            assert "**file1.txt:**\n```\nContent 1\n```\n\n" in result
            assert "**file2.md:**\n```\n# Markdown content\n```\n\n" in result
            assert '**file3.json:**\n```\n{"key": "value"}\n```\n\n' in result
        
        finally:
            for f in temp_files:
                if f.exists():
                    f.unlink()
    
    def test_append_empty_file(self):
        """Test appending an empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            # Write nothing (empty file)
            temp_file = Path(f.name)
        
        try:
            result = _append_file_attachments("Prompt", [temp_file])
            
            expected = (
                "Prompt\n\n---\n\n**Attached Files:**\n\n"
                f"**{temp_file.name}:**\n```\n\n```\n\n"
            )
            assert result == expected
        finally:
            temp_file.unlink()
    
    def test_missing_file_error(self):
        """Test error handling for missing files."""
        non_existent = Path("/non/existent/file.txt")
        
        with pytest.raises(typer.Exit) as exc_info:
            _append_file_attachments("Prompt", [non_existent])
        
        assert exc_info.value.exit_code == 1
    
    @patch('sys.stderr')
    def test_unsupported_file_type_warning(self, mock_stderr):
        """Test warning for unsupported file types."""
        # Create a file with unsupported extension
        with tempfile.NamedTemporaryFile(mode='w', suffix='.exe', delete=False) as f:
            f.write("binary content")
            temp_file = Path(f.name)
        
        try:
            result = _append_file_attachments("Prompt", [temp_file])
            
            # Should return original prompt since no supported files
            assert result == "Prompt"
            
            # Should print warning (captured by mock)
            mock_stderr.write.assert_called()
        finally:
            temp_file.unlink()
    
    @patch('sys.stderr')
    def test_unicode_error_handling(self, mock_stderr):
        """Test handling of files with invalid UTF-8 encoding."""
        # Create a file with invalid UTF-8 content
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as f:
            f.write(b'\x80\x81\x82\x83')  # Invalid UTF-8 bytes
            temp_file = Path(f.name)
        
        try:
            with pytest.raises(typer.Exit) as exc_info:
                _append_file_attachments("Prompt", [temp_file])
            
            assert exc_info.value.exit_code == 1
        finally:
            temp_file.unlink()
    
    def test_no_files_provided(self):
        """Test behavior when no files are provided."""
        result = _append_file_attachments("Original prompt", [])
        assert result == "Original prompt"
    
    def test_mixed_valid_invalid_files(self):
        """Test handling of mixed valid and invalid files."""
        # Create one valid file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Valid content")
            valid_file = Path(f.name)
        
        # Use a non-existent file as invalid
        invalid_file = Path("/non/existent/file.txt")
        
        try:
            with pytest.raises(typer.Exit) as exc_info:
                _append_file_attachments("Prompt", [valid_file, invalid_file])
            
            assert exc_info.value.exit_code == 1
        finally:
            valid_file.unlink()
    
    def test_supported_file_extensions(self):
        """Test all supported file extensions."""
        extensions = ['.txt', '.md', '.markdown', '.json', '.yaml', '.yml']
        temp_files = []
        
        try:
            for ext in extensions:
                with tempfile.NamedTemporaryFile(mode='w', suffix=ext, delete=False) as f:
                    f.write(f"Content for {ext} file")
                    temp_files.append(Path(f.name))
            
            result = _append_file_attachments("Test", temp_files)
            
            # All files should be included
            assert "---" in result
            assert "**Attached Files:**" in result
            for temp_file in temp_files:
                assert f"**{temp_file.name}:**" in result
                assert f"Content for {temp_file.suffix} file" in result
        
        finally:
            for f in temp_files:
                if f.exists():
                    f.unlink()


class TestCLIIntegration:
    """Test CLI integration with file attachment."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.test_files_dir = Path(__file__).parent / "fixtures" / "file_attachment"
    
    def test_cli_single_file(self):
        """Test CLI with single file attachment."""
        test_file = self.test_files_dir / "sample.txt"
        
        # Mock the app components since we're testing CLI parsing only
        with patch('ollm.cli.get_app') as mock_app:
            mock_app_instance = mock_app.return_value
            mock_app_instance.initialize.return_value = None
            mock_app_instance.process_prompt.return_value = None
            mock_app_instance.cleanup.return_value = None
            
            result = self.runner.invoke(app, [
                "-p", "Test prompt",
                "-f", str(test_file)
            ])
            
            # Should not exit with error
            assert result.exit_code == 0
            
            # Verify process_prompt was called with enhanced content
            mock_app_instance.process_prompt.assert_called_once()
            args = mock_app_instance.process_prompt.call_args[0]
            enhanced_prompt = args[0]
            
            assert "Test prompt" in enhanced_prompt
            assert "---" in enhanced_prompt
            assert "**Attached Files:**" in enhanced_prompt
            assert "**sample.txt:**" in enhanced_prompt
    
    def test_cli_multiple_files(self):
        """Test CLI with multiple file attachments."""
        test_files = [
            self.test_files_dir / "sample.txt",
            self.test_files_dir / "sample.md"
        ]
        
        with patch('ollm.cli.get_app') as mock_app:
            mock_app_instance = mock_app.return_value
            mock_app_instance.initialize.return_value = None
            mock_app_instance.process_prompt.return_value = None
            mock_app_instance.cleanup.return_value = None
            
            result = self.runner.invoke(app, [
                "-p", "Compare files",
                "-f", str(test_files[0]),
                "-f", str(test_files[1])
            ])
            
            assert result.exit_code == 0
            
            # Verify enhanced prompt contains both files
            mock_app_instance.process_prompt.assert_called_once()
            args = mock_app_instance.process_prompt.call_args[0]
            enhanced_prompt = args[0]
            
            assert "Compare files" in enhanced_prompt
            assert "**sample.txt:**" in enhanced_prompt
            assert "**sample.md:**" in enhanced_prompt
    
    def test_cli_file_with_output(self):
        """Test file attachment with output file."""
        test_file = self.test_files_dir / "sample.json"
        
        with patch('ollm.cli.get_app') as mock_app:
            mock_app_instance = mock_app.return_value
            mock_app_instance.initialize.return_value = None
            mock_app_instance.process_prompt.return_value = None
            mock_app_instance.cleanup.return_value = None
            
            with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as output_file:
                result = self.runner.invoke(app, [
                    "-p", "Analyze config", 
                    "-f", str(test_file),
                    "-o", output_file.name
                ])
                
                assert result.exit_code == 0
                
                # Verify process_prompt was called with output file
                mock_app_instance.process_prompt.assert_called_once()
                args = mock_app_instance.process_prompt.call_args
                output_arg = args[0][2]  # Third positional arg should be output path
                assert str(output_arg) == output_file.name
                
                Path(output_file.name).unlink()  # Clean up
    
    def test_cli_nonexistent_file_error(self):
        """Test CLI error handling for non-existent files."""
        result = self.runner.invoke(app, [
            "-p", "Test prompt",
            "-f", "/non/existent/file.txt"
        ])
        
        assert result.exit_code == 1
        assert "Error: File not found" in result.output