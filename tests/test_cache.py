"""Tests for caching functionality."""

import json
from pathlib import Path
from unittest.mock import patch

from yt_summary.cache import _find_cache_file, is_legacy_filename, load_cache, save_to_cache


class TestLoadCache:
    """Test loading cached data."""

    def test_load_cache_existing_markdown_file(self, tmp_path: Path) -> None:
        """Load cache from existing markdown file (new format)."""
        channel_dir = tmp_path / "Summaries" / "Tech Channel"
        channel_dir.mkdir(parents=True)
        cache_file = channel_dir / "Sample Video [test_video].md"
        markdown_content = """---
video_id: test_video
title: Sample Video
channel: Tech Channel
url: https://www.youtube.com/watch?v=test_video
cached_at: 2026-01-01T00:00:00+00:00
---
# Sample Video

## Summary

Sample summary

## Top Takeaways

- Point 1
- Point 2

## Full Transcript

Sample transcript
"""
        cache_file.write_text(markdown_content)

        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            result = load_cache("test_video")

        assert result["video_id"] == "test_video"
        assert result["title"] == "Sample Video"
        assert result["channel"] == "Tech Channel"
        assert result["full_text"] == "Sample transcript"
        assert "Sample summary" in result["summary"]
        assert result["read"] is False

    def test_load_cache_old_format_flat_structure(self, tmp_path: Path) -> None:
        """Load cache from old format in flat structure."""
        cache_file = tmp_path / "test_video – Sample Video.md"
        markdown_content = """---
video_id: test_video
title: Sample Video
url: https://www.youtube.com/watch?v=test_video
cached_at: 2026-01-01T00:00:00+00:00
---
# Sample Video

## Summary

Sample summary

## Full Transcript

Sample transcript
"""
        cache_file.write_text(markdown_content)

        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            result = load_cache("test_video")

        assert result["video_id"] == "test_video"
        assert result["title"] == "Sample Video"
        assert result["channel"] == ""
        assert result["full_text"] == "Sample transcript"
        assert "Sample summary" in result["summary"]
        assert result["read"] is False

    def test_load_cache_legacy_json_auto_migrates(self, tmp_path: Path) -> None:
        """Load legacy JSON cache and auto-migrate to markdown."""
        cache_file = tmp_path / "test_video.json"
        test_data = {
            "video_id": "test_video",
            "title": "Test Video",
            "full_text": "Sample transcript",
            "summary": "SUMMARY:\nSample summary",
        }
        cache_file.write_text(json.dumps(test_data))

        with (
            patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path),
            patch("yt_summary.cache.save_to_cache") as mock_save,
        ):
            result = load_cache("test_video")

            # Should call save_to_cache to migrate
            mock_save.assert_called_once()

        # Should return the data
        assert result["video_id"] == "test_video"
        assert result["full_text"] == "Sample transcript"

    def test_load_cache_nonexistent_file(self, tmp_path: Path) -> None:
        """Return None when cache file doesn't exist."""
        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            result = load_cache("nonexistent_video")

        assert result is None

    def test_load_cache_with_unicode(self, tmp_path: Path) -> None:
        """Load cache containing unicode characters."""
        cache_file = tmp_path / "unicode_video – 世界 Test.md"
        markdown_content = """---
video_id: unicode_video
title: 世界 Test
url: https://www.youtube.com/watch?v=unicode_video
cached_at: 2026-01-01T00:00:00+00:00
---
# 世界 Test

## Summary

Summary with émojis and ñ

## Full Transcript

Hello 世界 🌍 Привет
"""
        cache_file.write_text(markdown_content, encoding="utf-8")

        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            result = load_cache("unicode_video")

        assert "世界 🌍 Привет" in result["full_text"]
        assert "émojis and ñ" in result["summary"]

    def test_load_cache_empty_sections(self, tmp_path: Path) -> None:
        """Load cache with minimal content."""
        cache_file = tmp_path / "empty_data.md"
        markdown_content = """---
video_id: empty_data
title: Empty
url: https://www.youtube.com/watch?v=empty_data
cached_at: 2026-01-01T00:00:00+00:00
---
# Empty

## Full Transcript


"""
        cache_file.write_text(markdown_content)

        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            result = load_cache("empty_data")

        assert result["video_id"] == "empty_data"
        assert result["full_text"] == ""
        assert result["summary"] == ""

    def test_load_cache_special_video_id(self, tmp_path: Path) -> None:
        """Load cache with special characters in video ID."""
        video_id = "abc-123_XYZ"
        cache_file = tmp_path / f"{video_id} – Test.md"
        markdown_content = f"""---
video_id: {video_id}
title: Test
url: https://www.youtube.com/watch?v={video_id}
cached_at: 2026-01-01T00:00:00+00:00
---
# Test

## Full Transcript

Test content
"""
        cache_file.write_text(markdown_content)

        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            result = load_cache(video_id)

        assert result["video_id"] == video_id


class TestSaveToCache:
    """Test saving data to cache."""

    def test_save_to_cache_new_file_with_title(self, tmp_path: Path) -> None:
        """Save data to new cache file with title (new format)."""
        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            save_to_cache(
                "test_video", "Sample transcript", "SUMMARY:\nSample summary", "Test Video"
            )

        cache_file = tmp_path / "Summaries" / "Test Video [test_video].md"
        assert cache_file.exists()

        content = cache_file.read_text()
        assert "video_id: test_video" in content
        assert 'title: "Test Video"' in content
        assert "Sample transcript" in content
        assert "Sample summary" in content

    def test_save_to_cache_with_channel(self, tmp_path: Path) -> None:
        """Save data to channel subdirectory."""
        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            save_to_cache(
                "test_video",
                "Sample transcript",
                "SUMMARY:\nSample summary",
                "Test Video",
                "Tech Channel",
            )

        channel_dir = tmp_path / "Summaries" / "Tech Channel"
        assert channel_dir.exists()
        assert channel_dir.is_dir()

        cache_file = channel_dir / "Test Video [test_video].md"
        assert cache_file.exists()

        content = cache_file.read_text()
        assert "video_id: test_video" in content
        assert 'title: "Test Video"' in content
        assert 'channel: "Tech Channel"' in content
        assert "Sample transcript" in content
        assert "Sample summary" in content

    def test_save_to_cache_new_file_without_title(self, tmp_path: Path) -> None:
        """Save data without title uses minimal format."""
        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            save_to_cache("test_video", "Sample transcript", "SUMMARY:\nSample summary")

        cache_file = tmp_path / "Summaries" / "[test_video].md"
        assert cache_file.exists()

        content = cache_file.read_text()
        assert "video_id: test_video" in content
        assert "Sample transcript" in content

    def test_save_to_cache_creates_directory(self, tmp_path: Path) -> None:
        """Create cache directory if it doesn't exist."""
        nonexistent_dir = tmp_path / "new_cache"
        assert not nonexistent_dir.exists()

        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=nonexistent_dir):
            save_to_cache("test_video", "Sample transcript", "SUMMARY:\nTest")

        assert nonexistent_dir.exists()
        assert (nonexistent_dir / "Summaries" / "[test_video].md").exists()

    def test_save_to_cache_creates_channel_directory(self, tmp_path: Path) -> None:
        """Create channel subdirectory if it doesn't exist."""
        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            save_to_cache(
                "test_video", "Sample transcript", "SUMMARY:\nTest", "Test Video", "New Channel"
            )

        channel_dir = tmp_path / "Summaries" / "New Channel"
        assert channel_dir.exists()
        assert channel_dir.is_dir()
        assert (channel_dir / "Test Video [test_video].md").exists()

    def test_save_to_cache_without_summary(self, tmp_path: Path) -> None:
        """Save transcript without summary."""
        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            save_to_cache("test_video", "Sample transcript", "", "Test")

        cache_file = tmp_path / "Summaries" / "Test [test_video].md"
        assert cache_file.exists()

        content = cache_file.read_text()
        assert "Sample transcript" in content

    def test_save_to_cache_merge_with_existing(self, tmp_path: Path) -> None:
        """Merge new data with existing cache."""
        # Create existing cache with transcript only (old format)
        existing_md = """---
video_id: test_video
title: Test
url: https://www.youtube.com/watch?v=test_video
cached_at: 2026-01-01T00:00:00+00:00
---
# Test

## Full Transcript

Original transcript
"""
        old_cache_file = tmp_path / "test_video – Test.md"
        old_cache_file.write_text(existing_md)

        # Save with summary - should migrate to new format
        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            save_to_cache("test_video", "Original transcript", "SUMMARY:\nNew summary", "Test")

        # Old file should be gone
        assert not old_cache_file.exists()

        # New format file should exist under Summaries/
        new_cache_file = tmp_path / "Summaries" / "Test [test_video].md"
        assert new_cache_file.exists()

        # Verify merge
        content = new_cache_file.read_text()
        assert "Original transcript" in content
        assert "New summary" in content

    def test_save_to_cache_merge_preserves_existing_summary(self, tmp_path: Path) -> None:
        """Don't overwrite existing summary with empty string."""
        # Create existing cache with summary (old format)
        existing_md = """---
video_id: test_video
title: Test
url: https://www.youtube.com/watch?v=test_video
cached_at: 2026-01-01T00:00:00+00:00
---
# Test

## Summary

Existing summary

## Full Transcript

Transcript
"""
        old_cache_file = tmp_path / "test_video – Test.md"
        old_cache_file.write_text(existing_md)

        # Save transcript without summary (empty string) - should migrate to new format
        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            save_to_cache("test_video", "Transcript", "", "Test")

        # Old file should be gone
        assert not old_cache_file.exists()

        # New format file should exist under Summaries/
        new_cache_file = tmp_path / "Summaries" / "Test [test_video].md"
        assert new_cache_file.exists()

        # Verify existing summary is preserved
        content = new_cache_file.read_text()
        assert "Existing summary" in content

    def test_save_to_cache_merge_updates_full_text(self, tmp_path: Path) -> None:
        """Update full_text when saving to existing cache."""
        existing_md = """---
video_id: test_video
title: Test
url: https://www.youtube.com/watch?v=test_video
cached_at: 2026-01-01T00:00:00+00:00
---
# Test

## Summary

Summary

## Full Transcript

Old transcript
"""
        old_cache_file = tmp_path / "test_video – Test.md"
        old_cache_file.write_text(existing_md)

        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            save_to_cache("test_video", "New transcript", "SUMMARY:\nSummary", "Test")

        # Old file should be gone
        assert not old_cache_file.exists()

        # New format file should exist under Summaries/
        new_cache_file = tmp_path / "Summaries" / "Test [test_video].md"
        content = new_cache_file.read_text()
        assert "New transcript" in content
        assert "Old transcript" not in content

    def test_save_to_cache_with_unicode(self, tmp_path: Path) -> None:
        """Save cache with unicode characters."""
        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            save_to_cache(
                "unicode_video",
                "Hello 世界 🌍 Привет мир",
                "SUMMARY:\nSummary with émojis 🎉",
                "世界 Test",
                "日本語チャンネル",
            )

        channel_dir = tmp_path / "Summaries" / "日本語チャンネル"
        assert channel_dir.exists()

        cache_file = channel_dir / "世界 Test [unicode_video].md"
        content = cache_file.read_text(encoding="utf-8")
        assert "世界" in content
        assert "Привет" in content
        assert "émojis" in content
        assert "🎉" in content
        assert 'channel: "日本語チャンネル"' in content

    def test_save_to_cache_with_special_video_id(self, tmp_path: Path) -> None:
        """Save cache with special characters in video ID."""
        video_id = "abc-123_XYZ"
        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            save_to_cache(video_id, "Sample transcript", "SUMMARY:\nSample summary", "Test")

        cache_file = tmp_path / "Summaries" / f"Test [{video_id}].md"
        assert cache_file.exists()
        content = cache_file.read_text()
        assert f"video_id: {video_id}" in content

    def test_save_to_cache_empty_strings(self, tmp_path: Path) -> None:
        """Save cache with empty strings preserves video_id."""
        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            save_to_cache("test_video", "", "")

        cache_file = tmp_path / "Summaries" / "[test_video].md"
        content = cache_file.read_text()
        assert "video_id: test_video" in content

    def test_save_to_cache_long_transcript(self, tmp_path: Path) -> None:
        """Save cache with very long transcript."""
        long_transcript = "A" * 100000  # 100k characters
        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            save_to_cache("test_video", long_transcript, "SUMMARY:\nSummary", "Test")

        cache_file = tmp_path / "Summaries" / "Test [test_video].md"
        content = cache_file.read_text()
        assert long_transcript in content

    def test_save_to_cache_special_characters(self, tmp_path: Path) -> None:
        """Save cache with special characters and newlines."""
        transcript_with_special = "Line 1\nLine 2\tTabbed\r\nWindows newline"
        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            save_to_cache("test_video", transcript_with_special, "SUMMARY:\nSummary", "Test")

        cache_file = tmp_path / "Summaries" / "Test [test_video].md"
        content = cache_file.read_text()
        assert "Line 1" in content
        assert "Line 2" in content

    def test_save_to_cache_merge_complex_scenario(self, tmp_path: Path) -> None:
        """Complex merge: save transcript first, then summary separately."""
        video_id = "complex_test"

        # Step 1: Save transcript only
        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            save_to_cache(video_id, "Full transcript text", "", "Test")

        cache_file = tmp_path / "Summaries" / f"Test [{video_id}].md"
        content = cache_file.read_text()
        assert "Full transcript text" in content

        # Step 2: Save summary (simulating cached transcript load)
        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            save_to_cache(video_id, "Full transcript text", "SUMMARY:\nGenerated summary", "Test")

        content = cache_file.read_text()
        assert "Full transcript text" in content
        assert "Generated summary" in content

    def test_save_to_cache_overwrites_video_id(self, tmp_path: Path) -> None:
        """Ensure video_id in cache matches the parameter."""
        existing_md = """---
video_id: wrong_id
title: Test
url: https://www.youtube.com/watch?v=wrong_id
cached_at: 2026-01-01T00:00:00+00:00
---
# Test

## Full Transcript

Transcript
"""
        old_cache_file = tmp_path / "test_video – Test.md"
        old_cache_file.write_text(existing_md)

        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            save_to_cache("test_video", "New transcript", "SUMMARY:\nNew summary", "Test")

        # Old file should be gone
        assert not old_cache_file.exists()

        # New format file should exist under Summaries/
        new_cache_file = tmp_path / "Summaries" / "Test [test_video].md"
        content = new_cache_file.read_text()
        assert "video_id: test_video" in content

    def test_save_to_cache_creates_daily_review(self, tmp_path: Path) -> None:
        """Verify Daily Review.md is created at vault root after save."""
        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            save_to_cache("test_video", "Transcript", "SUMMARY:\nSummary", "Test")

        review_file = tmp_path / "Daily Review.md"
        assert review_file.exists()

        content = review_file.read_text()
        assert "dataview" in content
        assert 'FROM "Summaries"' in content
        assert "read != true" in content

    def test_save_to_cache_creates_starred_review(self, tmp_path: Path) -> None:
        """Create Starred.md at vault root when saving to cache."""
        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            save_to_cache("vid123", "Test Video", "Transcript", "SUMMARY:\nSummary text.")

        starred_file = tmp_path / "Starred.md"
        assert starred_file.exists()
        content = starred_file.read_text()
        assert "dataview" in content
        assert 'FROM "Summaries"' in content
        assert "starred = true" in content


class TestFindCacheFile:
    """Test cache file discovery with new and legacy formats."""

    def test_find_cache_file_new_format(self, tmp_path: Path) -> None:
        """Find cache file with new format (title [video_id].md)."""
        channel_dir = tmp_path / "Tech Channel"
        channel_dir.mkdir()
        cache_file = channel_dir / "Amazing Tutorial [abc123].md"
        cache_file.write_text("---\nvideo_id: abc123\n---")

        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            result = _find_cache_file("abc123")

        assert result == cache_file

    def test_find_cache_file_old_markdown_format(self, tmp_path: Path) -> None:
        """Find cache file with old markdown format (video_id – title.md)."""
        cache_file = tmp_path / "abc123 – Amazing Tutorial.md"
        cache_file.write_text("---\nvideo_id: abc123\n---")

        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            result = _find_cache_file("abc123")

        assert result == cache_file

    def test_find_cache_file_legacy_json_format(self, tmp_path: Path) -> None:
        """Find cache file with legacy JSON format (video_id.json)."""
        cache_file = tmp_path / "abc123.json"
        cache_file.write_text(json.dumps({"video_id": "abc123"}))

        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            result = _find_cache_file("abc123")

        assert result == cache_file

    def test_find_cache_file_prefers_new_format_over_json(self, tmp_path: Path) -> None:
        """Prefer new markdown format over JSON when both exist."""
        channel_dir = tmp_path / "Tech Channel"
        channel_dir.mkdir()
        md_file = channel_dir / "Title [abc123].md"
        json_file = tmp_path / "abc123.json"
        md_file.write_text("---\nvideo_id: abc123\n---")
        json_file.write_text(json.dumps({"video_id": "abc123"}))

        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            result = _find_cache_file("abc123")

        # Should find new format markdown first
        assert result == md_file

    def test_find_cache_file_recursive_search(self, tmp_path: Path) -> None:
        """Find cache file in nested subdirectories."""
        channel_dir = tmp_path / "Tech Channel"
        channel_dir.mkdir()
        cache_file = channel_dir / "Tutorial [abc123].md"
        cache_file.write_text("---\nvideo_id: abc123\n---")

        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            result = _find_cache_file("abc123")

        assert result == cache_file

    def test_find_cache_file_nonexistent(self, tmp_path: Path) -> None:
        """Return None when no cache file exists."""
        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            result = _find_cache_file("nonexistent")

        assert result is None

    def test_find_cache_file_cache_dir_not_exists(self, tmp_path: Path) -> None:
        """Return None when cache directory doesn't exist."""
        nonexistent_dir = tmp_path / "nonexistent"

        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=nonexistent_dir):
            result = _find_cache_file("abc123")

        assert result is None

    def test_find_cache_file_with_special_video_id(self, tmp_path: Path) -> None:
        """Find cache file with special characters in video ID."""
        video_id = "abc-123_XYZ"
        cache_file = tmp_path / f"Title [{video_id}].md"
        cache_file.write_text(f"---\nvideo_id: {video_id}\n---")

        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            result = _find_cache_file(video_id)

        assert result == cache_file

    def test_find_cache_file_with_long_title(self, tmp_path: Path) -> None:
        """Find cache file with very long title."""
        long_title = "A" * 200
        cache_file = tmp_path / f"{long_title} [abc123].md"
        cache_file.write_text("---\nvideo_id: abc123\n---")

        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            result = _find_cache_file("abc123")

        assert result == cache_file


class TestSaveToCacheWithTitle:
    """Test saving cache files with title in filename."""

    def test_save_to_cache_with_title_creates_new_format(self, tmp_path: Path) -> None:
        """Create cache file with title in filename (new format)."""
        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            save_to_cache("abc123", "Transcript", "SUMMARY:\nSummary", title="Amazing Tutorial")

        cache_file = tmp_path / "Summaries" / "Amazing Tutorial [abc123].md"
        assert cache_file.exists()

        content = cache_file.read_text()
        assert "video_id: abc123" in content
        assert 'title: "Amazing Tutorial"' in content
        assert "Transcript" in content
        assert "Summary" in content

    def test_save_to_cache_without_title_uses_minimal_format(self, tmp_path: Path) -> None:
        """Create cache file without title in filename (minimal format)."""
        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            save_to_cache("abc123", "Transcript", "SUMMARY:\nSummary")

        cache_file = tmp_path / "Summaries" / "[abc123].md"
        assert cache_file.exists()

        content = cache_file.read_text()
        assert "video_id: abc123" in content

    def test_save_to_cache_renames_legacy_json_to_markdown(self, tmp_path: Path) -> None:
        """Rename legacy JSON file to new markdown format when title provided."""
        # Create legacy format file
        legacy_file = tmp_path / "abc123.json"
        legacy_data = {"video_id": "abc123", "full_text": "Transcript", "summary": ""}
        legacy_file.write_text(json.dumps(legacy_data))

        # Save with title
        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            save_to_cache("abc123", "Transcript", "SUMMARY:\nNew summary", title="Amazing Tutorial")

        # Legacy file should be deleted
        assert not legacy_file.exists()

        # New format file should exist under Summaries/
        new_file = tmp_path / "Summaries" / "Amazing Tutorial [abc123].md"
        assert new_file.exists()

        content = new_file.read_text()
        assert "video_id: abc123" in content
        assert "Transcript" in content
        assert "New summary" in content

    def test_save_to_cache_does_not_rename_if_same_filename(self, tmp_path: Path) -> None:
        """Don't rename when existing file already has correct new format."""
        # Create file with new format in Summaries/
        summaries_dir = tmp_path / "Summaries"
        summaries_dir.mkdir(parents=True)
        existing_md = """---
video_id: abc123
title: Amazing Tutorial
url: https://www.youtube.com/watch?v=abc123
cached_at: 2026-01-01T00:00:00+00:00
---
# Amazing Tutorial

## Summary

Old summary

## Full Transcript

Old transcript
"""
        existing_file = summaries_dir / "Amazing Tutorial [abc123].md"
        existing_file.write_text(existing_md)

        # Save with same title
        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            save_to_cache(
                "abc123", "New transcript", "SUMMARY:\nNew summary", title="Amazing Tutorial"
            )

        # File should still exist
        assert existing_file.exists()

        content = existing_file.read_text()
        assert "New transcript" in content
        assert "New summary" in content

    def test_save_to_cache_with_sanitized_title(self, tmp_path: Path) -> None:
        """Handle titles with special characters in filename."""
        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            save_to_cache(
                "abc123", "Transcript", "SUMMARY:\nSummary", title="Tutorial: Part 1 <HD>"
            )

        # sanitize_filename replaces special chars with space and normalizes
        # Expected: "Tutorial Part 1 HD [abc123].md"
        # Use rglob to find all .md files and check manually (glob pattern with brackets doesn't work)
        summaries_dir = tmp_path / "Summaries"
        md_files = [f for f in summaries_dir.rglob("*.md") if "abc123" in f.name]
        assert len(md_files) == 1
        # Check the file contains the content
        assert "Transcript" in md_files[0].read_text()

    def test_save_to_cache_with_unicode_title(self, tmp_path: Path) -> None:
        """Handle unicode characters in title filename."""
        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            save_to_cache("abc123", "Transcript", "SUMMARY:\nSummary", title="世界 Hello")

        cache_file = tmp_path / "Summaries" / "世界 Hello [abc123].md"
        assert cache_file.exists()

        content = cache_file.read_text(encoding="utf-8")
        assert 'title: "世界 Hello"' in content

    def test_save_to_cache_empty_title_uses_minimal_format(self, tmp_path: Path) -> None:
        """Use minimal format when title is empty string."""
        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            save_to_cache("abc123", "Transcript", "SUMMARY:\nSummary", title="")

        minimal_file = tmp_path / "Summaries" / "[abc123].md"
        assert minimal_file.exists()

        titled_file = tmp_path / "Summaries" / " [abc123].md"
        assert not titled_file.exists()

    def test_save_to_cache_renames_different_title(self, tmp_path: Path) -> None:
        """Rename when saving with different title."""
        # Create file with old title (old format)
        old_md = """---
video_id: abc123
title: Old Title
url: https://www.youtube.com/watch?v=abc123
cached_at: 2026-01-01T00:00:00+00:00
---
# Old Title

## Full Transcript

Transcript
"""
        old_file = tmp_path / "abc123 – Old Title.md"
        old_file.write_text(old_md)

        # Save with new title - should migrate to new format
        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            save_to_cache("abc123", "Transcript", "SUMMARY:\nSummary", title="New Title")

        # Old file should be deleted
        assert not old_file.exists()

        # New file should exist with new format under Summaries/
        new_file = tmp_path / "Summaries" / "New Title [abc123].md"
        assert new_file.exists()

        content = new_file.read_text()
        assert 'title: "New Title"' in content


class TestLoadCacheWithTitle:
    """Test loading cache files with new filename format."""

    def test_load_cache_with_new_format(self, tmp_path: Path) -> None:
        """Load cache from new markdown format file."""
        channel_dir = tmp_path / "Tech Channel"
        channel_dir.mkdir()
        markdown_content = """---
video_id: abc123
title: Amazing Tutorial
channel: Tech Channel
url: https://www.youtube.com/watch?v=abc123
cached_at: 2026-01-01T00:00:00+00:00
---
# Amazing Tutorial

## Summary

Summary content

## Full Transcript

Transcript content
"""
        cache_file = channel_dir / "Amazing Tutorial [abc123].md"
        cache_file.write_text(markdown_content)

        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            result = load_cache("abc123")

        assert result["video_id"] == "abc123"
        assert result["title"] == "Amazing Tutorial"
        assert result["channel"] == "Tech Channel"
        assert "Transcript content" in result["full_text"]
        assert "Summary content" in result["summary"]

    def test_load_cache_with_legacy_json_format(self, tmp_path: Path) -> None:
        """Load cache from legacy JSON format file."""
        cache_file = tmp_path / "abc123.json"
        test_data = {"video_id": "abc123", "full_text": "Transcript", "summary": "Summary"}
        cache_file.write_text(json.dumps(test_data))

        with (
            patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path),
            patch("yt_summary.cache.save_to_cache"),
        ):
            result = load_cache("abc123")

        assert result["video_id"] == "abc123"
        assert result["full_text"] == "Transcript"

    def test_load_cache_finds_either_format(self, tmp_path: Path) -> None:
        """Load cache regardless of filename format."""
        # Test with old markdown format
        markdown_content = """---
video_id: video1
title: Title
url: https://www.youtube.com/watch?v=video1
cached_at: 2026-01-01T00:00:00+00:00
---
# Title

## Full Transcript

Content
"""
        cache_file = tmp_path / "video1 – Title.md"
        cache_file.write_text(markdown_content)

        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            result = load_cache("video1")
        assert result is not None
        assert result["title"] == "Title"
        cache_file.unlink()

        # Test with legacy JSON format
        cache_file = tmp_path / "video1.json"
        cache_file.write_text(json.dumps({"video_id": "video1", "full_text": "Test"}))

        with (
            patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path),
            patch("yt_summary.cache.save_to_cache"),
        ):
            result = load_cache("video1")
        assert result is not None


class TestIsLegacyFilename:
    """Test detection of legacy cache filename format."""

    def test_is_legacy_filename_with_legacy_json_format(self, tmp_path: Path) -> None:
        """Detect legacy JSON format file (video_id.json)."""
        cache_file = tmp_path / "abc123.json"
        cache_file.write_text(json.dumps({"video_id": "abc123"}))

        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            result = is_legacy_filename("abc123")

        assert result is True

    def test_is_legacy_filename_with_legacy_md_format(self, tmp_path: Path) -> None:
        """Detect legacy markdown format file (video_id.md without title)."""
        cache_file = tmp_path / "abc123.md"
        cache_file.write_text("---\nvideo_id: abc123\n---")

        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            result = is_legacy_filename("abc123")

        assert result is True

    def test_is_legacy_filename_with_old_format_is_legacy(self, tmp_path: Path) -> None:
        """Detect old format file (video_id – title.md) as legacy."""
        cache_file = tmp_path / "abc123 – Amazing Tutorial.md"
        cache_file.write_text("---\nvideo_id: abc123\n---")

        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            result = is_legacy_filename("abc123")

        assert result is True

    def test_is_legacy_filename_with_new_format(self, tmp_path: Path) -> None:
        """Detect new format file (title [video_id].md) as not legacy."""
        channel_dir = tmp_path / "Summaries" / "Tech Channel"
        channel_dir.mkdir(parents=True)
        cache_file = channel_dir / "Amazing Tutorial [abc123].md"
        cache_file.write_text("---\nvideo_id: abc123\n---")

        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            result = is_legacy_filename("abc123")

        assert result is False

    def test_is_legacy_filename_with_flat_structure_is_legacy(self, tmp_path: Path) -> None:
        """Detect file in flat structure (no channel subdirectory) as legacy."""
        cache_file = tmp_path / "Tutorial [abc123].md"
        cache_file.write_text("---\nvideo_id: abc123\n---")

        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            result = is_legacy_filename("abc123")

        assert result is True

    def test_is_legacy_filename_no_cache_file(self, tmp_path: Path) -> None:
        """Return False when no cache file exists."""
        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            result = is_legacy_filename("nonexistent")

        assert result is False

    def test_is_legacy_filename_with_partial_match(self, tmp_path: Path) -> None:
        """Return True when cache file starts with video_id (old glob behavior)."""
        cache_file = tmp_path / "abc123extra.md"
        cache_file.write_text("---\nvideo_id: abc123extra\n---")

        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=tmp_path):
            result = is_legacy_filename("abc123")

        # The old format glob pattern matches any file starting with video_id
        # So abc123extra.md matches abc123*.md and is considered legacy
        assert result is True

    def test_is_legacy_filename_cache_dir_not_exists(self, tmp_path: Path) -> None:
        """Return False when cache directory doesn't exist."""
        nonexistent_dir = tmp_path / "nonexistent"

        with patch("yt_summary.cache.get_obsidian_vault_path", return_value=nonexistent_dir):
            result = is_legacy_filename("abc123")

        assert result is False
