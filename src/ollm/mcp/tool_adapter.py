"""Tool adapter to convert MCP tools to Ollama tool format."""

from typing import Dict, List, Any

from .client import McpTool


def convert_mcp_tool_to_ollama(tool: McpTool) -> Dict[str, Any]:
    """Convert an MCP tool to Ollama tool format.
    
    Args:
        tool: MCP tool to convert
        
    Returns:
        Ollama tool definition dict
    """
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.input_schema
        }
    }


def convert_mcp_tools_to_ollama(tools: List[McpTool]) -> List[Dict[str, Any]]:
    """Convert a list of MCP tools to Ollama tools format.
    
    Args:
        tools: List of MCP tools to convert
        
    Returns:
        List of Ollama tool definitions
    """
    return [convert_mcp_tool_to_ollama(tool) for tool in tools]


def create_tool_name_mapping(tools: List[McpTool]) -> Dict[str, str]:
    """Create mapping from Ollama tool call names to MCP tool names.
    
    Args:
        tools: List of MCP tools
        
    Returns:
        Dictionary mapping tool names to server names
    """
    return {tool.name: tool.server_name for tool in tools}