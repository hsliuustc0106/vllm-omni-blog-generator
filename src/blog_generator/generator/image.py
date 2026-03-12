"""Image generation using BigModel's GLM-Image API."""

import base64
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
            httpx.HTTPStatusError: If the API request fails.
        """
        image_size = size or self.config.size

        async with httpx.AsyncClient() as client:
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

            data = response.json()
            base64_image = data["data"][0]
            image_data = base64.b64decode(base64_image)

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
