"""Zhihu platform formatter."""

from pathlib import Path
from datetime import datetime


class ZhihuFormatter:
    @staticmethod
    def format(content_md: str, title: str) -> str:
        """Format content for Zhihu."""
        # Add Zhihu-specific formatting
        formatted = f"""# {title}

{content_md}

---

**相关链接**
- [vLLM-Omni GitHub](https://github.com/vllm-project/vllm-omni)
- [vLLM-Omni 文档](https://vllm-omni.readthedocs.io)

*发布于 {datetime.now().strftime('%Y年%m月%d日')}*
"""
        return formatted

    @staticmethod
    def save(content: str, output_path: Path) -> None:
        """Save Zhihu-formatted content."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)
