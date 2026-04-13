"""Ollama HTTP client for ollm."""

import asyncio
import json
from typing import Any, Dict, List, Optional

import httpx

from .config import Config, get_api_key
from .errors import OllamaError
from .logging_setup import get_logger

logger = get_logger(__name__)


class OllamaClient:
    """HTTP client for Ollama API."""
    
    def __init__(self, config: Config):
        """Initialize Ollama client.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.base_url = config.base_url
        self.api_key = get_api_key(config)
        self.timeout = config.agent_loop.request_timeout_seconds
        
        # Create HTTP client
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            logger.debug("Using API key for Ollama authentication")
        
        self.client = httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=self.timeout
        )
        
        logger.info(f"Initialized Ollama client for {self.base_url}")
    
    def list_models(self) -> List[str]:
        """List available models from Ollama.
        
        Returns:
            List of model names
            
        Raises:
            OllamaError: On API errors
        """
        try:
            logger.debug("Requesting model list from Ollama")
            response = self.client.get("/api/tags")
            
            if response.status_code == 401:
                raise OllamaError(
                    "Authentication to Ollama failed. Check your API key and endpoint configuration."
                )
            elif response.status_code == 403:
                raise OllamaError(
                    "Authentication to Ollama failed. Check your API key and endpoint configuration."
                )
            
            response.raise_for_status()
            
            data = response.json()
            models = data.get("models", [])
            
            # Extract model names
            model_names = []
            for model in models:
                name = model.get("name", "")
                if name:
                    model_names.append(name)
            
            logger.info(f"Retrieved {len(model_names)} models from Ollama")
            return model_names
            
        except httpx.TimeoutException:
            raise OllamaError(f"Request to Ollama timed out after {self.timeout} seconds")
        except httpx.ConnectError:
            raise OllamaError(f"Could not connect to Ollama at {self.base_url}")
        except httpx.HTTPError as e:
            raise OllamaError(f"HTTP error communicating with Ollama: {e}")
        except json.JSONDecodeError:
            raise OllamaError("Invalid JSON response from Ollama")
        except Exception as e:
            raise OllamaError(f"Unexpected error communicating with Ollama: {e}")
    
    def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Send a chat request to Ollama.
        
        Args:
            model: Model name to use
            messages: Chat messages in OpenAI format
            tools: Optional tool definitions
            stream: Whether to stream the response
            
        Returns:
            Chat response from Ollama
            
        Raises:
            OllamaError: On API errors
        """
        try:
            payload = {
                "model": model,
                "messages": messages,
                "stream": stream
            }
            
            if tools:
                payload["tools"] = tools
            
            logger.debug(f"Sending chat request to Ollama", extra={
                "model": model,
                "message_count": len(messages),
                "tool_count": len(tools) if tools else 0,
                "stream": stream
            })
            
            response = self.client.post("/api/chat", json=payload)
            
            if response.status_code == 401:
                raise OllamaError(
                    "Authentication to Ollama failed. Check your API key and endpoint configuration."
                )
            elif response.status_code == 403:
                raise OllamaError(
                    "Authentication to Ollama failed. Check your API key and endpoint configuration."
                )
            elif response.status_code == 404:
                raise OllamaError(f"Model '{model}' not found. Please pull the model first: ollama pull {model}")
            
            response.raise_for_status()
            
            result = response.json()
            logger.info("Received chat response from Ollama", extra={
                "model": model,
                "done": result.get("done", False)
            })
            
            return result
            
        except httpx.TimeoutException:
            raise OllamaError(f"Chat request to Ollama timed out after {self.timeout} seconds")
        except httpx.ConnectError:
            raise OllamaError(f"Could not connect to Ollama at {self.base_url}")
        except httpx.HTTPError as e:
            raise OllamaError(f"HTTP error during chat request: {e}")
        except json.JSONDecodeError:
            raise OllamaError("Invalid JSON response from Ollama chat")
        except Exception as e:
            raise OllamaError(f"Unexpected error during chat request: {e}")
    
    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()
        logger.debug("Closed Ollama client")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()