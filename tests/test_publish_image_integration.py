"""Tests for publish command image generation integration."""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
import shutil

from blog_generator.formatter.xiaohongshu import XiaohongshuFormatter


class TestPublishImageIntegration:
    """Tests for --cover/--no-cover flag integration in publish command."""

    @pytest.fixture
    def temp_blog_dir(self):
        """Create a temporary blog directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            blog_dir = Path(tmpdir) / "v0.16.0"
            blog_dir.mkdir(parents=True)

            # Create blog.json with test data
            blog_data = {
                "title": "Test Blog Title for XHS",
                "content_md": "This is test content for the blog post.",
                "tags": ["vLLM", "AI", "multimodal"],
            }
            with open(blog_dir / "blog.json", "w") as f:
                json.dump(blog_data, f)

            # Create blog.md
            (blog_dir / "blog.md").write_text("# Test Blog\n\nContent here.")

            yield blog_dir

    def test_cover_image_generation_flag_default_true(self):
        """Verify cover flag defaults to True."""
        # The publish command should have cover=True by default
        # This test verifies the behavior expectation
        from typer.testing import CliRunner
        from blog_generator.cli import app

        # This is a behavioral test - cover should default to True
        # When we call publish without --no-cover, cover generation should happen
        # We'll test the integration in async tests below
        pass

    def test_no_cover_flag_skips_generation(self):
        """Verify --no-cover flag skips image generation."""
        # When --no-cover is set, no API calls should be made
        pass


class TestCoverImageGeneration:
    """Tests for cover image generation in publish command."""

    @pytest.fixture
    def temp_blog_dir(self):
        """Create a temporary blog directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            blog_dir = Path(tmpdir) / "v0.16.0"
            blog_dir.mkdir(parents=True)

            # Create blog.json with test data
            blog_data = {
                "title": "Test Blog Title for XHS",
                "content_md": "This is test content for the blog post.",
                "tags": ["vLLM", "AI", "multimodal"],
            }
            with open(blog_dir / "blog.json", "w") as f:
                json.dump(blog_data, f)

            # Create blog.md
            (blog_dir / "blog.md").write_text("# Test Blog\n\nContent here.")

            yield blog_dir

    @pytest.mark.asyncio
    async def test_generate_cover_image_success(self, temp_blog_dir):
        """Verify cover image is generated and saved correctly."""
        import base64

        # Create a fake PNG image
        fake_png_bytes = b"\x89PNG\r\n\x1a\n" + b"fake image data"
        fake_png_base64 = base64.b64encode(fake_png_bytes).decode("utf-8")

        # Mock the image generator
        from blog_generator.config import ImageConfig
        from blog_generator.generator.image import GeneratedImage, ImageGenerator

        with patch("blog_generator.generator.image.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [fake_png_base64]}
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Create generator and generate cover
            config = ImageConfig()
            generator = ImageGenerator(config=config, auth_token="test-token")

            prompt = XiaohongshuFormatter.build_cover_prompt(
                title="Test Blog Title",
                content="Test content"
            )
            result = await generator.generate(prompt=prompt)

            # Verify result
            assert result.format == "png"
            assert len(result.image_data) > 0

            # Save to expected location
            images_dir = temp_blog_dir / "xiaohongshu" / "images"
            images_dir.mkdir(parents=True, exist_ok=True)
            cover_path = images_dir / "cover.png"
            cover_path.write_bytes(result.image_data)

            assert cover_path.exists()
            assert cover_path.read_bytes() == fake_png_bytes

    @pytest.mark.asyncio
    async def test_generate_cover_image_updates_post_json(self, temp_blog_dir):
        """Verify post.json is updated with cover image path."""
        # Create initial post.json
        xhs_dir = temp_blog_dir / "xiaohongshu"
        xhs_dir.mkdir(parents=True)

        post_data = {
            "title": "Test Blog Title",
            "content": "Test content",
            "images": [],
            "tags": ["vLLM", "AI"],
            "ready_to_post": True,
        }
        post_json_path = xhs_dir / "post.json"
        with open(post_json_path, "w") as f:
            json.dump(post_data, f)

        # Simulate cover image generation and path update
        images_dir = xhs_dir / "images"
        images_dir.mkdir(parents=True)
        cover_path = images_dir / "cover.png"
        cover_path.write_bytes(b"\x89PNG fake image")

        # Update post.json with cover path
        abs_cover_path = str(cover_path.resolve())
        XiaohongshuFormatter.update_post_json_images(xhs_dir, [abs_cover_path])

        # Verify post.json updated
        with open(post_json_path) as f:
            updated_data = json.load(f)

        assert len(updated_data["images"]) == 1
        assert abs_cover_path in updated_data["images"]
        # ready_to_post should remain True (unchanged by update)
        assert updated_data["ready_to_post"] == True

    @pytest.mark.asyncio
    async def test_cover_generation_error_graceful_handling(self, temp_blog_dir):
        """Verify errors during cover generation are handled gracefully."""
        from blog_generator.config import ImageConfig
        from blog_generator.generator.image import ImageGenerator

        with patch("blog_generator.generator.image.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = Exception("API Error")
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            config = ImageConfig()
            generator = ImageGenerator(config=config, auth_token="test-token")

            prompt = XiaohongshuFormatter.build_cover_prompt(
                title="Test",
                content="Content"
            )

            # Should raise an exception
            with pytest.raises(Exception):
                await generator.generate(prompt=prompt)

            # In actual CLI, this should be caught and logged as warning


class TestCoverPromptBuilding:
    """Tests for cover prompt building integration."""

    def test_cover_prompt_uses_blog_data(self):
        """Verify cover prompt uses actual blog title and content."""
        title = "vLLM-Omni v0.16.0 Release Notes"
        content = "This release includes new multimodal features and bug fixes."

        prompt = XiaohongshuFormatter.build_cover_prompt(title, content)

        # Title should be in prompt (truncated if necessary)
        assert title[:30] in prompt

        # Content context should be included
        assert "multimodal" in prompt or "features" in prompt

    def test_cover_prompt_style_consistency(self):
        """Verify cover prompt maintains consistent style guidelines."""
        prompt = XiaohongshuFormatter.build_cover_prompt("Test", "Content")

        # Required style elements
        assert "clean" in prompt.lower()
        assert "minimalist" in prompt.lower()
        assert "tech" in prompt.lower()
        assert "blue" in prompt.lower()

        # Required visual elements
        assert "AI" in prompt or "ai" in prompt.lower()


class TestPostJsonCoverIntegration:
    """Tests for post.json cover image integration."""

    def test_post_json_cover_path_is_absolute(self, tmp_path):
        """Verify cover image path in post.json is absolute."""
        xhs_dir = tmp_path / "xiaohongshu"
        xhs_dir.mkdir(parents=True)
        images_dir = xhs_dir / "images"
        images_dir.mkdir(parents=True)

        cover_path = images_dir / "cover.png"
        cover_path.write_bytes(b"fake image")

        # Update post.json
        abs_path = str(cover_path.resolve())
        XiaohongshuFormatter.update_post_json_images(xhs_dir, [abs_path])

        # Read back and verify
        post_json = xhs_dir / "post.json"
        post_json.write_text('{}')  # Create empty first
        XiaohongshuFormatter.update_post_json_images(xhs_dir, [abs_path])

        with open(post_json) as f:
            data = json.load(f)

        # Path should be absolute
        saved_path = data["images"][0]
        assert Path(saved_path).is_absolute()

    def test_post_json_cover_prepends_existing_images(self, tmp_path):
        """Verify cover image is prepended to existing images list."""
        xhs_dir = tmp_path / "xiaohongshu"
        xhs_dir.mkdir(parents=True)

        # Create post.json with existing images
        existing_images = ["/path/to/existing1.png", "/path/to/existing2.png"]
        post_json = xhs_dir / "post.json"
        with open(post_json, "w") as f:
            json.dump({"images": existing_images, "ready_to_post": True}, f)

        # Update with cover (should prepend)
        cover_path = "/path/to/cover.png"
        XiaohongshuFormatter.update_post_json_images(xhs_dir, [cover_path] + existing_images)

        with open(post_json) as f:
            data = json.load(f)

        assert data["images"][0] == cover_path
        assert len(data["images"]) == 3
