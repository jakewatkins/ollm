"""MCP client for connecting to and managing MCP servers."""

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from contextlib import asynccontextmanager
import httpx

from ..errors import OllmError
from ..logging_setup import get_logger
from ..newrelic_integration import get_event_recorder
from .config_schema import McpConfig, StdioServerConfig, HttpServerConfig

logger = get_logger(__name__)


class McpTool:
    """Represents a tool discovered from an MCP server."""
    
    def __init__(self, name: str, description: str, input_schema: Dict[str, Any], server_name: str):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.server_name = server_name


class McpServer:
    """Base class for MCP server connections."""
    
    def __init__(self, name: str, config: Any):
        self.name = name
        self.config = config
        self.tools: Dict[str, McpTool] = {}
        self.connected = False
    
    async def connect(self) -> None:
        """Connect to the MCP server."""
        raise NotImplementedError
    
    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        raise NotImplementedError
    
    async def list_tools(self) -> List[McpTool]:
        """List available tools from this server."""
        raise NotImplementedError
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on this server."""
        raise NotImplementedError


class StdioMcpServer(McpServer):
    """MCP server connected via stdio."""
    
    def __init__(self, name: str, config: StdioServerConfig):
        super().__init__(name, config)
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0
        
    async def connect(self) -> None:
        """Start the stdio MCP server process."""
        if self.connected:
            return
            
        logger.debug(f"Starting stdio MCP server '{self.name}'", extra={
            "command": self.config.command,
            "command_args": self.config.args
        })
        
        try:
            # Build command line
            command = [self.config.command]
            if self.config.args:
                command.extend(self.config.args)
            
            # Build environment
            env = {}
            if self.config.env:
                env.update(self.config.env)
            
            # Start process
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                bufsize=0
            )
            
            self.connected = True
            logger.info(f"Started stdio MCP server '{self.name}'", extra={"pid": self.process.pid})
            
        except Exception as e:
            logger.error(f"Failed to start stdio MCP server '{self.name}': {e}")
            raise OllmError(f"Failed to start MCP server {self.name}: {e}")
    
    async def disconnect(self) -> None:
        """Stop the stdio MCP server process."""
        if self.process:
            logger.debug(f"Stopping stdio MCP server '{self.name}'")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"Force killing stdio MCP server '{self.name}'")
                self.process.kill()
            
            self.process = None
            self.connected = False
            logger.info(f"Stopped stdio MCP server '{self.name}'")
    
    async def list_tools(self) -> List[McpTool]:
        """List tools via JSON-RPC."""
        if not self.connected or not self.process:
            raise OllmError(f"MCP server {self.name} not connected")
        
        # For now, return empty list - full JSON-RPC implementation would go here
        logger.debug(f"Listing tools for stdio MCP server '{self.name}' (placeholder)")
        return []
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call tool via JSON-RPC."""
        if not self.connected or not self.process:
            raise OllmError(f"MCP server {self.name} not connected")
        
        # For now, return empty result - full JSON-RPC implementation would go here
        logger.debug(f"Calling tool '{tool_name}' on stdio MCP server '{self.name}' (placeholder)")
        return {"result": "placeholder"}


class HttpMcpServer(McpServer):
    """MCP server connected via HTTP/SSE."""
    
    def __init__(self, name: str, config: HttpServerConfig):
        super().__init__(name, config)
        self.client: Optional[httpx.AsyncClient] = None
    
    async def connect(self) -> None:
        """Connect to HTTP MCP server."""
        if self.connected:
            return
        
        logger.debug(f"Connecting to HTTP MCP server '{self.name}'", extra={
            "url": self.config.url,
            "type": self.config.type
        })
        
        try:
            # Create HTTP client
            headers = self.config.headers or {}
            self.client = httpx.AsyncClient(
                base_url=self.config.url,
                headers=headers,
                timeout=30.0
            )
            
            # Test connection with health check
            response = await self.client.get("/health")
            response.raise_for_status()
            
            self.connected = True
            logger.info(f"Connected to HTTP MCP server '{self.name}'")
            
        except Exception as e:
            logger.error(f"Failed to connect to HTTP MCP server '{self.name}': {e}")
            if self.client:
                await self.client.aclose()
                self.client = None
            raise OllmError(f"Failed to connect to MCP server {self.name}: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from HTTP MCP server."""
        if self.client:
            logger.debug(f"Disconnecting from HTTP MCP server '{self.name}'")
            await self.client.aclose()
            self.client = None
            self.connected = False
            logger.info(f"Disconnected from HTTP MCP server '{self.name}'")
    
    async def list_tools(self) -> List[McpTool]:
        """List tools via HTTP API."""
        if not self.connected or not self.client:
            raise OllmError(f"MCP server {self.name} not connected")
        
        # For now, return empty list - full HTTP API implementation would go here
        logger.debug(f"Listing tools for HTTP MCP server '{self.name}' (placeholder)")
        return []
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call tool via HTTP API."""
        if not self.connected or not self.client:
            raise OllmError(f"MCP server {self.name} not connected")
        
        # For now, return empty result - full HTTP API implementation would go here
        logger.debug(f"Calling tool '{tool_name}' on HTTP MCP server '{self.name}' (placeholder)")
        return {"result": "placeholder"}


class McpClient:
    """Main MCP client that manages multiple servers."""
    
    def __init__(self, config: Optional[McpConfig] = None):
        self.config = config
        self.servers: Dict[str, McpServer] = {}
        self.tools: Dict[str, McpTool] = {}  # tool_name -> tool
    
    async def connect_all(self) -> None:
        """Connect to all configured MCP servers."""
        if not self.config:
            logger.info("No MCP configuration found, running without tools")
            return
        
        logger.info(f"Connecting to {len(self.config.servers)} MCP servers")
        
        for name, server_config in self.config.servers.items():
            try:
                # Create appropriate server type
                if isinstance(server_config, StdioServerConfig):
                    server = StdioMcpServer(name, server_config)
                elif isinstance(server_config, HttpServerConfig):
                    server = HttpMcpServer(name, server_config)
                else:
                    logger.error(f"Unknown server config type for '{name}': {type(server_config)}")
                    continue
                
                # Connect and discover tools
                await server.connect()
                tools = await server.list_tools()
                
                # Register server and tools
                self.servers[name] = server
                for tool in tools:
                    self.tools[tool.name] = tool
                
                logger.info(f"Connected to MCP server '{name}', discovered {len(tools)} tools")
                
            except Exception as e:
                logger.error(f"Failed to connect to MCP server '{name}': {e}")
                # Continue with other servers
    
    async def disconnect_all(self) -> None:
        """Disconnect from all MCP servers."""
        logger.debug("Disconnecting from all MCP servers")
        
        for name, server in self.servers.items():
            try:
                await server.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting from MCP server '{name}': {e}")
        
        self.servers.clear()
        self.tools.clear()
        logger.info("Disconnected from all MCP servers")
    
    def get_tool_names(self) -> List[str]:
        """Get list of all available tool names."""
        return list(self.tools.keys())
    
    def get_tools(self) -> List[McpTool]:
        """Get list of all available tools."""
        return list(self.tools.values())
    
    def get_connected_servers(self) -> List[str]:
        """Get list of successfully connected server names."""
        return [name for name, server in self.servers.items() if server.connected]
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the appropriate MCP server."""
        if tool_name not in self.tools:
            raise OllmError(f"Tool '{tool_name}' not found")
        
        tool = self.tools[tool_name]
        server = self.servers.get(tool.server_name)
        
        if not server:
            raise OllmError(f"Server '{tool.server_name}' for tool '{tool_name}' not found")
        
        logger.debug(f"Calling MCP tool '{tool_name}'", extra={
            "server": tool.server_name,
            "arguments": arguments
        })
        
        # Record timing for New Relic event
        start_time = time.perf_counter()
        event_recorder = get_event_recorder()
        
        try:
            result = await server.call_tool(tool_name, arguments)
            
            # Calculate duration and record success event
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            if event_recorder:
                event_recorder.record_tool_call(
                    tool_name=tool_name,
                    duration_ms=duration_ms,
                    status="success"
                )
            
            logger.info(f"MCP tool call completed", extra={
                "tool": tool_name,
                "server": tool.server_name,
                "duration_ms": duration_ms
            })
            return result
            
        except Exception as e:
            # Calculate duration and record failure event
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            
            # Determine error type
            error_type = "exception"
            http_status_code = None
            
            if isinstance(e, httpx.HTTPStatusError):
                error_type = "http_error"
                http_status_code = e.response.status_code
            elif isinstance(e, httpx.TimeoutException):
                error_type = "timeout"
            elif isinstance(e, httpx.ConnectError):
                error_type = "connection_error"
            
            if event_recorder:
                event_recorder.record_tool_call(
                    tool_name=tool_name,
                    duration_ms=duration_ms,
                    status="failure",
                    error_message=str(e),
                    error_type=error_type,
                    http_status_code=http_status_code
                )
            
            logger.error(f"MCP tool call failed", extra={
                "tool": tool_name,
                "server": tool.server_name,
                "error": str(e),
                "duration_ms": duration_ms
            })
            raise OllmError(f"Tool call failed for '{tool_name}': {e}")