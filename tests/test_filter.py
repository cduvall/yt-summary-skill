"""Tests for video filtering."""

from yt_summary.filter import keyword_filter


class TestKeywordFilter:
    """Test keyword-based video filtering."""

    def test_no_filters_returns_all(self) -> None:
        """Return all videos when no filters are specified."""
        videos = [
            {"title": "Python Tutorial", "description": "Learn Python"},
            {"title": "JavaScript Guide", "description": "Learn JS"},
        ]

        filtered, reasons = keyword_filter(videos, [], [])

        assert len(filtered) == 2

    def test_include_filter_matches(self) -> None:
        """Include only videos matching at least one keyword."""
        videos = [
            {"title": "Python Tutorial", "description": "Learn Python"},
            {"title": "JavaScript Guide", "description": "Learn JS"},
            {"title": "React Course", "description": "Build web apps"},
        ]

        filtered, reasons = keyword_filter(videos, ["python", "react"], [])

        assert len(filtered) == 2
        assert filtered[0]["title"] == "Python Tutorial"
        assert filtered[1]["title"] == "React Course"

    def test_exclude_filter_removes(self) -> None:
        """Exclude videos matching any exclude keyword in title."""
        videos = [
            {"title": "Python Tutorial", "description": "Learn Python"},
            {"title": "Sponsored Python Course", "description": "Great content"},
            {"title": "JavaScript Guide", "description": "Learn JS"},
        ]

        filtered, reasons = keyword_filter(videos, [], ["sponsored"])

        assert len(filtered) == 2
        assert all("sponsored" not in v["title"].lower() for v in filtered)

    def test_include_and_exclude_combined(self) -> None:
        """Apply both include and exclude filters."""
        videos = [
            {"title": "Python Tutorial", "description": "Learn Python"},
            {"title": "Sponsored Python Ads", "description": "Python course"},
            {"title": "JavaScript Guide", "description": "Learn JS"},
        ]

        filtered, reasons = keyword_filter(videos, ["python"], ["sponsored"])

        assert len(filtered) == 1
        assert filtered[0]["title"] == "Python Tutorial"

    def test_case_insensitive_matching(self) -> None:
        """Match keywords case-insensitively."""
        videos = [
            {"title": "PYTHON Tutorial", "description": "learn PYTHON"},
            {"title": "JavaScript Guide", "description": "Learn JS"},
        ]

        filtered, reasons = keyword_filter(videos, ["python"], [])

        assert len(filtered) == 1

    def test_searches_title_only(self) -> None:
        """Search only in title, not description."""
        videos = [
            {"title": "Tutorial", "description": "Learn Python"},
            {"title": "Python Guide", "description": "Advanced topics"},
        ]

        filtered, reasons = keyword_filter(videos, ["python"], [])

        assert len(filtered) == 1
        assert filtered[0]["title"] == "Python Guide"

    def test_empty_video_list(self) -> None:
        """Handle empty video list."""
        filtered, reasons = keyword_filter([], ["python"], ["sponsored"])
        assert len(filtered) == 0

    def test_missing_description_field(self) -> None:
        """Handle videos without description field."""
        videos = [
            {"title": "Python Tutorial"},
            {"title": "JavaScript Guide", "description": ""},
        ]

        filtered, reasons = keyword_filter(videos, ["python"], [])

        assert len(filtered) == 1
        assert filtered[0]["title"] == "Python Tutorial"

    def test_whole_word_matching(self) -> None:
        """Match whole words only, not substrings."""
        videos = [
            {"title": "My portfolio site", "description": ""},
            {"title": "lofi beats to study", "description": ""},
            {"title": "Online radio station", "description": ""},
        ]
        filtered, reasons = keyword_filter(videos, [], ["lofi", "radio"])
        assert len(filtered) == 1
        assert filtered[0]["title"] == "My portfolio site"

    def test_returns_matched_keyword_reason(self) -> None:
        """Return reason dict with matched keyword for removed videos."""
        videos = [
            {"video_id": "vid1", "title": "Python Tutorial", "description": ""},
            {"video_id": "vid2", "title": "Sponsored Content", "description": ""},
        ]
        filtered, reasons = keyword_filter(videos, [], ["sponsored"])
        assert len(filtered) == 1
        assert "vid2" in reasons
        assert "sponsored" in reasons["vid2"].lower()
