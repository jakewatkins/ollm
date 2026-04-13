"""Minimal functional test to verify ollm core functionality."""

import pytest
from pathlib import Path
from unittest.mock import Mock

# Test that the core modules can be imported
def test_core_imports():
    """Test that core ollm modules can be imported."""
    try:
        from ollm.config import Config, load_config, get_api_key
        from ollm.model_selection import select_model  
        from ollm.paths import resolve_install_directory
        from ollm.errors import OllmError, ConfigurationError
        from ollm.script_execution.executor import ScriptExecutor
        from ollm.skills.loader import SkillLoader
        from ollm.loop.agent_loop import AgentLoop
    except ImportError as e:
        pytest.fail(f"Failed to import core modules: {e}")


def test_config_creation():
    """Test basic config creation."""
    from ollm.config import Config
    
    config_data = {
        "baseUrl": "http://localhost:11434",
        "apiKey": "test-key"
    }
    
    config = Config(**config_data)
    assert config.base_url == "http://localhost:11434"
    assert config.api_key == "test-key"


def test_model_selection():
    """Test basic model selection logic."""
    from ollm.model_selection import select_model
    from ollm.ollama_client import OllamaClient
    from unittest.mock import Mock
    
    mock_client = Mock(spec=OllamaClient)
    
    # Test explicit model selection
    result = select_model(mock_client, requested_model="test-model")
    assert result == "test-model"
    
    # Test automatic selection
    mock_client.list_models.return_value = ["model-a", "model-b", "model-c"]
    result = select_model(mock_client, requested_model=None)
    assert result == "model-a"  # Lexically first


def test_path_resolution():
    """Test install directory resolution."""
    from ollm.paths import resolve_install_directory
    import tempfile
    import os
    from unittest.mock import patch, Mock
    
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        
        # Mock Path.home() to return temp directory  
        with patch('pathlib.Path.home', return_value=temp_path):
            with patch.dict(os.environ, {"OLLM_HOME": str(temp_path / "ollm")}, clear=True):
                # Create the directory
                (temp_path / "ollm").mkdir()
                
                result = resolve_install_directory()
                assert result == temp_path / "ollm"


if __name__ == "__main__":
    # Run the tests
    test_core_imports()
    test_config_creation()
    test_model_selection()
    test_path_resolution()
    print("✅ All functional tests passed!")