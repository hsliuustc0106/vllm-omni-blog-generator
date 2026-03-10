"""Data fetcher module."""

from blog_generator.fetcher.github import GitHubFetcher
from blog_generator.fetcher.docs import DocFetcher
from blog_generator.fetcher.images import (
    ImageInput,
    load_image,
    extract_image_urls_from_markdown,
    image_paths_for_embed,
)

__all__ = [
    "GitHubFetcher",
    "DocFetcher",
    "ImageInput",
    "load_image",
    "extract_image_urls_from_markdown",
    "image_paths_for_embed",
]
