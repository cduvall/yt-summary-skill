"""Tests for markdown formatting utilities."""

import re
from datetime import datetime

import pytest

from yt_summary.markdown import (
    _extract_frontmatter_field,
    _extract_section,
    _parse_summary_sections,
    generate_markdown,
    parse_markdown,
)


class TestGenerateMarkdown:
    """Test markdown generation from video data."""

    def test_generate_markdown_basic(self) -> None:
        """Generate markdown with basic summary."""
        result = generate_markdown(
            video_id="abc123",
            title="Test Video",
            full_text="This is the transcript.",
            summary="SUMMARY:\nThis is the summary.",
        )

        assert "---" in result
        assert "video_id: abc123" in result
        assert 'title: "Test Video"' in result
        assert "url: https://www.youtube.com/watch?v=abc123" in result
        assert "# Test Video" in result
        assert "## Summary" in result
        assert "This is the summary." in result
        assert "## Full Transcript" in result
        assert "This is the transcript." in result
        assert "read: false" in result
        assert "starred: false" in result

    def test_generate_markdown_with_channel(self) -> None:
        """Generate markdown with channel in frontmatter."""
        result = generate_markdown(
            video_id="abc123",
            title="Test Video",
            full_text="Transcript text.",
            summary="SUMMARY:\nSummary text.",
            channel="Tech Channel",
        )

        assert "video_id: abc123" in result
        assert 'title: "Test Video"' in result
        assert 'channel: "Tech Channel"' in result
        assert "url: https://www.youtube.com/watch?v=abc123" in result

    def test_generate_markdown_without_channel(self) -> None:
        """Generate markdown without channel field when not provided."""
        result = generate_markdown(
            video_id="abc123",
            title="Test Video",
            full_text="Transcript text.",
            summary="SUMMARY:\nSummary text.",
        )

        assert "video_id: abc123" in result
        assert 'title: "Test Video"' in result
        assert "channel:" not in result

    def test_generate_markdown_empty_channel(self) -> None:
        """Generate markdown without channel field when empty string."""
        result = generate_markdown(
            video_id="abc123",
            title="Test Video",
            full_text="Transcript text.",
            summary="SUMMARY:\nSummary text.",
            channel="",
        )

        assert "video_id: abc123" in result
        assert 'title: "Test Video"' in result
        assert "channel:" not in result

    def test_generate_markdown_with_all_sections(self) -> None:
        """Generate markdown with all sections."""
        summary = """SUMMARY:
Main summary text here.

TOP TAKEAWAYS:
- Point 1
- Point 2
- Point 3

PROTOCOLS & INSTRUCTIONS:
1. Step one
2. Step two"""

        result = generate_markdown(
            video_id="abc123",
            title="Complete Video",
            full_text="Full transcript text.",
            summary=summary,
        )

        assert "## Summary" in result
        assert "Main summary text here." in result
        assert "## Top Takeaways" in result
        assert "- Point 1" in result
        assert "## Protocols & Instructions" in result
        assert "1. Step one" in result
        assert "## Full Transcript" in result
        assert "Full transcript text." in result

    def test_generate_markdown_with_unicode(self) -> None:
        """Generate markdown with unicode characters."""
        result = generate_markdown(
            video_id="unicode123",
            title="世界 Hello 🌍",
            full_text="Transcript with émojis 🎉 and special chars ñ",
            summary="SUMMARY:\nSummary with 世界",
        )

        assert 'title: "世界 Hello 🌍"' in result
        assert "émojis 🎉" in result
        assert "世界" in result

    def test_generate_markdown_empty_summary(self) -> None:
        """Generate markdown with empty summary."""
        result = generate_markdown(
            video_id="abc123", title="Test", full_text="Transcript", summary=""
        )

        assert "## Full Transcript" in result
        assert "Transcript" in result
        # Should not have summary section if empty
        assert result.count("## Summary") == 0

    def test_generate_markdown_frontmatter_has_timestamp(self) -> None:
        """Frontmatter includes cached_at timestamp."""
        result = generate_markdown(video_id="abc123", title="Test", full_text="Text", summary="")

        assert "cached_at:" in result
        # Verify it's a valid ISO timestamp
        match = re.search(r"cached_at: (.+)", result)
        assert match
        timestamp_str = match.group(1)
        # Should be parseable as ISO format
        datetime.fromisoformat(timestamp_str)

    def test_generate_markdown_preserves_newlines(self) -> None:
        """Preserve newlines in transcript and summary."""
        result = generate_markdown(
            video_id="abc123",
            title="Test",
            full_text="Line 1\nLine 2\nLine 3",
            summary="SUMMARY:\nParagraph 1\n\nParagraph 2",
        )

        assert "Line 1\nLine 2\nLine 3" in result
        assert "Paragraph 1\n\nParagraph 2" in result


class TestParseMarkdown:
    """Test parsing markdown back to data structure."""

    def test_parse_markdown_basic(self) -> None:
        """Parse basic markdown file."""
        markdown = """---
video_id: abc123
title: Test Video
url: https://www.youtube.com/watch?v=abc123
cached_at: 2026-01-01T00:00:00+00:00
---
# Test Video

## Summary

This is the summary.

## Full Transcript

This is the transcript.
"""
        result = parse_markdown(markdown)

        assert result["video_id"] == "abc123"
        assert result["title"] == "Test Video"
        assert result["channel"] == ""
        assert result["read"] is False
        assert result["starred"] is False
        assert result["full_text"] == "This is the transcript."
        assert "SUMMARY:" in result["summary"]
        assert "This is the summary." in result["summary"]

    def test_parse_markdown_with_channel(self) -> None:
        """Parse markdown file with channel."""
        markdown = """---
video_id: abc123
title: Test Video
channel: Tech Channel
url: https://www.youtube.com/watch?v=abc123
cached_at: 2026-01-01T00:00:00+00:00
---
# Test Video

## Summary

This is the summary.

## Full Transcript

This is the transcript.
"""
        result = parse_markdown(markdown)

        assert result["video_id"] == "abc123"
        assert result["title"] == "Test Video"
        assert result["channel"] == "Tech Channel"
        assert result["full_text"] == "This is the transcript."
        assert "This is the summary." in result["summary"]

    def test_parse_markdown_with_all_sections(self) -> None:
        """Parse markdown with all sections."""
        markdown = """---
video_id: abc123
title: Complete Video
url: https://www.youtube.com/watch?v=abc123
cached_at: 2026-01-01T00:00:00+00:00
---
# Complete Video

## Summary

Main summary text.

## Top Takeaways

- Point 1
- Point 2

## Protocols & Instructions

1. Step one
2. Step two

## Full Transcript

Full transcript here.
"""
        result = parse_markdown(markdown)

        assert "SUMMARY:\nMain summary text." in result["summary"]
        assert "TOP TAKEAWAYS:\n- Point 1\n- Point 2" in result["summary"]
        assert "PROTOCOLS & INSTRUCTIONS:\n1. Step one\n2. Step two" in result["summary"]
        assert result["full_text"] == "Full transcript here."

    def test_parse_markdown_with_unicode(self) -> None:
        """Parse markdown with unicode characters."""
        markdown = """---
video_id: unicode123
title: 世界 Test
url: https://www.youtube.com/watch?v=unicode123
cached_at: 2026-01-01T00:00:00+00:00
---
# 世界 Test

## Summary

Summary with émojis 🎉

## Full Transcript

世界 transcript text
"""
        result = parse_markdown(markdown)

        assert result["title"] == "世界 Test"
        assert "émojis 🎉" in result["summary"]
        assert "世界 transcript text" in result["full_text"]

    def test_parse_markdown_missing_frontmatter_raises_error(self) -> None:
        """Raise error when frontmatter is missing."""
        markdown = """# No Frontmatter

Content here.
"""
        with pytest.raises(ValueError, match="missing frontmatter"):
            parse_markdown(markdown)

    def test_parse_markdown_empty_sections(self) -> None:
        """Parse markdown with empty sections."""
        markdown = """---
video_id: empty123
title: Empty
url: https://www.youtube.com/watch?v=empty123
cached_at: 2026-01-01T00:00:00+00:00
---
# Empty

## Full Transcript


"""
        result = parse_markdown(markdown)

        assert result["video_id"] == "empty123"
        assert result["full_text"] == ""
        assert result["summary"] == ""

    def test_parse_markdown_preserves_newlines(self) -> None:
        """Preserve newlines in parsed content."""
        markdown = """---
video_id: abc123
title: Test
url: https://www.youtube.com/watch?v=abc123
cached_at: 2026-01-01T00:00:00+00:00
---
# Test

## Summary

Paragraph 1

Paragraph 2

## Full Transcript

Line 1
Line 2
Line 3
"""
        result = parse_markdown(markdown)

        assert "Paragraph 1\n\nParagraph 2" in result["summary"]
        assert "Line 1\nLine 2\nLine 3" in result["full_text"]


class TestParseSummarySections:
    """Test parsing summary text into sections."""

    def test_parse_summary_sections_all_present(self) -> None:
        """Parse summary with all sections present."""
        summary = """SUMMARY:
Main summary text.

TOP TAKEAWAYS:
- Point 1
- Point 2

PROTOCOLS & INSTRUCTIONS:
1. Step one
2. Step two"""

        summary_text, takeaways_text, protocols_text = _parse_summary_sections(summary)

        assert summary_text == "Main summary text."
        assert takeaways_text == "- Point 1\n- Point 2"
        assert protocols_text == "1. Step one\n2. Step two"

    def test_parse_summary_sections_only_summary(self) -> None:
        """Parse summary with only main summary section."""
        summary = "SUMMARY:\nJust the summary text."

        summary_text, takeaways_text, protocols_text = _parse_summary_sections(summary)

        assert summary_text == "Just the summary text."
        assert takeaways_text == ""
        assert protocols_text == ""

    def test_parse_summary_sections_empty_string(self) -> None:
        """Parse empty summary string."""
        summary_text, takeaways_text, protocols_text = _parse_summary_sections("")

        assert summary_text == ""
        assert takeaways_text == ""
        assert protocols_text == ""

    def test_parse_summary_sections_multiline_content(self) -> None:
        """Parse sections with multiline content."""
        summary = """SUMMARY:
This is a long summary.
It spans multiple lines.
With lots of content.

TOP TAKEAWAYS:
- First takeaway
- Second takeaway
- Third takeaway"""

        summary_text, takeaways_text, protocols_text = _parse_summary_sections(summary)

        assert "This is a long summary." in summary_text
        assert "It spans multiple lines." in summary_text
        assert "- First takeaway" in takeaways_text


class TestExtractFrontmatterField:
    """Test extracting fields from YAML frontmatter."""

    def test_extract_frontmatter_field_basic(self) -> None:
        """Extract basic field from frontmatter."""
        frontmatter = """video_id: abc123
title: Test Video
url: https://example.com"""

        assert _extract_frontmatter_field(frontmatter, "video_id") == "abc123"
        assert _extract_frontmatter_field(frontmatter, "title") == "Test Video"
        assert _extract_frontmatter_field(frontmatter, "url") == "https://example.com"

    def test_extract_frontmatter_field_missing(self) -> None:
        """Return empty string when field is missing."""
        frontmatter = "video_id: abc123"

        assert _extract_frontmatter_field(frontmatter, "title") == ""

    def test_extract_frontmatter_field_with_unicode(self) -> None:
        """Extract field with unicode characters."""
        frontmatter = "title: 世界 Test 🌍"

        assert _extract_frontmatter_field(frontmatter, "title") == "世界 Test 🌍"

    def test_extract_frontmatter_field_with_spaces(self) -> None:
        """Extract field value with leading/trailing spaces."""
        frontmatter = "title:   Lots of Spaces   "

        result = _extract_frontmatter_field(frontmatter, "title")
        assert result == "Lots of Spaces"


class TestExtractSection:
    """Test extracting markdown sections."""

    def test_extract_section_basic(self) -> None:
        """Extract basic section content."""
        content = """# Title

## Summary

This is the summary.

## Other Section

Other content.
"""
        result = _extract_section(content, "Summary")

        assert result == "This is the summary."

    def test_extract_section_multiline(self) -> None:
        """Extract section with multiline content."""
        content = """## Summary

Line 1
Line 2
Line 3

## Next Section

Next content.
"""
        result = _extract_section(content, "Summary")

        assert result == "Line 1\nLine 2\nLine 3"

    def test_extract_section_missing(self) -> None:
        """Return empty string when section is missing."""
        content = "## Other Section\n\nContent."

        result = _extract_section(content, "Summary")

        assert result == ""

    def test_extract_section_at_end(self) -> None:
        """Extract section at end of document."""
        content = """## First Section

First content.

## Last Section

Last content here.
"""
        result = _extract_section(content, "Last Section")

        assert result == "Last content here."

    def test_extract_section_with_special_characters(self) -> None:
        """Extract section with special characters in name."""
        content = """## Protocols & Instructions

Step 1
Step 2

## Other

Other content.
"""
        result = _extract_section(content, "Protocols & Instructions")

        assert result == "Step 1\nStep 2"

    def test_extract_section_preserves_blank_lines(self) -> None:
        """Preserve blank lines within section content."""
        content = """## Summary

Paragraph 1

Paragraph 2

## Next

Next content.
"""
        result = _extract_section(content, "Summary")

        assert result == "Paragraph 1\n\nParagraph 2"


class TestRoundTrip:
    """Test round-trip conversion (generate -> parse)."""

    def test_roundtrip_basic(self) -> None:
        """Round-trip basic data."""
        original_data = {
            "video_id": "abc123",
            "title": "Test Video",
            "full_text": "This is the transcript.",
            "summary": "SUMMARY:\nThis is the summary.",
        }

        # Generate markdown
        markdown = generate_markdown(
            original_data["video_id"],
            original_data["title"],
            original_data["full_text"],
            original_data["summary"],
        )

        # Parse it back
        parsed_data = parse_markdown(markdown)

        assert parsed_data["video_id"] == original_data["video_id"]
        assert parsed_data["title"] == original_data["title"]
        assert parsed_data["channel"] == ""
        assert parsed_data["read"] is False
        assert parsed_data["starred"] is False
        assert parsed_data["full_text"] == original_data["full_text"]
        assert "This is the summary." in parsed_data["summary"]

    def test_roundtrip_with_channel(self) -> None:
        """Round-trip data with channel."""
        markdown = generate_markdown(
            "abc123",
            "Test Video",
            "Transcript text.",
            "SUMMARY:\nSummary text.",
            channel="Tech Channel",
        )

        parsed = parse_markdown(markdown)

        assert parsed["video_id"] == "abc123"
        assert parsed["title"] == "Test Video"
        assert parsed["channel"] == "Tech Channel"
        assert parsed["full_text"] == "Transcript text."
        assert "Summary text." in parsed["summary"]

    def test_roundtrip_with_all_sections(self) -> None:
        """Round-trip with all summary sections."""
        summary = """SUMMARY:
Main summary.

TOP TAKEAWAYS:
- Point 1
- Point 2

PROTOCOLS & INSTRUCTIONS:
1. Step one
2. Step two"""

        markdown = generate_markdown("abc123", "Complete Video", "Transcript text.", summary)

        parsed = parse_markdown(markdown)

        assert "Main summary." in parsed["summary"]
        assert "Point 1" in parsed["summary"]
        assert "Step one" in parsed["summary"]
        assert parsed["full_text"] == "Transcript text."

    def test_roundtrip_with_unicode(self) -> None:
        """Round-trip with unicode content."""
        markdown = generate_markdown(
            "unicode123", "世界 Test 🌍", "Transcript with émojis 🎉", "SUMMARY:\nSummary 世界"
        )

        parsed = parse_markdown(markdown)

        assert parsed["title"] == "世界 Test 🌍"
        assert "émojis 🎉" in parsed["full_text"]
        assert "世界" in parsed["summary"]


class TestGenerateMarkdownPlaylist:
    """Test markdown generation with playlist metadata fields."""

    def test_generate_markdown_with_playlist_metadata(self) -> None:
        result = generate_markdown(
            video_id="abc123",
            title="Test Video",
            full_text="Transcript text.",
            summary="SUMMARY:\nSummary text.",
            playlist_id="PLddiDRMhpXFL",
            playlist_title="My Playlist",
        )

        assert 'playlist_id: "PLddiDRMhpXFL"' in result
        assert 'playlist_title: "My Playlist"' in result

    def test_generate_markdown_without_playlist_metadata(self) -> None:
        result = generate_markdown(
            video_id="abc123",
            title="Test Video",
            full_text="Transcript text.",
            summary="SUMMARY:\nSummary text.",
        )

        assert "playlist_id:" not in result
        assert "playlist_title:" not in result


class TestParseMarkdownPlaylist:
    """Test parsing markdown with playlist metadata fields."""

    def test_parse_markdown_with_playlist_metadata(self) -> None:
        markdown = """---
video_id: abc123
title: Test Video
playlist_id: "PLddiDRMhpXFL"
playlist_title: "My Playlist"
url: https://www.youtube.com/watch?v=abc123
cached_at: 2026-01-01T00:00:00+00:00
---
# Test Video

## Full Transcript

Transcript text.
"""
        result = parse_markdown(markdown)

        assert result["playlist_id"] == "PLddiDRMhpXFL"
        assert result["playlist_title"] == "My Playlist"

    def test_parse_markdown_without_playlist_metadata(self) -> None:
        markdown = """---
video_id: abc123
title: Test Video
url: https://www.youtube.com/watch?v=abc123
cached_at: 2026-01-01T00:00:00+00:00
---
# Test Video

## Full Transcript

Transcript text.
"""
        result = parse_markdown(markdown)

        assert result["playlist_id"] == ""
        assert result["playlist_title"] == ""


class TestRoundTripPlaylist:
    """Test round-trip conversion with playlist metadata."""

    def test_roundtrip_with_playlist_metadata(self) -> None:
        markdown = generate_markdown(
            video_id="abc123",
            title="Test Video",
            full_text="Transcript text.",
            summary="SUMMARY:\nSummary text.",
            channel="Tech Channel",
            playlist_id="PLddiDRMhpXFL",
            playlist_title="My Playlist",
        )

        parsed = parse_markdown(markdown)

        assert parsed["video_id"] == "abc123"
        assert parsed["channel"] == "Tech Channel"
        assert parsed["playlist_id"] == "PLddiDRMhpXFL"
        assert parsed["playlist_title"] == "My Playlist"
        assert parsed["full_text"] == "Transcript text."
