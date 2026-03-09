"""JSON output formatter."""

import json
from pathlib import Path
from datetime import datetime
from typing import List

from blog_generator.generator.claude import BlogDraft
from blog_generator.fetcher.github import Release


class JsonFormatter:
    @staticmethod
    def save(
        draft: BlogDraft,
        release: Release,
        source_commits: List[str],
        source_prs: List[int],
        output_path: Path,
    ) -> None:
        """Save blog as JSON file."""
        data = {
            "version": release.tag_name,
            "release_date": release.published_at[:10],
            "language": "zh",
            "title": draft.title,
            "summary": draft.summary,
            "tags": draft.tags,
            "content_md": draft.content,
            "generated_at": datetime.now().isoformat(),
            "source_commits": source_commits,
            "source_prs": source_prs,
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
