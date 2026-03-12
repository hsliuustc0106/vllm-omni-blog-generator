"""Tests for configuration models."""

import pytest

from blog_generator.config import Config, ImageConfig


class TestImageConfig:
    """Tests for ImageConfig class."""

    def test_image_config_defaults(self):
        """Verify ImageConfig has correct defaults."""
        config = ImageConfig()

        assert config.base_url == "https://open.bigmodel.cn/api/paas/v4"
        assert config.model == "GLM-Image"
        assert config.size == "1024x1024"

    def test_image_config_custom_values(self):
        """Verify ImageConfig accepts custom values."""
        config = ImageConfig(
            base_url="https://custom.api.com",
            model="Custom-Model",
            size="512x512"
        )

        assert config.base_url == "https://custom.api.com"
        assert config.model == "Custom-Model"
        assert config.size == "512x512"


class TestConfigWithImage:
    """Tests for Config class with image section."""

    def test_config_with_image_section(self):
        """Verify Config loads with default image config when no image section provided."""
        config = Config(
            api={
                "anthropic_auth_token": "test-token"
            }
        )

        assert config.image is not None
        assert isinstance(config.image, ImageConfig)
        assert config.image.base_url == "https://open.bigmodel.cn/api/paas/v4"
        assert config.image.model == "GLM-Image"
        assert config.image.size == "1024x1024"

    def test_config_with_custom_image_settings(self):
        """Verify Config loads custom image settings."""
        config = Config(
            api={
                "anthropic_auth_token": "test-token"
            },
            image={
                "base_url": "https://custom.bigmodel.cn/api",
                "model": "Custom-Image-Model",
                "size": "2048x2048"
            }
        )

        assert config.image.base_url == "https://custom.bigmodel.cn/api"
        assert config.image.model == "Custom-Image-Model"
        assert config.image.size == "2048x2048"
