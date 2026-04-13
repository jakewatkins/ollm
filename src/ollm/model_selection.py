"""Model selection logic for ollm."""

import re
from typing import List, Optional

from .logging_setup import get_logger
from .ollama_client import OllamaClient

logger = get_logger(__name__)


def select_model(
    client: OllamaClient,
    requested_model: Optional[str] = None
) -> str:
    """Select a model to use for the request.
    
    Args:
        client: Ollama client instance
        requested_model: Model requested by user via -m flag
        
    Returns:
        Model name to use
        
    Raises:
        ValueError: If no models are available or requested model not found
    """
    if requested_model:
        logger.info(f"Using requested model: {requested_model}")
        return requested_model
    
    # No specific model requested, use auto-selection
    logger.debug("No model specified, selecting automatically")
    models = client.list_models()
    
    if not models:
        raise ValueError(
            "No models available from Ollama. Please install a model first using 'ollama pull <model-name>'."
        )
    
    logger.debug(f"Available models: {models}")
    
    # Sort models lexicographically and select the first one
    sorted_models = sorted(models, key=str.lower)
    selected_model = sorted_models[0]
    
    logger.info(f"Auto-selected model: {selected_model} (first of {len(models)} available models)")
    return selected_model


def validate_model_name(model_name: str) -> bool:
    """Validate that a model name is reasonably formatted.
    
    Args:
        model_name: Model name to validate
        
    Returns:
        True if model name appears valid
    """
    if not model_name or not isinstance(model_name, str):
        return False
    
    # Basic validation - no empty names, reasonable characters
    if not model_name.strip():
        return False
    
    # Allow alphanumeric, hyphens, underscores, dots, slashes, colons
    if not re.match(r'^[a-zA-Z0-9._:/-]+$', model_name):
        return False
    
    return True