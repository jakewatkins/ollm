"""MCP tool for exposing script execution to the agent loop."""

import asyncio
import logging
from typing import Dict, List, Optional, Any

from .executor import ScriptExecutor, ScriptExecutionRequest, ScriptExecutionResponse
from ..mcp.client import McpTool

logger = logging.getLogger(__name__)

class ScriptTool(McpTool):
    """MCP tool for script execution."""
    
    def __init__(self, executor: ScriptExecutor, skill_name: Optional[str] = None):
        """Initialize script execution tool.
        
        Args:
            executor: Script executor instance
            skill_name: Name of the skill this tool belongs to (for context)
        """
        self.executor = executor
        self.skill_name = skill_name
        
        # Build tool definition
        super().__init__(
            name="execute_script",
            description="Execute a script in an isolated container environment",
            input_schema={
                "type": "object",
                "properties": {
                    "script_content": {
                        "type": "string",
                        "description": "The script code to execute"
                    },
                    "script_language": {
                        "type": "string",
                        "description": "Programming language (python, bash, shell, javascript, node)",
                        "enum": ["python", "bash", "shell", "javascript", "node"]
                    },
                    "environment_vars": {
                        "type": "object",
                        "description": "Optional environment variables (string key-value pairs)",
                        "additionalProperties": {"type": "string"},
                        "default": {}
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Explanation of why this script execution is needed",
                        "default": ""
                    }
                },
                "required": ["script_content", "script_language"],
                "additionalProperties": False
            },
            server_name="ollm_script_executor"
        )
    
    async def call(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the script with given arguments.
        
        Args:
            arguments: Tool call arguments containing script details
            
        Returns:
            Dictionary with execution results
            
        Raises:
            Exception: If execution fails or arguments are invalid
        """
        try:
            # Extract and validate arguments
            script_content = arguments.get("script_content", "").strip()
            script_language = arguments.get("script_language", "").lower()
            environment_vars = arguments.get("environment_vars", {})
            reasoning = arguments.get("reasoning", "")
            
            if not script_content:
                raise ValueError("script_content is required and cannot be empty")
            
            if not script_language:
                raise ValueError("script_language is required")
            
            # Validate environment variables
            if not isinstance(environment_vars, dict):
                environment_vars = {}
            
            # Log the execution request
            logger.info(
                f"Script execution requested",
                extra={
                    "skill_name": self.skill_name,
                    "language": script_language,
                    "script_length": len(script_content),
                    "reasoning": reasoning[:100] + "..." if len(reasoning) > 100 else reasoning
                }
            )
            
            # Build execution request
            request = ScriptExecutionRequest(
                script_content=script_content,
                script_language=script_language,
                skill_name=self.skill_name,
                environment_vars=environment_vars,
                user_context={
                    "reasoning": reasoning,
                    "tool_call_timestamp": asyncio.get_event_loop().time()
                }
            )
            
            # Execute script
            response = await self.executor.execute_script(request)
            
            # Format response for MCP
            result = {
                "success": response.success,
                "task_id": response.task_id,
                "exit_code": response.exit_code,
                "output": {
                    "stdout": response.stdout,
                    "stderr": response.stderr
                },
                "execution_time": round(response.execution_time, 3),
                "metadata": {
                    "language": script_language,
                    "skill_name": response.skill_name,
                    "timed_out": response.timed_out
                }
            }
            
            # Add error information if execution failed
            if not response.success:
                result["error"] = {
                    "message": response.error_message or "Script execution failed",
                    "type": "execution_error" if response.exit_code != 0 else "timeout" if response.timed_out else "unknown"
                }
            
            # Log execution completion
            logger.info(
                f"Script execution completed",
                extra={
                    "task_id": response.task_id,
                    "success": response.success,
                    "execution_time": response.execution_time,
                    "exit_code": response.exit_code
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Script tool execution failed: {e}")
            
            # Return structured error response
            return {
                "success": False,
                "task_id": "error",
                "exit_code": -1,
                "output": {
                    "stdout": "",
                    "stderr": ""
                },
                "execution_time": 0.0,
                "error": {
                    "message": str(e),
                    "type": "tool_error"
                },
                "metadata": {
                    "language": arguments.get("script_language", "unknown"),
                    "skill_name": self.skill_name,
                    "timed_out": False
                }
            }


def create_script_tool_for_skill(
    executor: ScriptExecutor,
    skill_name: str,
    skill_resources: Dict[str, str] = None
) -> ScriptTool:
    """Create a script execution tool configured for a specific skill.
    
    Args:
        executor: Script executor instance
        skill_name: Name of the skill
        skill_resources: Optional skill resources to include
        
    Returns:
        Configured ScriptTool instance
    """
    tool = ScriptTool(executor, skill_name)
    
    # Store skill resources for execution context
    if skill_resources:
        tool._skill_resources = skill_resources
    
    # Customize tool for skill context
    tool.description = f"Execute a script as part of the '{skill_name}' skill in an isolated container environment"
    
    return tool


class SkillAwareScriptTool(ScriptTool):
    """Script tool that includes skill resources automatically."""
    
    def __init__(
        self,
        executor: ScriptExecutor,
        skill_name: str,
        skill_resources: Dict[str, str] = None
    ):
        """Initialize skill-aware script tool.
        
        Args:
            executor: Script executor instance
            skill_name: Name of the skill
            skill_resources: Skill resources to include in execution
        """
        super().__init__(executor, skill_name)
        self.skill_resources = skill_resources or {}
    
    async def call(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute script with skill resources included.
        
        Args:
            arguments: Tool call arguments
            
        Returns:
            Execution results
        """
        try:
            # Build request with skill resources
            request = ScriptExecutionRequest(
                script_content=arguments.get("script_content", "").strip(),
                script_language=arguments.get("script_language", "").lower(),
                skill_name=self.skill_name,
                skill_resources=self.skill_resources,
                environment_vars=arguments.get("environment_vars", {}),
                user_context={
                    "reasoning": arguments.get("reasoning", ""),
                    "tool_call_timestamp": asyncio.get_event_loop().time()
                }
            )
            
            # Execute with parent implementation
            response = await self.executor.execute_script(request)
            
            # Format response (same as parent)
            result = {
                "success": response.success,
                "task_id": response.task_id,
                "exit_code": response.exit_code,
                "output": {
                    "stdout": response.stdout,
                    "stderr": response.stderr
                },
                "execution_time": round(response.execution_time, 3),
                "metadata": {
                    "language": request.script_language,
                    "skill_name": response.skill_name,
                    "timed_out": response.timed_out,
                    "skill_resources": list(self.skill_resources.keys())
                }
            }
            
            if not response.success:
                result["error"] = {
                    "message": response.error_message or "Script execution failed",
                    "type": "execution_error" if response.exit_code != 0 else "timeout" if response.timed_out else "unknown"
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Skill-aware script tool execution failed: {e}")
            
            return {
                "success": False,
                "task_id": "error",
                "exit_code": -1,
                "output": {"stdout": "", "stderr": ""},
                "execution_time": 0.0,
                "error": {"message": str(e), "type": "tool_error"},
                "metadata": {
                    "language": arguments.get("script_language", "unknown"),
                    "skill_name": self.skill_name,
                    "timed_out": False,
                    "skill_resources": list(self.skill_resources.keys())
                }
            }