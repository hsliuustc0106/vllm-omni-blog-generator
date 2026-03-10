# Xiaohongshu Publishing Workflow Design

**Date**: 2026-03-10
**Status**: Approved
**Approach**: Semi-automated with manual copy-paste (Option 1)

## Overview

Use existing blog-generator + baoyu-xhs-images skills with manual copy-paste to Xiaohongshu. No new code required.

## Requirements

- Generate Xiaohongshu-formatted content from blog posts
- Generate carousel images automatically
- Simple, reliable workflow without browser automation risks

## Workflow

```
blog-generator generate --pr 962
         ↓
blog-generator publish --release pr962
         ↓
/baoyu-xhs-images blogs/pr962/xiaohongshu/images/prompts.md --style tech
         ↓
Manual: Open creator.xiaohongshu.com
         ↓
Manual: Copy content from blogs/pr962/xiaohongshu/content.md
         ↓
Manual: Upload generated images
         ↓
Manual: Click 发布
```

## Components

| Component | Purpose | Status |
|-----------|---------|--------|
| `blog-generator publish` | Format content for XHS | Exists |
| `blogs/pr962/xiaohongshu/content.md` | Short-form content (800 chars) | Generated |
| `blogs/pr962/xiaohongshu/images/prompts.md` | Image prompts | Generated |
| `baoyu-xhs-images` | Generate carousel images | Skill exists |

## Output Files

```
blogs/pr962/xiaohongshu/
├── content.md           # Copy-paste to XHS
└── images/
    ├── prompts.md       # Image prompts
    └── *.png            # Generated images (from baoyu-xhs-images)
```

## Future Enhancements

- Option 2: Add `xhs-publish` command with Chrome CDP automation
- Option 3: Create standalone xhs-post skill for broader use
