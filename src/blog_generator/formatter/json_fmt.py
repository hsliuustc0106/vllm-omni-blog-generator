"""JSON output formatter."""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

from blog_generator.generator.claude import BlogDraft
from blog_generator.fetcher.github import Release


class BlogValidationError(Exception):
    """Raised when blog.json validation fails."""
    pass


class JsonFormatter:
    """Formatter for blog.json files."""

    # Required fields for a valid blog.json
    REQUIRED_FIELDS = [
        "title",
        "content_md",
        "tags",
    ]

    # Optional but recommended fields
    OPTIONAL_FIELDS = [
        "version",
        "release_date",
        "language",
        "summary",
        "generated_at",
        "source_commits",
        "source_prs",
        "source_issues",
    ]

    @staticmethod
    def save(
        draft: BlogDraft,
        release: Optional[Release],
        source_commits: List[str],
        source_prs: List[int],
        source_issues: List[int],
        output_path: Path,
    ) -> None:
        """Save blog as JSON file."""
        data = {
            "version": release.tag_name if release else None,
            "release_date": release.published_at[:10] if release else None,
            "language": "zh",
            "title": draft.title,
            "summary": draft.summary,
            "tags": draft.tags,
            "content_md": draft.content,
            "generated_at": datetime.now().isoformat(),
            "source_commits": source_commits,
            "source_prs": source_prs,
            "source_issues": source_issues,
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def validate(blog_data: Dict[str, Any]) -> List[str]:
        """Validate blog.json has required fields.

        Args:
            blog_data: Parsed blog.json data

        Returns:
            List of validation warnings (empty if all valid)

        Raises:
            BlogValidationError: If required fields are missing
        """
        warnings = []

        # Check required fields
        missing_required = []
        for field in JsonFormatter.REQUIRED_FIELDS:
            if field not in blog_data:
                missing_required.append(field)
            elif not blog_data[field]:
                warnings.append(f"Required field '{field}' is empty")

        if missing_required:
            raise BlogValidationError(
                f"Missing required fields: {', '.join(missing_required)}"
            )

        # Check for recommended optional fields
        for field in JsonFormatter.OPTIONAL_FIELDS:
            if field not in blog_data:
                warnings.append(f"Optional field '{field}' is missing")

        # Validate source_prs and source_issues are lists
        if "source_prs" in blog_data and not isinstance(blog_data["source_prs"], list):
            warnings.append("source_prs should be a list")
        if "source_issues" in blog_data and not isinstance(blog_data["source_issues"], list):
            warnings.append("source_issues should be a list")

        # Validate tags is a list
        if "tags" in blog_data and not isinstance(blog_data["tags"], list):
            warnings.append("tags should be a list")

        return warnings
