"""Skill selection and scoring."""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging

from .schema import Skill
from ..config import Config
from ..logging_setup import get_logger

logger = get_logger(__name__)


@dataclass
class SkillScore:
    """Skill scoring result."""
    skill: Skill
    score: float
    details: Dict[str, float]


class SkillSelector:
    """Selects the best matching skill for a given prompt."""
    
    def __init__(self, config: Config):
        self.config = config
    
    def select_skill(
        self, 
        prompt: str, 
        available_skills: Dict[str, Skill],
        available_mcp_servers: List[str]
    ) -> Optional[Skill]:
        """Select the best matching skill for a prompt.
        
        Args:
            prompt: User prompt to match against
            available_skills: Available skills to choose from
            available_mcp_servers: List of successfully loaded MCP server names
            
        Returns:
            Selected skill or None if no skill meets threshold
        """
        if not available_skills:
            logger.debug("No skills available for selection")
            return None
            
        logger.debug(f"Evaluating {len(available_skills)} skills for prompt")
        
        # Score all skills
        scored_skills = []
        for skill in available_skills.values():
            # Check MCP server requirements first
            if skill.metadata.requiredMcpServers:
                missing_servers = set(skill.metadata.requiredMcpServers) - set(available_mcp_servers)
                if missing_servers:
                    logger.debug(
                        f"Skipping skill '{skill.name}': missing required MCP servers: {missing_servers}"
                    )
                    continue
            
            score = self._score_skill(prompt, skill)
            scored_skills.append(score)
            
            logger.debug(
                f"Skill '{skill.name}' scored {score.score:.3f}: {score.details}"
            )
        
        if not scored_skills:
            logger.debug("No skills passed MCP server requirements")
            return None
        
        # Sort by score (descending) then by name (ascending) for tie-breaking
        scored_skills.sort(key=lambda x: (-x.score, x.skill.name))
        
        # Apply minimum score threshold
        min_score = self.config.skills.selection.minScore
        best_score = scored_skills[0]
        
        if best_score.score < min_score:
            logger.debug(
                f"Best skill '{best_score.skill.name}' score {best_score.score:.3f} "
                f"below threshold {min_score}"
            )
            return None
        
        # In v1, enforce topK = 1
        if self.config.skills.selection.topK != 1:
            logger.warning(f"topK={self.config.skills.selection.topK} not supported, using 1")
        
        selected_skill = best_score.skill
        logger.info(f"Selected skill '{selected_skill.name}' with score {best_score.score:.3f}")
        
        # Log rejection reasons for non-selected skills
        for score in scored_skills[1:]:
            if score.score >= min_score:
                logger.debug(f"Rejected skill '{score.skill.name}': lower score {score.score:.3f}")
            else:
                logger.debug(f"Rejected skill '{score.skill.name}': below threshold {score.score:.3f}")
        
        return selected_skill
    
    def _score_skill(self, prompt: str, skill: Skill) -> SkillScore:
        """Score a skill against a prompt.
        
        Args:
            prompt: User prompt
            skill: Skill to score
            
        Returns:
            SkillScore with overall score and component details
        """
        # Normalize prompt for matching
        prompt_tokens = self._tokenize(prompt)
        
        # Score components
        details = {}
        
        # 1. Exact phrase matches (weight: 0.50)
        phrase_score = self._score_phrase_matches(prompt, skill)
        details['phrase_matches'] = phrase_score
        
        # 2. Token overlap (weight: 0.35)
        token_score = self._score_token_overlap(prompt_tokens, skill)
        details['token_overlap'] = token_score
        
        # 3. Fuzzy token similarity (weight: 0.15)
        fuzzy_score = 0.0
        if self.config.skills.selection.fuzzyMatch:
            fuzzy_score = self._score_fuzzy_similarity(prompt_tokens, skill)
        details['fuzzy_similarity'] = fuzzy_score
        
        # Calculate weighted final score
        final_score = (
            phrase_score * 0.50 +
            token_score * 0.35 +
            fuzzy_score * 0.15
        )
        
        # Normalize to 0..1 range (should already be normalized by components)
        final_score = max(0.0, min(1.0, final_score))
        
        return SkillScore(
            skill=skill,
            score=final_score,
            details=details
        )
    
    def _score_phrase_matches(self, prompt: str, skill: Skill) -> float:
        """Score exact phrase matches.
        
        Args:
            prompt: User prompt (case insensitive)
            skill: Skill to score
            
        Returns:
            Score from 0.0 to 1.0
        """
        prompt_lower = prompt.lower()
        
        # Check name and description for exact phrase matches
        text_sources = [
            skill.metadata.name.lower(),
            skill.metadata.description.lower(),
        ]
        
        # Add preferred tools if available
        if skill.metadata.preferredTools:
            for tool in skill.metadata.preferredTools:
                text_sources.append(tool.lower())
        
        # Find matches
        matches = 0
        total_phrases = 0
        
        for source_text in text_sources:
            # Split into potential phrases (3+ character words)
            phrases = [p.strip() for p in re.findall(r'\b\w{3,}\b', source_text)]
            total_phrases += len(phrases)
            
            for phrase in phrases:
                if phrase in prompt_lower:
                    matches += 1
        
        if total_phrases == 0:
            return 0.0
        
        return matches / total_phrases
    
    def _score_token_overlap(self, prompt_tokens: List[str], skill: Skill) -> float:
        """Score token overlap between prompt and skill metadata.
        
        Args:
            prompt_tokens: Tokenized prompt
            skill: Skill to score
            
        Returns:
            Score from 0.0 to 1.0
        """
        if not prompt_tokens:
            return 0.0
        
        # Get skill tokens
        skill_text = " ".join([
            skill.metadata.name,
            skill.metadata.description,
        ])
        
        if skill.metadata.preferredTools:
            skill_text += " " + " ".join(skill.metadata.preferredTools)
        
        skill_tokens = self._tokenize(skill_text)
        
        if not skill_tokens:
            return 0.0
        
        # Calculate overlap
        prompt_set = set(prompt_tokens)
        skill_set = set(skill_tokens)
        
        overlap = len(prompt_set & skill_set)
        union_size = len(prompt_set | skill_set)
        
        if union_size == 0:
            return 0.0
        
        # Use Jaccard similarity
        return overlap / union_size
    
    def _score_fuzzy_similarity(self, prompt_tokens: List[str], skill: Skill) -> float:
        """Score fuzzy token similarity using edit distance.
        
        Args:
            prompt_tokens: Tokenized prompt
            skill: Skill to score
            
        Returns:
            Score from 0.0 to 1.0
        """
        if not prompt_tokens:
            return 0.0
        
        # Get skill tokens
        skill_text = " ".join([
            skill.metadata.name,
            skill.metadata.description,
        ])
        skill_tokens = self._tokenize(skill_text)
        
        if not skill_tokens:
            return 0.0
        
        # Find best fuzzy matches for each prompt token
        total_similarity = 0.0
        
        for prompt_token in prompt_tokens:
            best_similarity = 0.0
            
            for skill_token in skill_tokens:
                similarity = self._token_similarity(prompt_token, skill_token)
                best_similarity = max(best_similarity, similarity)
            
            total_similarity += best_similarity
        
        return total_similarity / len(prompt_tokens)
    
    def _token_similarity(self, token1: str, token2: str) -> float:
        """Calculate similarity between two tokens using edit distance.
        
        Args:
            token1: First token
            token2: Second token
            
        Returns:
            Similarity from 0.0 to 1.0
        """
        if token1 == token2:
            return 1.0
        
        if not token1 or not token2:
            return 0.0
        
        # Use Levenshtein distance
        distance = self._edit_distance(token1, token2)
        max_len = max(len(token1), len(token2))
        
        return 1.0 - (distance / max_len)
    
    def _edit_distance(self, s1: str, s2: str) -> int:
        """Calculate edit distance between two strings.
        
        Args:
            s1: First string
            s2: Second string
            
        Returns:
            Edit distance
        """
        if len(s1) < len(s2):
            s1, s2 = s2, s1
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                
                current_row.append(min(insertions, deletions, substitutions))
            
            previous_row = current_row
        
        return previous_row[-1]
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into normalized tokens.
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of normalized tokens
        """
        # Convert to lowercase and extract alphanumeric words
        tokens = re.findall(r'\b[a-zA-Z0-9]{2,}\b', text.lower())
        return tokens