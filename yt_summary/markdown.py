"""Markdown formatting utilities for Obsidian integration."""

import re
from datetime import datetime, timezone
from typing import TypedDict


class ParsedMarkdown(TypedDict):
    """Typed structure returned by parse_markdown."""

    video_id: str
    title: str
    channel: str
    read: bool
    starred: bool
    full_text: str
    summary: str
    title_evaluation: str


def generate_markdown(
    video_id: str, title: str, full_text: str, summary: str, channel: str = ""
) -> str:
    """Generate Obsidian-compatible markdown from video data.

    Args:
        video_id: YouTube video ID
        title: Video title
        full_text: Complete transcript text
        summary: Claude-generated summary with sections (legacy colon-prefix or
            new markdown-heading format)
        channel: Channel name (optional)

    Returns:
        Formatted markdown string with YAML frontmatter
    """
    # Parse summary into sections
    (
        title_eval_section,
        summary_section,
        takeaways_section,
        protocols_section,
    ) = _parse_summary_sections(summary)

    # Generate YAML frontmatter
    timestamp = datetime.now(timezone.utc).isoformat()
    frontmatter_lines = [
        "---",
        f"video_id: {video_id}",
        f'title: "{title}"',
    ]
    if channel:
        frontmatter_lines.append(f'channel: "{channel}"')
    frontmatter_lines.extend(
        [
            f"url: https://www.youtube.com/watch?v={video_id}",
            f"cached_at: {timestamp}",
            "read: false",
            "starred: false",
            "---",
        ]
    )
    frontmatter = "\n".join(frontmatter_lines) + "\n"

    # Build markdown content
    content_parts = [frontmatter, f"# {title}", ""]

    # Add title evaluation section (new format only)
    if title_eval_section:
        content_parts.extend(["## Title Evaluation", "", title_eval_section, ""])

    # Add summary section
    if summary_section:
        content_parts.extend(["## Summary", "", summary_section, ""])

    # Add takeaways section
    if takeaways_section:
        content_parts.extend(["## Top Takeaways", "", takeaways_section, ""])

    # Add protocols section if present
    if protocols_section:
        content_parts.extend(["## Protocols & Instructions", "", protocols_section, ""])

    # Add full transcript
    content_parts.extend(["## Full Transcript", "", full_text, ""])

    return "\n".join(content_parts)


def parse_markdown(markdown_content: str) -> ParsedMarkdown:
    """Parse Obsidian markdown back to original data structure.

    Args:
        markdown_content: Markdown file content with frontmatter

    Returns:
        Dictionary with video_id, title, full_text, summary, and title_evaluation.
        For files written with new-format headings (``## Title Evaluation`` present),
        ``summary`` is reconstructed as full markdown-heading text so the skill can
        render all four sections directly.  For legacy files (no Title Evaluation
        section), ``summary`` is reconstructed in the legacy colon-prefix format so
        existing callers are unaffected.
    """
    # Extract frontmatter
    frontmatter_match = re.match(r"^---\n(.*?)\n---\n", markdown_content, re.DOTALL)
    if not frontmatter_match:
        raise ValueError("Invalid markdown: missing frontmatter")

    frontmatter = frontmatter_match.group(1)
    content = markdown_content[frontmatter_match.end() :]

    # Parse frontmatter fields
    video_id = _extract_frontmatter_field(frontmatter, "video_id")
    title = _extract_frontmatter_field(frontmatter, "title")
    channel = _extract_frontmatter_field(frontmatter, "channel")
    read_raw = _extract_frontmatter_field(frontmatter, "read")
    starred_raw = _extract_frontmatter_field(frontmatter, "starred")

    # Extract sections from content
    title_eval_text = _extract_section(content, "Title Evaluation")
    summary_text = _extract_section(content, "Summary")
    takeaways_text = _extract_section(content, "Top Takeaways")
    protocols_text = _extract_section(content, "Protocols & Instructions")
    transcript_text = _extract_section(content, "Full Transcript")

    # Reconstruct summary field.
    # New format (Title Evaluation present): use markdown headings so the skill
    # can render all four sections directly.
    # Legacy format (no Title Evaluation): use colon-prefix format for backwards
    # compatibility with the legacy yt-summary skill.
    if title_eval_text:
        summary_parts = []
        summary_parts.append(f"## Title Evaluation\n{title_eval_text}")
        if summary_text:
            summary_parts.append(f"## Summary\n{summary_text}")
        if takeaways_text:
            summary_parts.append(f"## Top Takeaways\n{takeaways_text}")
        if protocols_text:
            summary_parts.append(f"## Protocols & Instructions\n{protocols_text}")
        summary = "\n\n".join(summary_parts)
    else:
        summary_parts = []
        if summary_text:
            summary_parts.append(f"SUMMARY:\n{summary_text}")
        if takeaways_text:
            summary_parts.append(f"TOP TAKEAWAYS:\n{takeaways_text}")
        if protocols_text:
            summary_parts.append(f"PROTOCOLS & INSTRUCTIONS:\n{protocols_text}")
        summary = "\n\n".join(summary_parts)

    return {
        "video_id": video_id,
        "title": title,
        "channel": channel,
        "read": read_raw.lower() == "true" if read_raw else False,
        "starred": starred_raw.lower() == "true" if starred_raw else False,
        "full_text": transcript_text,
        "summary": summary,
        "title_evaluation": title_eval_text,
    }


def _parse_summary_sections(summary: str) -> tuple[str, str, str, str]:
    """Parse summary text into component sections.

    Recognises two formats:

    *Legacy* (``yt-summary`` skill)::

        SUMMARY:
        ...

        TOP TAKEAWAYS:
        ...

        PROTOCOLS & INSTRUCTIONS:
        ...

    *New* (``yt-summary-mdflow`` skill)::

        ## Title Evaluation
        ...

        ## Summary
        ...

        ## Top Takeaways
        ...

        ## Protocols & Instructions
        ...

    Args:
        summary: Complete summary text with section headers

    Returns:
        Tuple of (title_evaluation_text, summary_text, takeaways_text,
        protocols_text).  ``title_evaluation_text`` is always ``""`` for
        legacy-format input.
    """
    title_eval_text = ""
    summary_text = ""
    takeaways_text = ""
    protocols_text = ""

    # Detect new markdown-heading format by looking for ## headings
    if re.search(r"^## ", summary, re.MULTILINE):
        # New format: split on markdown headings
        parts = re.split(r"\n(?=## )", summary)
        for part in parts:
            part = part.strip()
            if part.startswith("## Title Evaluation"):
                title_eval_text = part[len("## Title Evaluation") :].strip()
            elif part.startswith("## Summary"):
                summary_text = part[len("## Summary") :].strip()
            elif part.startswith("## Top Takeaways"):
                takeaways_text = part[len("## Top Takeaways") :].strip()
            elif part.startswith("## Protocols & Instructions"):
                protocols_text = part[len("## Protocols & Instructions") :].strip()
    else:
        # Legacy format: split on colon-prefix headers
        parts = re.split(r"\n\n(?=SUMMARY:|TOP TAKEAWAYS:|PROTOCOLS & INSTRUCTIONS:)", summary)
        for part in parts:
            part = part.strip()
            if part.startswith("SUMMARY:"):
                summary_text = part[len("SUMMARY:") :].strip()
            elif part.startswith("TOP TAKEAWAYS:"):
                takeaways_text = part[len("TOP TAKEAWAYS:") :].strip()
            elif part.startswith("PROTOCOLS & INSTRUCTIONS:"):
                protocols_text = part[len("PROTOCOLS & INSTRUCTIONS:") :].strip()

    return title_eval_text, summary_text, takeaways_text, protocols_text


def _extract_frontmatter_field(frontmatter: str, field_name: str) -> str:
    """Extract a field value from YAML frontmatter.

    Args:
        frontmatter: YAML frontmatter content
        field_name: Field to extract

    Returns:
        Field value or empty string if not found
    """
    pattern = rf"^{field_name}:\s*(.+)$"
    match = re.search(pattern, frontmatter, re.MULTILINE)
    if not match:
        return ""
    value = match.group(1).strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        value = value[1:-1]
    return value


def _extract_section(content: str, section_name: str) -> str:
    """Extract content from a markdown section.

    Args:
        content: Markdown content
        section_name: Section header to find (without ##)

    Returns:
        Section content or empty string if not found
    """
    # Match section header and capture content until next header or end
    pattern = rf"^## {re.escape(section_name)}\n\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, content, re.DOTALL | re.MULTILINE)
    return match.group(1).strip() if match else ""
