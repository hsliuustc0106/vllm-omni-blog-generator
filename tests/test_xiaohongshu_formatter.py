"""Tests for XiaohongshuFormatter class."""

import pytest

from blog_generator.formatter.xiaohongshu import XiaohongshuFormatter


class TestBuildCoverPrompt:
    """Tests for build_cover_prompt static method."""

    def test_build_cover_prompt_contains_title(self):
        """Verify prompt contains the title."""
        title = "vLLM-Omni Multimodal Features"
        content = "This is some blog content about vLLM-Omni features."

        prompt = XiaohongshuFormatter.build_cover_prompt(title, content)

        assert title[:30] in prompt
        assert "vLLM-Omni" in prompt

    def test_build_cover_prompt_contains_styling(self):
        """Verify prompt contains required styling elements."""
        title = "Test Title"
        content = "Some content here."

        prompt = XiaohongshuFormatter.build_cover_prompt(title, content)

        # Check for required style elements
        assert "clean" in prompt.lower()
        assert "minimalist" in prompt.lower()
        assert "tech" in prompt.lower()

    def test_build_cover_prompt_contains_colors(self):
        """Verify prompt contains blue gradient and white accents."""
        title = "Test"
        content = "Content"

        prompt = XiaohongshuFormatter.build_cover_prompt(title, content)

        assert "blue" in prompt.lower()
        assert "gradient" in prompt.lower()
        assert "white" in prompt.lower()

    def test_build_cover_prompt_contains_elements(self):
        """Verify prompt contains AI/cloud/network visualization elements."""
        title = "Test"
        content = "Content"

        prompt = XiaohongshuFormatter.build_cover_prompt(title, content)

        assert "AI" in prompt or "ai" in prompt.lower()
        assert "cloud" in prompt.lower() or "network" in prompt.lower()

    def test_build_cover_prompt_truncates_long_title(self):
        """Verify long titles are truncated to 30 chars for text overlay."""
        # Create a title longer than 30 chars
        long_title = "This is a very long title that should be truncated"
        content = "Some content here."

        prompt = XiaohongshuFormatter.build_cover_prompt(long_title, content)

        # The prompt should contain the truncated version (30 chars max)
        # Find the text overlay section and verify truncation
        assert "This is a very long title tha" in prompt  # First 30 chars
        # Full long title should NOT appear
        assert long_title not in prompt

    def test_build_cover_prompt_includes_content_context(self):
        """Verify prompt includes first 200 chars of content for context."""
        title = "Test Title"
        # Create content longer than 200 chars
        long_content = "A" * 300

        prompt = XiaohongshuFormatter.build_cover_prompt(title, long_content)

        # Should include first 200 chars
        assert "A" * 200 in prompt
        # Should NOT include beyond 200
        assert "A" * 201 not in prompt

    def test_build_cover_prompt_short_content_unchanged(self):
        """Verify short content is included fully."""
        title = "Test"
        short_content = "Short content here."

        prompt = XiaohongshuFormatter.build_cover_prompt(title, short_content)

        assert short_content in prompt

    def test_build_cover_prompt_returns_string(self):
        """Verify method returns a string."""
        title = "Test"
        content = "Content"

        prompt = XiaohongshuFormatter.build_cover_prompt(title, content)

        assert isinstance(prompt, str)
        assert len(prompt) > 0
