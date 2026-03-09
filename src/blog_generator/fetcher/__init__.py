"""Data fetcher module."""

from blog_generator.fetcher.github import GitHubFetcher
from blog_generator.fetcher.docs import DocFetcher

__all__ = ["GitHubFetcher", "DocFetcher"]
