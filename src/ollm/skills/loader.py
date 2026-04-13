"""Skill discovery and loading."""

from pathlib import Path
from typing import List, Dict, Optional
import logging

from .schema import Skill, SkillParseError, parse_skill_md, validate_skill_name
from ..config import Config
from ..logging_setup import get_logger

logger = get_logger(__name__)


class SkillLoader:
    """Loads and manages skills from the skills directory."""
    
    def __init__(self, config: Config, skills_dir: Path):
        self.config = config
        self.skills_dir = skills_dir
        self._skills_cache: Optional[Dict[str, Skill]] = None
    
    def discover_skills(self) -> Dict[str, Skill]:
        """Discover and load all valid skills.
        
        Returns:
            Dictionary mapping skill names to Skill objects
        """
        if self._skills_cache is not None:
            return self._skills_cache
            
        skills = {}
        
        if not self.skills_dir.exists():
            logger.info(f"Skills directory {self.skills_dir} does not exist, running without skills")
            self._skills_cache = skills
            return skills
            
        logger.info(f"Scanning skills directory: {self.skills_dir}")
        
        # Scan for skill directories
        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
                
            skill_name = skill_dir.name
            if not validate_skill_name(skill_name):
                logger.warning(f"Skipping skill with invalid name: {skill_name}")
                continue
                
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                logger.warning(f"Skipping skill {skill_name}: missing SKILL.md")
                continue
                
            try:
                skill = self._load_skill(skill_file)
                
                # Validate skill name matches directory name
                if skill.name != skill_name:
                    logger.warning(
                        f"Skill name mismatch: directory '{skill_name}' vs metadata '{skill.name}'. "
                        f"Using metadata name."
                    )
                
                # Check for name conflicts
                if skill.name in skills:
                    logger.warning(f"Duplicate skill name '{skill.name}', skipping {skill_file}")
                    continue
                    
                skills[skill.name] = skill
                logger.info(f"Loaded skill: {skill.name}")
                
            except SkillParseError as e:
                logger.warning(f"Failed to parse skill {skill_name}: {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error loading skill {skill_name}: {e}")
                continue
        
        logger.info(f"Discovered {len(skills)} valid skills")
        self._skills_cache = skills
        return skills
    
    def _load_skill(self, skill_file: Path) -> Skill:
        """Load a single skill from SKILL.md file.
        
        Args:
            skill_file: Path to SKILL.md file
            
        Returns:
            Loaded skill
            
        Raises:
            SkillParseError: If skill cannot be loaded
        """
        # Parse the skill
        skill = parse_skill_md(skill_file)
        
        # Load resources if declared
        if skill.metadata.resources:
            self._load_skill_resources(skill)
            
        return skill
    
    def _load_skill_resources(self, skill: Skill) -> None:
        """Load additional resource files for a skill.
        
        Args:
            skill: Skill to load resources for
            
        Raises:
            SkillParseError: If resources exceed limits
        """
        max_file_size = self.config.skills.resources.maxFileSizeKB * 1024
        max_total_size = self.config.skills.resources.maxTotalSizeKB * 1024
        
        total_size = 0
        loaded_resources = {}
        
        for resource_path in skill.metadata.resources:
            resource_file = skill.skill_dir / resource_path
            
            # Check if file exists
            if not resource_file.exists():
                logger.warning(f"Resource file not found: {resource_file}")
                continue
                
            # Check if it's a file (not directory)
            if not resource_file.is_file():
                logger.warning(f"Resource path is not a file: {resource_file}")
                continue
                
            try:
                # Check file size
                file_size = resource_file.stat().st_size
                if file_size > max_file_size:
                    raise SkillParseError(
                        f"Resource file {resource_file} exceeds maxFileSizeKB "
                        f"({file_size} > {max_file_size} bytes)"
                    )
                
                # Check total size
                if total_size + file_size > max_total_size:
                    raise SkillParseError(
                        f"Total resource size exceeds maxTotalSizeKB "
                        f"({total_size + file_size} > {max_total_size} bytes)"
                    )
                
                # Load file content
                content = resource_file.read_text(encoding='utf-8')
                loaded_resources[resource_path] = content
                total_size += file_size
                
                logger.debug(f"Loaded resource {resource_path} ({file_size} bytes)")
                
            except Exception as e:
                logger.warning(f"Failed to load resource {resource_file}: {e}")
                continue
        
        skill.resource_files = loaded_resources
        logger.debug(f"Loaded {len(loaded_resources)} resources for skill {skill.name}")
    
    def get_skill(self, name: str) -> Optional[Skill]:
        """Get a skill by name.
        
        Args:
            name: Skill name
            
        Returns:
            Skill if found, None otherwise
        """
        skills = self.discover_skills()
        return skills.get(name)
    
    def list_skills(self) -> List[str]:
        """Get list of available skill names.
        
        Returns:
            List of skill names
        """
        skills = self.discover_skills()
        return list(skills.keys())
    
    def clear_cache(self) -> None:
        """Clear the skills cache to force reload."""
        self._skills_cache = None