"""Skill schema definitions and validation."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any

import yaml
from pydantic import BaseModel, Field, ValidationError


class SkillMetadata(BaseModel):
    """Skill frontmatter metadata."""
    
    name: str = Field(..., description="Skill name")
    description: str = Field(..., description="Description of when to use this skill")
    requiredMcpServers: Optional[List[str]] = Field(
        default=None, 
        description="Required MCP server names"
    )
    preferredTools: Optional[List[str]] = Field(
        default=None,
        description="Preferred MCP tool names" 
    )
    resources: Optional[List[str]] = Field(
        default=None,
        description="Relative file paths for additional context"
    )
    scriptExecution: Optional[bool] = Field(
        default=False,
        description="Enable script execution capabilities"
    )


@dataclass
class Skill:
    """A complete skill definition."""
    
    name: str
    skill_dir: Path
    metadata: SkillMetadata
    instructions: str
    resource_files: Dict[str, str] = None
    
    def __post_init__(self):
        if self.resource_files is None:
            self.resource_files = {}


class SkillParseError(Exception):
    """Error parsing skill file."""
    pass


def parse_skill_md(skill_file: Path) -> Skill:
    """Parse a SKILL.md file into a Skill object.
    
    Args:
        skill_file: Path to SKILL.md file
        
    Returns:
        Skill object
        
    Raises:
        SkillParseError: If skill cannot be parsed
    """
    try:
        content = skill_file.read_text(encoding='utf-8')
    except Exception as e:
        raise SkillParseError(f"Could not read skill file {skill_file}: {e}")
    
    # Split frontmatter and content
    if not content.startswith('---'):
        raise SkillParseError(f"Skill file {skill_file} missing frontmatter")
    
    # Find end of frontmatter
    parts = content[3:].split('---', 1)
    if len(parts) != 2:
        raise SkillParseError(f"Skill file {skill_file} has invalid frontmatter format")
    
    frontmatter_text, instructions = parts
    instructions = instructions.strip()
    
    # Parse frontmatter YAML
    try:
        frontmatter_data = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as e:
        raise SkillParseError(f"Invalid YAML frontmatter in {skill_file}: {e}")
    
    # Validate metadata
    try:
        metadata = SkillMetadata(**frontmatter_data)
    except ValidationError as e:
        raise SkillParseError(f"Invalid skill metadata in {skill_file}: {e}")
    
    # Create skill object
    skill_dir = skill_file.parent
    
    # Import secrets function locally to avoid circular imports
    try:
        from ..secrets import process_secrets_in_text
        # Process secrets in instructions
        instructions = process_secrets_in_text(instructions)
    except ImportError:
        # If secrets module not available, continue without processing
        pass
    
    skill = Skill(
        name=metadata.name,
        skill_dir=skill_dir,
        metadata=metadata,
        instructions=instructions
    )
    
    return skill


def validate_skill_name(name: str) -> bool:
    """Validate skill name format.
    
    Args:  
        name: Skill name to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Allow alphanumeric, hyphens, underscores
    pattern = r'^[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, name)) and len(name) > 0