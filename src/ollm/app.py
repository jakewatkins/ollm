"""Main application logic for ollm."""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer

from .config import Config, load_config
from .errors import OllmError, ConfigurationError, InstallDirectoryError, OllamaError
from .logging_setup import setup_logging, get_logger
from .loop.agent_loop import AgentLoop
from .mcp.client import McpClient
from .mcp.config_schema import load_mcp_config
from .model_selection import select_model
from .ollama_client import OllamaClient
from .output import write_output
from .paths import resolve_install_directory
from .skills import SkillLoader, SkillSelector, SkillContextBuilder, Skill
from .script_execution import ScriptExecutor, SkillAwareScriptTool

logger = get_logger(__name__)


class OllmApp:
    """Main ollm application."""
    
    def __init__(self):
        self.config: Optional[Config] = None
        self.config_file: Optional[Path] = None
        self.install_dir: Optional[Path] = None
        self.ollama_client: Optional[OllamaClient] = None
        self.mcp_client: Optional[McpClient] = None
        self.agent_loop: Optional[AgentLoop] = None
        self.skill_loader: Optional[SkillLoader] = None
        self.skill_selector: Optional[SkillSelector] = None
        self.skill_context_builder: Optional[SkillContextBuilder] = None
        self.script_executor: Optional[ScriptExecutor] = None
    
    def initialize(self) -> None:
        """Initialize the application.
        
        Raises:
            typer.Exit: On initialization errors
        """
        try:
            # Resolve install directory
            self.install_dir = resolve_install_directory()
            logger.info(f"Using install directory: {self.install_dir}")
            
            # Load configuration
            self.config = load_config(self.config_file)
            logger.info("Configuration loaded successfully")
            
            # Setup logging with loaded config
            setup_logging(self.config.logging)
            logger.info("Logging initialized")
            
            # Initialize Ollama client
            self.ollama_client = OllamaClient(self.config)
            logger.info("Ollama client initialized")
            
            # Load MCP configuration and initialize client
            mcp_config = load_mcp_config(self.install_dir)
            self.mcp_client = McpClient(mcp_config)
            
            # Initialize MCP connections
            asyncio.run(self._async_init_mcp())
            
            # Initialize skills system
            skills_dir = self.install_dir / "skills"
            self.skill_loader = SkillLoader(self.config, skills_dir)
            self.skill_selector = SkillSelector(self.config)
            self.skill_context_builder = SkillContextBuilder()
            logger.info("Skills system initialized")
            
            # Initialize script execution (if enabled)
            try:
                if self.config.script_execution.enabled:
                    self.script_executor = ScriptExecutor(self.config.script_execution)
                    asyncio.run(self._async_init_script_executor())
                    logger.info("Script execution system initialized")
                else:
                    logger.info("Script execution disabled in configuration")
            except Exception as e:
                logger.error(f"Failed to initialize script execution: {e}")
                logger.info("Continuing without script execution capabilities")
                self.script_executor = None
            
            # Initialize agent loop
            self.agent_loop = AgentLoop(
                self.ollama_client,
                self.mcp_client,
                self.config.agent_loop
            )
            logger.info("Agent loop initialized")
            
        except InstallDirectoryError as e:
            print(f"Install Directory Error: {e}", file=sys.stderr)
            raise typer.Exit(1)
        except ConfigurationError as e:
            print(f"Configuration Error: {e}", file=sys.stderr)
            raise typer.Exit(1)
        except Exception as e:
            print(f"Initialization Error: {e}", file=sys.stderr)
            raise typer.Exit(1)
    
    async def _async_init_mcp(self) -> None:
        """Initialize MCP connections asynchronously."""
        if self.mcp_client:
            await self.mcp_client.connect_all()
    
    async def _async_init_script_executor(self) -> None:
        """Initialize script executor asynchronously."""
        if self.script_executor:
            await self.script_executor.initialize()
    
    def process_prompt(
        self, 
        prompt_content: str, 
        model: Optional[str] = None,
        output_file: Optional[Path] = None
    ) -> None:
        """Process a prompt using Ollama with MCP tools and skills support.
        
        Args:
            prompt_content: The prompt to process
            model: Optional model name to use
            output_file: Optional output file path
        """
        if not self.config or not self.ollama_client or not self.agent_loop:
            raise OllmError("Application not initialized")
        
        # Get available MCP servers for skill selection
        available_mcp_servers = []
        if self.mcp_client:
            available_mcp_servers = list(self.mcp_client.get_connected_servers())
        
        logger.info("Processing prompt", extra={
            "prompt_length": len(prompt_content),
            "requested_model": model,
            "output_file": str(output_file) if output_file else None,
            "tools_available": len(self.mcp_client.get_tools()) if self.mcp_client else 0,
            "mcp_servers": len(available_mcp_servers)
        })
        
        try:
            # Select best skill for this prompt
            selected_skill = None
            skill_context = []
            additional_tools = []
            
            if self.skill_loader and self.skill_selector and self.skill_context_builder:
                available_skills = self.skill_loader.discover_skills()
                selected_skill = self.skill_selector.select_skill(
                    prompt_content, 
                    available_skills, 
                    available_mcp_servers
                )
                
                if selected_skill:
                    skill_context = self.skill_context_builder.build_context(selected_skill)
                    
                    # Add script execution tools if skill supports it and executor is available
                    if (selected_skill.metadata.scriptExecution and 
                        self.script_executor and 
                        self.script_executor.is_initialized()):
                        
                        # Create skill-aware script tool with resources
                        script_tool = SkillAwareScriptTool(
                            self.script_executor,
                            selected_skill.name,
                            selected_skill.resources
                        )
                        
                        additional_tools.append(script_tool)
                        
                        logger.info(
                            f"Added script execution tool for skill '{selected_skill.name}'",
                            extra={
                                "skill_resources": len(selected_skill.resources),
                                "script_execution_enabled": True
                            }
                        )
                    
                    logger.info(f"Using skill: {selected_skill.name}")
                else:
                    logger.debug("No skill selected for this prompt")
            
            # Select model to use
            selected_model = select_model(self.ollama_client, model)
            
            # Run agent loop with skill context and additional tools
            logger.debug(f"Starting agent loop with model: {selected_model}")
            response = asyncio.run(
                self.agent_loop.run(
                    selected_model, 
                    prompt_content, 
                    skill_context, 
                    additional_tools
                )
            )
            
            # Write output
            write_output(response, output_file)
            
            logger.info("Prompt processing completed successfully", extra={
                "model_used": selected_model,
                "response_length": len(response),
                "skill_used": selected_skill.name if selected_skill else None
            })
            
        except OllamaError as e:
            logger.error(f"Ollama error: {e}")
            raise OllmError(f"Ollama error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error processing prompt: {e}")
            raise OllmError(f"Unexpected error: {e}")
    
    def list_models(self, output_file: Optional[Path] = None) -> None:
        """List available Ollama models.
        
        Args:
            output_file: Optional output file path
        """
        if not self.config or not self.ollama_client:
            raise OllmError("Application not initialized")
        
        logger.info("Listing available models", extra={
            "output_file": str(output_file) if output_file else None
        })
        
        try:
            # Get models from Ollama
            model_names = self.ollama_client.list_models()
            
            # Convert to text (one per line)
            model_list_text = "\n".join(model_names)
            
            # Write output
            write_output(model_list_text, output_file)
            
            logger.info("Model listing completed successfully", extra={
                "model_count": len(model_names)
            })
            
        except OllamaError as e:
            logger.error(f"Ollama error listing models: {e}")
            raise OllmError(f"Failed to list models: {e}")
        except Exception as e:
            logger.error(f"Unexpected error listing models: {e}")
            raise OllmError(f"Unexpected error: {e}")
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        # Cleanup script executor
        if self.script_executor:
            asyncio.run(self.script_executor.cleanup())
        
        # Cleanup MCP connections
        if self.mcp_client:
            asyncio.run(self.mcp_client.disconnect_all())
        
        # Cleanup Ollama client
        if self.ollama_client:
            self.ollama_client.close()


# Global app instance
app_instance = OllmApp()


def get_app() -> OllmApp:
    """Get the global app instance."""
    return app_instance