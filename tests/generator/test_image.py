"""Tests for ImageGenerator class."""

import base64
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import fields

from blog_generator.config import ImageConfig
from blog_generator.generator.image import GeneratedImage, ImageGenerator


class TestGeneratedImageDataclass:
    """Tests for GeneratedImage dataclass."""

    def test_generated_image_dataclass(self):
        """Verify dataclass structure with image_data, format, prompt fields."""
        # Verify dataclass has the correct fields
        field_names = {f.name for f in fields(GeneratedImage)}
        assert field_names == {"image_data", "format", "prompt"}

        # Verify field types (optional but good for documentation)
        field_types = {f.name: f.type for f in fields(GeneratedImage)}
        assert field_types["image_data"] == bytes
        assert field_types["format"] == str
        assert field_types["prompt"] == str

    def test_generated_image_creation(self):
        """Verify GeneratedImage can be created with expected values."""
        image_data = b"\x89PNG test data"
        generated = GeneratedImage(
            image_data=image_data,
            format="png",
            prompt="a beautiful sunset"
        )

        assert generated.image_data == image_data
        assert generated.format == "png"
        assert generated.prompt == "a beautiful sunset"


class TestImageGeneratorInit:
    """Tests for ImageGenerator initialization."""

    def test_image_generator_init(self):
        """Verify initialization with config and auth_token."""
        config = ImageConfig(
            base_url="https://test.api.com",
            model="Test-Model",
            size="512x512"
        )
        auth_token = "test-auth-token"

        generator = ImageGenerator(config=config, auth_token=auth_token)

        assert generator.config == config
        assert generator.auth_token == auth_token
        assert generator.config.base_url == "https://test.api.com"
        assert generator.config.model == "Test-Model"
        assert generator.config.size == "512x512"


class TestImageGeneratorGenerate:
    """Tests for ImageGenerator generate method."""

    @pytest.mark.asyncio
    async def test_generate_image_success(self):
        """Verify async generation with mocked httpx client."""
        config = ImageConfig(
            base_url="https://test.api.com",
            model="Test-Model",
            size="1024x1024"
        )
        auth_token = "test-auth-token"
        generator = ImageGenerator(config=config, auth_token=auth_token)

        # Create a fake PNG image (starts with PNG magic bytes)
        fake_png_bytes = b"\x89PNG\r\n\x1a\n" + b"fake image data here"
        fake_png_base64 = base64.b64encode(fake_png_bytes).decode("utf-8")

        # Mock the httpx AsyncClient
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [fake_png_base64]
        }

        with patch("blog_generator.generator.image.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await generator.generate(prompt="a beautiful sunset")

            # Verify the result
            assert isinstance(result, GeneratedImage)
            assert result.image_data == fake_png_bytes
            assert result.format == "png"
            assert result.prompt == "a beautiful sunset"

            # Verify the API call was made correctly
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args

            # Check URL
            assert call_args[0][0] == "https://test.api.com/images/generations"

            # Check headers
            headers = call_args[1]["headers"]
            assert headers["Authorization"] == "Bearer test-auth-token"
            assert headers["Content-Type"] == "application/json"

            # Check body
            body = call_args[1]["json"]
            assert body["model"] == "Test-Model"
            assert body["prompt"] == "a beautiful sunset"
            assert body["size"] == "1024x1024"
            assert body["response_format"] == "b64_json"

    @pytest.mark.asyncio
    async def test_generate_image_jpeg_format(self):
        """Verify format detection for JPEG images."""
        config = ImageConfig()
        auth_token = "test-token"
        generator = ImageGenerator(config=config, auth_token=auth_token)

        # Create a fake JPEG image (starts with JPEG magic bytes)
        fake_jpeg_bytes = b"\xff\xd8\xff" + b"fake jpeg data"
        fake_jpeg_base64 = base64.b64encode(fake_jpeg_bytes).decode("utf-8")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [fake_jpeg_base64]
        }

        with patch("blog_generator.generator.image.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await generator.generate(prompt="test prompt")

            assert result.format == "jpeg"

    @pytest.mark.asyncio
    async def test_generate_image_custom_size(self):
        """Verify custom size parameter is used."""
        config = ImageConfig(size="1024x1024")
        auth_token = "test-token"
        generator = ImageGenerator(config=config, auth_token=auth_token)

        fake_png_bytes = b"\x89PNG test data"
        fake_png_base64 = base64.b64encode(fake_png_bytes).decode("utf-8")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [fake_png_base64]}

        with patch("blog_generator.generator.image.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await generator.generate(prompt="test", size="512x512")

            # Verify custom size was used
            call_args = mock_client.post.call_args
            body = call_args[1]["json"]
            assert body["size"] == "512x512"

    @pytest.mark.asyncio
    async def test_generate_image_api_error(self):
        """Verify error handling when API returns error."""
        config = ImageConfig()
        auth_token = "test-token"
        generator = ImageGenerator(config=config, auth_token=auth_token)

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = Exception("HTTP 401: Unauthorized")

        with patch("blog_generator.generator.image.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            with pytest.raises(Exception, match="Unauthorized"):
                await generator.generate(prompt="test")
