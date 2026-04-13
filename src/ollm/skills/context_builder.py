"""Skill context building for Ollama requests."""

from typing import List, Optional, Dict, Any
import logging

from .schema import Skill
from ..logging_setup import get_logger

logger = get_logger(__name__)


class SkillContextBuilder:
    """Builds context messages from selected skills."""
    
    def build_context(self, skill: Skill) -> List[Dict[str, Any]]:
        """Build context messages from a skill.
        
        Args:
            skill: Selected skill to build context from
            
        Returns:
            List of context messages to inject into Ollama request
        """
        context_messages = []
        
        # Build the main skill context
        skill_context = self._build_skill_instructions(skill)
        if skill_context:
            context_messages.append({
                "role": "system",
                "content": skill_context
            })
            
        # Add resource contexts if available
        resource_contexts = self._build_resource_contexts(skill)
        context_messages.extend(resource_contexts)
        
        logger.debug(f"Built {len(context_messages)} context messages from skill '{skill.name}'")
        
        return context_messages
    
    def _build_skill_instructions(self, skill: Skill) -> str:
        """Build the main instruction context from skill.
        
        Args:
            skill: Skill to build instructions from
            
        Returns:
            Instruction text
        """
        lines = []
        
        # Add header
        lines.append(f"# {skill.metadata.name} Skill")
        lines.append("")
        
        # Add description
        lines.append(f"**Description:** {skill.metadata.description}")
        lines.append("")
        
        # Add MCP server requirements if present
        if skill.metadata.requiredMcpServers:
            lines.append("**Required MCP Servers:**")
            for server in skill.metadata.requiredMcpServers:
                lines.append(f"- {server}")
            lines.append("")
        
        # Add preferred tools if present
        if skill.metadata.preferredTools:
            lines.append("**Preferred Tools:**")
            for tool in skill.metadata.preferredTools:
                lines.append(f"- {tool}")
            lines.append("")
        
        # Add script execution notice if enabled
        if skill.metadata.scriptExecution:
            lines.append("**Script Execution:** Available via execute_script tool")
            lines.append("")
        
        # Add main instructions
        lines.append("**Instructions:**")
        lines.append("")
        lines.append(skill.instructions)
        
        return "\n".join(lines)
    
    def _build_resource_contexts(self, skill: Skill) -> List[Dict[str, Any]]:
        """Build context messages from skill resources.
        
        Args:
            skill: Skill with loaded resources
            
        Returns:
            List of resource context messages
        """
        context_messages = []
        
        if not skill.resource_files:
            return context_messages
        
        for resource_path, content in skill.resource_files.items():
            # Create context message for each resource
            resource_context = self._build_resource_context(resource_path, content)
            if resource_context:
                context_messages.append({
                    "role": "system",
                    "content": resource_context
                })
        
        return context_messages
    
    def _build_resource_context(self, resource_path: str, content: str) -> str:
        """Build context from a single resource file.
        
        Args:
            resource_path: Relative path of the resource
            content: Resource file content
            
        Returns:
            Formatted resource context
        """
        lines = []
        
        # Add resource header  
        lines.append(f"## Skill Resource: {resource_path}")
        lines.append("")
        
        # Add content (preserve formatting)
        lines.append(content.strip())
        
        return "\n".join(lines)
    
    def get_tool_filter(self, skill: Skill, available_tools: List[str]) -> Optional[List[str]]:
        """Get filtered tool list based on skill preferences.
        
        Args:
            skill: Selected skill
            available_tools: List of all available tool names
            
        Returns:
            Filtered tool list, or None to use all tools
        """
        if not skill.metadata.preferredTools:
            # No preference specified, use all available tools
            return None
        
        # Filter to only preferred tools that are actually available
        preferred_available = []
        for tool_name in skill.metadata.preferredTools:
            if tool_name in available_tools:
                preferred_available.append(tool_name)
            else:
                logger.debug(f"Preferred tool '{tool_name}' not available")
        
        # If no preferred tools are available, fall back to all tools
        if not preferred_available:
            logger.debug("No preferred tools available, using all tools")
            return None
        
        logger.debug(f"Filtered to {len(preferred_available)} preferred tools: {preferred_available}")
        return preferred_available