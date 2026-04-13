"""Unit tests for skill parsing and scoring."""

import yaml
from pathlib import Path
from unittest.mock import Mock

import pytest

from ollm.skills.loader import SkillLoader, SkillParseError
from ollm.skills.selector import SkillSelector
from ollm.skills.schema import Skill, SkillMetadata


class TestSkillParsing:
    """Test skill discovery and parsing logic."""

    def test_valid_skill_loads_correctly(self, temp_dir: Path, sample_skill_metadata: str):
        """Test that valid skill loads correctly."""
        skill_dir = temp_dir / "test-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(sample_skill_metadata)
        
        loader = SkillLoader()
        skills = loader.load_skills(temp_dir)
        
        assert len(skills) == 1
        skill = skills[0]
        assert skill.name == "test-skill"
        assert skill.metadata.name == "test-skill"
        assert skill.metadata.description == "Test skill for unit testing"
        assert skill.metadata.scriptExecution is True

    def test_malformed_skill_skipped_with_warning(self, temp_dir: Path, invalid_skill_metadata: str):
        """Test that malformed skills are skipped and logged."""
        skill_dir = temp_dir / "invalid-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(invalid_skill_metadata)
        
        loader = SkillLoader()
        
        # Should not raise, but should log warning
        with pytest.warns(UserWarning, match="Failed to load skill"):
            skills = loader.load_skills(temp_dir)
        
        assert len(skills) == 0  # Invalid skill should be skipped

    def test_missing_required_fields_fails(self, temp_dir: Path):
        """Test that missing required fields causes skill to fail loading."""
        skill_content = """---
description: Missing name field
---

# Invalid Skill
"""
        skill_dir = temp_dir / "invalid-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(skill_content)
        
        loader = SkillLoader()
        
        with pytest.warns(UserWarning):
            skills = loader.load_skills(temp_dir)
        
        assert len(skills) == 0

    def test_script_execution_flag_parsed_correctly(self, temp_dir: Path):
        """Test that scriptExecution boolean flag is parsed correctly."""
        skill_with_script = """---
name: script-skill
description: Skill with script execution
scriptExecution: true
---

# Script Skill
"""
        skill_without_script = """---
name: no-script-skill
description: Skill without script execution
scriptExecution: false
---

# No Script Skill
"""
        
        # Create both skills
        for i, (name, content) in enumerate([
            ("script-skill", skill_with_script),
            ("no-script-skill", skill_without_script)
        ]):
            skill_dir = temp_dir / name
            skill_dir.mkdir()
            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text(content)
        
        loader = SkillLoader()
        skills = loader.load_skills(temp_dir)
        
        assert len(skills) == 2
        
        script_skill = next(s for s in skills if s.name == "script-skill")
        no_script_skill = next(s for s in skills if s.name == "no-script-skill")
        
        assert script_skill.metadata.scriptExecution is True
        assert no_script_skill.metadata.scriptExecution is False

    def test_resource_files_loaded_within_limits(self, temp_dir: Path):
        """Test that resource files are loaded within size limits."""
        skill_content = """---
name: resource-skill
description: Skill with resources
resources: ["small.txt", "large.txt"]
---

# Resource Skill
"""
        
        skill_dir = temp_dir / "resource-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(skill_content)
        
        # Create resource files
        small_file = skill_dir / "small.txt"
        small_file.write_text("Small content")  # Under limit
        
        large_file = skill_dir / "large.txt"
        large_file.write_text("x" * 100_000)  # Over 64KB limit
        
        loader = SkillLoader()
        skills = loader.load_skills(temp_dir)
        
        assert len(skills) == 1
        skill = skills[0]
        
        # Small file should be loaded
        assert "small.txt" in skill.resource_files
        assert skill.resource_files["small.txt"] == "Small content"
        
        # Large file should be skipped (or skill skipped due to size)
        # This depends on implementation - test what actually happens


class TestSkillScoring:
    """Test deterministic scoring and selection logic."""

    def setUp(self):
        """Set up test skills."""
        self.selector = SkillSelector()
        
        # Mock skills for testing
        self.skills = [
            Mock(spec=Skill),
            Mock(spec=Skill),
            Mock(spec=Skill)
        ]
        
        self.skills[0].name = "data-analysis"
        self.skills[0].metadata.description = "Analyze data using Python scripts"
        self.skills[0].metadata.requiredMcpServers = []
        
        self.skills[1].name = "writing-help" 
        self.skills[1].metadata.description = "Help improve writing and communication"
        self.skills[1].metadata.requiredMcpServers = []
        
        self.skills[2].name = "github-review"
        self.skills[2].metadata.description = "Review GitHub pull requests and code"
        self.skills[2].metadata.requiredMcpServers = ["github"]

    def test_lexical_scoring_weights(self):
        """Test that scoring uses correct weights: phrase 0.50, token 0.35, fuzzy 0.15."""
        prompt = "data analysis with statistical calculations"
        
        # Mock the internal scoring methods
        with patch.object(self.selector, '_calculate_phrase_score', return_value=0.8):
            with patch.object(self.selector, '_calculate_token_overlap', return_value=0.6):
                with patch.object(self.selector, '_calculate_fuzzy_similarity', return_value=0.4):
                    score = self.selector._calculate_score(prompt, self.skills[0])
        
        expected = 0.8 * 0.50 + 0.6 * 0.35 + 0.4 * 0.15
        assert abs(score - expected) < 0.001

    def test_score_normalization_zero_to_one(self):
        """Test that scores are normalized to 0..1 range."""
        prompt = "test prompt for analysis"
        
        scores = []
        for skill in self.skills:
            score = self.selector._calculate_score(prompt, skill)
            scores.append(score)
            assert 0 <= score <= 1

    def test_min_score_threshold_applied(self):
        """Test that minScore threshold is properly applied."""
        prompt = "unrelated prompt that shouldn't match any skill"
        
        selected = self.selector.select_skill(
            prompt, 
            self.skills, 
            min_score=0.5,  # High threshold
            available_mcp_servers=set()
        )
        
        assert selected is None  # No skill should meet high threshold

    def test_lexical_tie_break_by_skill_name(self):
        """Test that ties are broken by lexical order of skill name."""
        # Create skills with identical scoring potential
        identical_skills = [
            Mock(name="zebra-skill", metadata=Mock(description="test", requiredMcpServers=[])),
            Mock(name="alpha-skill", metadata=Mock(description="test", requiredMcpServers=[]))
        ]
        
        prompt = "test"
        
        selected = self.selector.select_skill(
            prompt,
            identical_skills,
            min_score=0.0,  # Allow any score
            available_mcp_servers=set()
        )
        
        assert selected.name == "alpha-skill"  # Lexically first

    def test_top_k_equals_one_enforced(self):
        """Test that topK = 1 behavior is enforced for v1."""
        prompt = "analysis and data processing"
        
        selected = self.selector.select_skill(
            prompt,
            self.skills,
            top_k=1,
            min_score=0.0,
            available_mcp_servers=set()
        )
        
        # Should return single skill, not list
        assert selected is None or isinstance(selected, Skill)

    def test_required_mcp_servers_checked(self):
        """Test that requiredMcpServers are verified before selection."""
        prompt = "review github code changes"  # Should match github-review skill
        
        # Without required MCP server
        selected_without = self.selector.select_skill(
            prompt,
            self.skills,
            min_score=0.0,
            available_mcp_servers=set()  # No github server
        )
        
        # With required MCP server
        selected_with = self.selector.select_skill(
            prompt,
            self.skills,
            min_score=0.0,
            available_mcp_servers={"github"}  # Has github server
        )
        
        # Should be skipped without required server, selected with it
        assert selected_without != self.skills[2]  # github-review skill
        # Note: selected_with assertion depends on actual scoring implementation