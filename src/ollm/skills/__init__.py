"""Skills module for ollm.

This module provides skill discovery, parsing, selection, and context building.
Skills are reusable workflow packages that guide how Ollama should use available
MCP tools and context.
"""

from .schema import Skill, SkillMetadata
from .loader import SkillLoader
from .selector import SkillSelector
from .context_builder import SkillContextBuilder

__all__ = [
    "Skill",
    "SkillMetadata", 
    "SkillLoader",
    "SkillSelector",
    "SkillContextBuilder",
]