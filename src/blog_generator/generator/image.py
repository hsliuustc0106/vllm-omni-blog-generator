"""Image generation using BigModel's GLM-Image API."""

import base64
import re
from dataclasses import dataclass
from typing import Optional

import httpx

from blog_generator.config import ImageConfig


@dataclass
class GeneratedImage:
    """Container for a generated image."""
    image_data: bytes
    format: str
    prompt: str


class ImageGenerator:
    """Generate images using BigModel's GLM-Image API."""

    def __init__(self, config: ImageConfig, auth_token: str):
        """Initialize the image generator.

        Args:
            config: Image generation configuration.
            auth_token: BigModel API authentication token.
        """
        self.config = config
        self.auth_token = auth_token

    async def generate(self, prompt: str, size: Optional[str] = None) -> GeneratedImage:
        """Generate an image from a text prompt.

        Args:
            prompt: Text description of the image to generate.
            size: Image size (e.g., "1024x1024"). Uses config default if not provided.

        Returns:
            GeneratedImage containing the image data, format, and prompt.

        Raises:
            ValueError: If prompt is empty, size format is invalid, or API response is malformed.
            httpx.HTTPStatusError: If the API request fails.
        """
        # Input validation for prompt
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty or whitespace only")

        # Input validation for size
        image_size = size or self.config.size
        if not re.match(r"^\d+x\d+$", image_size):
            raise ValueError(f"Invalid size format: '{image_size}'. Expected format: 'WxH' (e.g., '1024x1024')")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.config.base_url}/images/generations",
                headers={
                    "Authorization": f"Bearer {self.auth_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.config.model,
                    "prompt": prompt,
                    "size": image_size,
                    "response_format": "b64_json",
                },
            )
            response.raise_for_status()

            try:
                data = response.json()
            except Exception as e:
                raise ValueError(f"Invalid API response format: {e}") from e

            try:
                base64_image = data["data"][0]
                image_data = base64.b64decode(base64_image)
            except (KeyError, IndexError) as e:
                raise ValueError(f"Invalid API response format: missing 'data[0]' field: {e}") from e
            except Exception as e:
                raise ValueError(f"Failed to decode base64 image data: {e}") from e

            # Detect format from magic bytes
            image_format = self._detect_format(image_data)

            return GeneratedImage(
                image_data=image_data,
                format=image_format,
                prompt=prompt,
            )

    def _detect_format(self, image_data: bytes) -> str:
        """Detect image format from magic bytes.

        Args:
            image_data: Raw image bytes.

        Returns:
            Format string: "png", "jpeg", or "unknown".
        """
        if image_data.startswith(b"\x89PNG"):
            return "png"
        elif image_data.startswith(b"\xff\xd8\xff"):
            return "jpeg"
        else:
            return "unknown"
