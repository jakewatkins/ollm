"""Agent loop implementation with bounds, timeouts, and tool calling."""

import asyncio
import json
from typing import Dict, List, Any, Optional

from ..config import AgentLoopConfig
from ..errors import OllmError
from ..logging_setup import get_logger
from ..mcp.client import McpClient
from ..mcp.tool_adapter import convert_mcp_tools_to_ollama
from ..ollama_client import OllamaClient
from .timeouts import with_timeout, Timer, TimeoutError

logger = get_logger(__name__)


class AgentLoop:
    """Bounded agent loop with tool calling support."""
    
    def __init__(
        self,
        ollama_client: OllamaClient,
        mcp_client: McpClient,
        config: AgentLoopConfig
    ):
        self.ollama_client = ollama_client
        self.mcp_client = mcp_client
        self.config = config
        self.timer = Timer()
    
    async def run(
        self,
        model: str,
        initial_prompt: str,
        skill_context: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Run the agent loop.
        
        Args:
            model: Ollama model to use
            initial_prompt: Initial user prompt
            skill_context: Optional skill context messages to inject
            
        Returns:
            Final assistant response
            
        Raises:
            OllmError: On various errors (timeout, max turns, etc.)
        """
        logger.info("Starting agent loop", extra={
            "model": model,
            "max_turns": self.config.max_turns,
            "tool_call_timeout": self.config.tool_call_timeout_seconds,
            "request_timeout": self.config.request_timeout_seconds,
            "skill_context_messages": len(skill_context) if skill_context else 0
        })
        
        self.timer.reset()
        
        # Build initial messages with skill context
        messages = []
        
        # Add skill context first (as system messages)
        if skill_context:
            messages.extend(skill_context)
            logger.debug(f"Added {len(skill_context)} skill context messages")
        
        # Add user prompt
        messages.append({"role": "user", "content": initial_prompt})
        
        # Get available tools
        tools = self.mcp_client.get_tools()
        ollama_tools = convert_mcp_tools_to_ollama(tools) if tools else None
        
        logger.debug(f"Available tools: {len(tools) if tools else 0}")
        
        # Main conversation loop
        turn = 0
        while turn < self.config.max_turns:
            turn += 1
            
            logger.debug(f"Agent loop turn {turn}/{self.config.max_turns}")
            
            try:
                # Make chat request with timeout
                response = await with_timeout(
                    self._make_chat_request(model, messages, ollama_tools),
                    self.config.request_timeout_seconds,
                    f"chat request (turn {turn})"
                )
                
                # Extract assistant message
                if "message" not in response or "content" not in response["message"]:
                    raise OllmError(f"Invalid response format from Ollama: {response}")
                
                assistant_message = response["message"]
                messages.append(assistant_message)
                
                # Check if response contains tool calls
                tool_calls = assistant_message.get("tool_calls", [])
                
                if not tool_calls:
                    # No tool calls - we're done
                    logger.info("Agent loop completed", extra={
                        "turns": turn,
                        "elapsed_time": self.timer.elapsed(),
                        "final_response_length": len(assistant_message["content"])
                    })
                    return assistant_message["content"]
                
                # Process tool calls
                await self._process_tool_calls(tool_calls, messages)
                
            except TimeoutError as e:
                logger.error(f"Timeout in agent loop: {e}")
                raise OllmError(str(e))
            except Exception as e:
                logger.error(f"Error in agent loop turn {turn}: {e}")
                raise OllmError(f"Agent loop error: {e}")
        
        # Max turns reached
        logger.warning(f"Agent loop hit max turns limit ({self.config.max_turns})")
        
        # Return the last assistant response, or a default message
        for message in reversed(messages):
            if message.get("role") == "assistant" and "content" in message:
                return message["content"]
        
        return "Maximum conversation turns reached. The conversation was truncated."
    
    async def _make_chat_request(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Make a chat request to Ollama.
        
        Args:
            model: Model to use
            messages: Conversation messages
            tools: Available tools (if any)
            
        Returns:
            Ollama chat response
        """
        # Note: Real Ollama tools support depends on the model and Ollama version
        # For now, just make a regular chat request
        return await asyncio.to_thread(
            self.ollama_client.chat,
            model=model,
            messages=messages
        )
    
    async def _process_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        messages: List[Dict[str, Any]]
    ) -> None:
        """Process tool calls and add results to messages.
        
        Args:
            tool_calls: List of tool calls from assistant
            messages: Current conversation messages (modified in place)
        """
        logger.debug(f"Processing {len(tool_calls)} tool calls")
        
        for tool_call in tool_calls:
            tool_name = tool_call.get("function", {}).get("name")
            tool_arguments = tool_call.get("function", {}).get("arguments", {})
            call_id = tool_call.get("id", "unknown")
            
            if not tool_name:
                logger.error("Tool call missing function name", extra={"tool_call": tool_call})
                self._add_tool_error_result(messages, call_id, "Tool call missing function name")
                continue
            
            logger.debug(f"Calling tool '{tool_name}'", extra={
                "call_id": call_id,
                "arguments": tool_arguments
            })
            
            try:
                # Parse arguments if string
                if isinstance(tool_arguments, str):
                    tool_arguments = json.loads(tool_arguments)
                
                # Call tool with timeout
                result = await with_timeout(
                    self.mcp_client.call_tool(tool_name, tool_arguments),
                    self.config.tool_call_timeout_seconds,
                    f"tool call '{tool_name}'"
                )
                
                # Add successful result
                self._add_tool_result(messages, call_id, result)
                
                logger.info(f"Tool call completed", extra={
                    "tool": tool_name,
                    "call_id": call_id
                })
                
            except TimeoutError as e:
                logger.error(f"Tool call timeout: {e}")
                self._add_tool_error_result(messages, call_id, str(e))
                
            except Exception as e:
                logger.error(f"Tool call error: {e}")
                self._add_tool_error_result(messages, call_id, str(e))
    
    def _add_tool_result(
        self,
        messages: List[Dict[str, Any]],
        call_id: str,
        result: Any
    ) -> None:
        """Add a successful tool result to messages."""
        messages.append({
            "role": "tool",
            "content": json.dumps(result, default=str),
            "tool_call_id": call_id
        })
    
    def _add_tool_error_result(
        self,
        messages: List[Dict[str, Any]],
        call_id: str,
        error_message: str
    ) -> None:
        """Add a tool error result to messages."""
        messages.append({
            "role": "tool", 
            "content": json.dumps({
                "error": error_message,
                "success": False
            }),
            "tool_call_id": call_id
        })