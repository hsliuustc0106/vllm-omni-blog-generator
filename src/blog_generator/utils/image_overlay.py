"""Image overlay utilities for adding text to generated images."""

import os
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont


def get_chinese_font(size: int) -> ImageFont.FreeTypeFont:
    """Get a Chinese-compatible font.

    Tries multiple fonts in order of preference.
    Falls back to default if none found.

    Args:
        size: Font size in pixels

    Returns:
        PIL Font object
    """
    # Common Chinese fonts on macOS
    font_paths = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
    ]

    # Try to find a working font
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue

    # Fallback to default font
    return ImageFont.load_default()


def add_text_overlay(
    image_path: Path,
    title: str,
    output_path: Optional[Path] = None,
    font_size: int = 48,
    text_color: Tuple[int, int, int] = (255, 255, 255),
    shadow_color: Tuple[int, int, int] = (0, 0, 0),
    padding: int = 40,
    line_spacing: int = 1.3,
) -> Path:
    """Add text overlay to an image.

    Args:
        image_path: Path to the input image
        title: Title text to overlay (can be multi-line)
        output_path: Path to save the output image (default: overwrite input)
        font_size: Font size in pixels
        text_color: RGB tuple for text color
        shadow_color: RGB tuple for text shadow
        padding: Padding from edges in pixels
        line_spacing: Multiplier for line spacing

    Returns:
        Path to the output image
    """
    # Load image
    img = Image.open(image_path)
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    # Create overlay
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Get font
    font = get_chinese_font(font_size)

    # Calculate text position (centered horizontally, top-aligned with padding)
    lines = _wrap_text(title, font, img.width - padding * 2)
    y_position = padding

    for line in lines:
        # Get text bounding box
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]

        # Center horizontally
        x_position = (img.width - text_width) // 2

        # Draw shadow for better readability
        shadow_offset = 2
        draw.text(
            (x_position + shadow_offset, y_position + shadow_offset),
            line,
            font=font,
            fill=(*shadow_color, 200),
        )

        # Draw main text
        draw.text((x_position, y_position), line, font=font, fill=(*text_color, 255))

        # Move to next line
        line_height = int(font_size * line_spacing)
        y_position += line_height

    # Composite overlay onto image
    result = Image.alpha_composite(img, overlay)

    # Convert back to RGB for saving as PNG
    result = result.convert("RGB")

    # Save
    save_path = output_path or image_path
    save_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(save_path, "PNG")

    return save_path


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Wrap text to fit within max_width.

    Args:
        text: Text to wrap
        font: PIL Font object
        max_width: Maximum width in pixels

    Returns:
        List of lines
    """
    lines = []
    current_line = ""

    # Try to break at natural points (spaces, punctuation)
    for char in text:
        test_line = current_line + char
        bbox = font.getbbox(test_line)
        text_width = bbox[2] - bbox[0]

        if text_width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = char

    if current_line:
        lines.append(current_line)

    return lines


def add_cover_text_overlay(
    image_path: Path,
    title: str,
    output_path: Optional[Path] = None,
) -> Path:
    """Add title text overlay to a cover image.

    Optimized for Xiaohongshu cover images with Chinese text.

    Args:
        image_path: Path to the input image
        title: Title text to overlay
        output_path: Path to save the output image

    Returns:
        Path to the output image
    """
    img = Image.open(image_path)

    # Adjust font size based on image dimensions
    # For 3:4 aspect ratio Xiaohongshu images
    base_font_size = min(img.width, img.height) // 12

    return add_text_overlay(
        image_path=image_path,
        title=title,
        output_path=output_path,
        font_size=base_font_size,
        text_color=(255, 255, 255),
        shadow_color=(0, 0, 0),
        padding=40,
        line_spacing=1.4,
    )


def add_ending_text_overlay(
    image_path: Path,
    main_text: str = "关注获取更多 AI 技术分享",
    project_link: str = "",
    references: str = "",
    output_path: Optional[Path] = None,
) -> Path:
    """Add text overlay to an ending/CTA image.

    Args:
        image_path: Path to the input image
        main_text: Main CTA text
        project_link: GitHub project link
        references: PR/issue references
        output_path: Path to save the output image

    Returns:
        Path to the output image
    """
    img = Image.open(image_path)

    if img.mode != "RGBA":
        img = img.convert("RGBA")

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Main text - large, centered
    main_font_size = min(img.width, img.height) // 10
    main_font = get_chinese_font(main_font_size)

    # Calculate main text position (centered)
    bbox = draw.textbbox((0, 0), main_text, font=main_font)
    text_width = bbox[2] - bbox[0]
    x_position = (img.width - text_width) // 2
    y_position = img.height // 3

    # Draw shadow and main text
    shadow_offset = 3
    draw.text(
        (x_position + shadow_offset, y_position + shadow_offset),
        main_text,
        font=main_font,
        fill=(0, 0, 0, 200),
    )
    draw.text((x_position, y_position), main_text, font=main_font, fill=(255, 255, 255, 255))

    # Project link - smaller, at bottom
    if project_link:
        link_font_size = main_font_size // 2
        link_font = get_chinese_font(link_font_size)

        link_text = f"🔗 {project_link}"
        bbox = draw.textbbox((0, 0), link_text, font=link_font)
        text_width = bbox[2] - bbox[0]
        x_position = (img.width - text_width) // 2
        y_position = img.height - link_font_size * 4

        draw.text(
            (x_position + 1, y_position + 1),
            link_text,
            font=link_font,
            fill=(0, 0, 0, 150),
        )
        draw.text((x_position, y_position), link_text, font=link_font, fill=(255, 215, 0, 255))

    # References - smallest, above link
    if references:
        ref_font_size = main_font_size // 3
        ref_font = get_chinese_font(ref_font_size)

        bbox = draw.textbbox((0, 0), references, font=ref_font)
        text_width = bbox[2] - bbox[0]
        x_position = (img.width - text_width) // 2
        y_position = img.height - ref_font_size * 7

        draw.text(
            (x_position + 1, y_position + 1),
            references,
            font=ref_font,
            fill=(0, 0, 0, 150),
        )
        draw.text((x_position, y_position), references, font=ref_font, fill=(200, 200, 200, 255))

    # Composite and save
    result = Image.alpha_composite(img, overlay)
    result = result.convert("RGB")

    save_path = output_path or image_path
    save_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(save_path, "PNG")

    return save_path
