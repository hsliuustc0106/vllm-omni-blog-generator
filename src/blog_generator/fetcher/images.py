"""Image fetcher for blog generation context."""

import base64
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx
from dataclasses import dataclass

# Markdown image syntax: ![alt](url) or ![alt](url "title")
IMAGE_URL_PATTERN = re.compile(r"!\[[^\]]*\]\s*\(\s*([^)\s]+)\s*\)")

ALLOWED_MEDIA_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}

EXTENSION_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


@dataclass
class ImageInput:
    """Loaded image for API input."""

    media_type: str
    data_base64: str
    source: str


def is_url(s: str) -> bool:
    """Check if string is a URL."""
    return s.startswith("http://") or s.startswith("https://")


def _safe_filename_from_source(source: str) -> str:
    """Derive a safe filename from URL or path. Used for embedding images in blog output."""
    if is_url(source):
        name = Path(urlparse(source).path).name or "image"
    else:
        name = Path(source).name or "image"
    # Sanitize: keep alphanumeric, dash, underscore, dot
    safe = re.sub(r"[^\w\-.]", "_", name)
    if not safe.strip("_"):
        safe = "image"
    if not any(safe.lower().endswith(ext) for ext in EXTENSION_MEDIA_TYPES):
        safe = safe + ".png"
    return safe


def image_paths_for_embed(
    image_data: list[ImageInput],
    prefix: str = "images",
) -> list[tuple[str, str]]:
    """
    Compute (path, source) for each image so they can be saved under output_dir and
    referenced in markdown. Paths are unique (e.g. images/foo.png, images/foo_2.png).
    """
    seen: dict[str, int] = {}
    result: list[tuple[str, str]] = []
    for img in image_data:
        base_name = _safe_filename_from_source(img.source)
        key = base_name.lower()
        count = seen.get(key, 0) + 1
        seen[key] = count
        if count == 1:
            path = f"{prefix}/{base_name}"
        else:
            stem = Path(base_name).stem
            suffix = Path(base_name).suffix
            path = f"{prefix}/{stem}_{count}{suffix}"
        result.append((path, img.source))
    return result


def extract_image_urls_from_markdown(text: str) -> list[str]:
    """Extract image URLs from markdown (e.g. PR/issue body). Returns unique URLs in order."""
    if not text:
        return []
    urls = IMAGE_URL_PATTERN.findall(text)
    seen = set()
    unique = []
    for u in urls:
        u = u.strip()
        if u and u not in seen and (u.startswith("http://") or u.startswith("https://")):
            seen.add(u)
            unique.append(u)
    return unique


async def load_image(
    source: str,
    client: Optional[httpx.AsyncClient] = None,
) -> ImageInput:
    """Load image from URL or local path; return ImageInput with base64 data."""
    if is_url(source):
        if client is None:
            raise ValueError("httpx.AsyncClient required for URL image sources")
        response = await client.get(source)
        response.raise_for_status()
        raw = response.content
        media_type = (
            response.headers.get("content-type", "").split(";")[0].strip().lower()
        )
        if not media_type or media_type not in ALLOWED_MEDIA_TYPES:
            # Infer from URL path
            path_suffix = Path(urlparse(source).path).suffix.lower()
            media_type = EXTENSION_MEDIA_TYPES.get(path_suffix)
        if not media_type or media_type not in ALLOWED_MEDIA_TYPES:
            raise ValueError(f"Unsupported or unknown media type for URL: {source}")
    else:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {source}")
        raw = path.read_bytes()
        suffix = path.suffix.lower()
        media_type = EXTENSION_MEDIA_TYPES.get(suffix)
        if not media_type:
            raise ValueError(f"Unsupported image format: {suffix} (path: {source})")

    if media_type not in ALLOWED_MEDIA_TYPES:
        raise ValueError(f"Unsupported media type: {media_type}")

    data_base64 = base64.standard_b64encode(raw).decode("ascii")
    return ImageInput(media_type=media_type, data_base64=data_base64, source=source)
