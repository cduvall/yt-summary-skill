"""Tests for batch subscription processing."""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

from yt_summary.subscriptions import run_subscriptions


class TestRunSubscriptions:
    """Test batch subscription processing workflow."""

    @patch("yt_summary.subscriptions.get_oauth_dir")
    @patch("yt_summary.subscriptions.get_credentials")
    @patch("yt_summary.subscriptions.get_subscribed_channels")
    @patch("yt_summary.subscriptions.get_recent_videos")
    @patch("yt_summary.subscriptions.load_cache")
    @patch("yt_summary.subscriptions.get_video_durations")
    def test_dry_run_prints_filtered_videos(
        self,
        mock_get_durations,
        mock_load_cache,
        mock_get_videos,
        mock_get_channels,
        mock_get_creds,
        mock_oauth_dir,
        caplog,
    ) -> None:
        """Dry run prints filtered videos without processing."""
        import logging

        caplog.set_level(logging.INFO)
        mock_oauth_dir.return_value = "/fake/path"
        mock_get_creds.return_value = Mock()
        mock_get_channels.return_value = [{"channel_id": "UC123", "title": "Channel"}]

        now = datetime.now(timezone.utc)
        mock_get_videos.return_value = [
            {
                "video_id": "vid1",
                "title": "Test Video",
                "description": "Test",
                "published_at": now,
                "channel": "Channel",
            }
        ]

        mock_load_cache.return_value = None  # Not cached
        mock_get_durations.return_value = {"vid1": 600}

        result = run_subscriptions(
            days=7,
            include_keywords=[],
            exclude_keywords=[],
            model="claude-model",
            lang="en",
            api_key="test-key",
            dry_run=True,
            max_videos=50,
        )

        assert result == 0
        assert "DRY RUN" in caplog.text
        assert "Test Video" in caplog.text

    @patch("yt_summary.subscriptions.get_oauth_dir")
    @patch("yt_summary.subscriptions.get_credentials")
    @patch("yt_summary.subscriptions.get_subscribed_channels")
    @patch("yt_summary.subscriptions.get_recent_videos")
    @patch("yt_summary.subscriptions.load_cache")
    @patch("yt_summary.subscriptions.get_video_durations")
    @patch("yt_summary.subscriptions.fetch_transcript")
    @patch("yt_summary.subscriptions.summarize_transcript")
    @patch("yt_summary.subscriptions.save_to_cache")
    def test_processes_videos_successfully(
        self,
        mock_save,
        mock_summarize,
        mock_fetch_transcript,
        mock_get_durations,
        mock_load_cache,
        mock_get_videos,
        mock_get_channels,
        mock_get_creds,
        mock_oauth_dir,
        caplog,
    ) -> None:
        """Process videos and generate summaries."""
        import logging

        caplog.set_level(logging.INFO)
        mock_oauth_dir.return_value = "/fake/path"
        mock_get_creds.return_value = Mock()
        mock_get_channels.return_value = [{"channel_id": "UC123", "title": "Channel"}]

        now = datetime.now(timezone.utc)
        mock_get_videos.return_value = [
            {
                "video_id": "vid1",
                "title": "Test Video",
                "description": "Test",
                "published_at": now,
                "channel": "Channel",
            }
        ]

        mock_load_cache.return_value = None
        mock_get_durations.return_value = {"vid1": 600}
        mock_fetch_transcript.return_value = "Transcript text"
        mock_summarize.return_value = "Summary text"

        result = run_subscriptions(
            days=7,
            include_keywords=[],
            exclude_keywords=[],
            model="claude-model",
            lang="en",
            api_key="test-key",
            dry_run=False,
            max_videos=50,
        )

        assert result == 0
        mock_fetch_transcript.assert_called_once_with("vid1", language_code="en")
        mock_summarize.assert_called_once()
        mock_save.assert_called_once()

        assert "Processed 1 videos" in caplog.text

    @patch("yt_summary.subscriptions.get_oauth_dir")
    @patch("yt_summary.subscriptions.get_credentials")
    @patch("yt_summary.subscriptions.get_subscribed_channels")
    @patch("yt_summary.subscriptions.get_recent_videos")
    @patch("yt_summary.subscriptions.load_cache")
    def test_skips_cached_videos(
        self,
        mock_load_cache,
        mock_get_videos,
        mock_get_channels,
        mock_get_creds,
        mock_oauth_dir,
        caplog,
    ) -> None:
        """Skip videos already cached with summaries."""
        import logging

        caplog.set_level(logging.INFO)
        mock_oauth_dir.return_value = "/fake/path"
        mock_get_creds.return_value = Mock()
        mock_get_channels.return_value = [{"channel_id": "UC123", "title": "Channel"}]

        now = datetime.now(timezone.utc)
        mock_get_videos.return_value = [
            {
                "video_id": "vid1",
                "title": "Cached Video",
                "description": "",
                "published_at": now,
                "channel": "Channel",
            }
        ]

        mock_load_cache.return_value = {
            "video_id": "vid1",
            "full_text": "transcript",
            "summary": "existing summary",
        }

        result = run_subscriptions(
            days=7,
            include_keywords=[],
            exclude_keywords=[],
            model="claude-model",
            lang="en",
            api_key="test-key",
            dry_run=False,
            max_videos=50,
        )

        assert result == 0
        assert "Skipped 1 videos already cached" in caplog.text
        assert "No videos to process" in caplog.text

    @patch("yt_summary.subscriptions.get_oauth_dir")
    @patch("yt_summary.subscriptions.get_credentials")
    @patch("yt_summary.subscriptions.get_subscribed_channels")
    @patch("yt_summary.subscriptions.get_recent_videos")
    @patch("yt_summary.subscriptions.load_cache")
    @patch("yt_summary.subscriptions.get_video_durations")
    @patch("yt_summary.subscriptions.keyword_filter")
    def test_applies_keyword_filter(
        self,
        mock_keyword_filter,
        mock_get_durations,
        mock_load_cache,
        mock_get_videos,
        mock_get_channels,
        mock_get_creds,
        mock_oauth_dir,
        capsys,
    ) -> None:
        """Apply keyword filters before processing."""
        mock_oauth_dir.return_value = "/fake/path"
        mock_get_creds.return_value = Mock()
        mock_get_channels.return_value = [{"channel_id": "UC123", "title": "Channel"}]

        now = datetime.now(timezone.utc)
        videos = [
            {
                "video_id": "vid1",
                "title": "Python Video",
                "description": "",
                "published_at": now,
                "channel": "Channel",
            }
        ]
        mock_get_videos.return_value = videos
        mock_load_cache.return_value = None
        mock_get_durations.return_value = {"vid1": 600}
        mock_keyword_filter.return_value = (videos, {})  # Pass through

        run_subscriptions(
            days=7,
            include_keywords=["python"],
            exclude_keywords=["sponsored"],
            model="claude-model",
            lang="en",
            api_key="test-key",
            dry_run=True,
            max_videos=50,
        )

        mock_keyword_filter.assert_called_once_with(videos, ["python"], ["sponsored"])

    @patch("yt_summary.subscriptions.get_oauth_dir")
    @patch("yt_summary.subscriptions.get_credentials")
    @patch("yt_summary.subscriptions.get_subscribed_channels")
    @patch("yt_summary.subscriptions.get_recent_videos")
    @patch("yt_summary.subscriptions.load_cache")
    @patch("yt_summary.subscriptions.get_video_durations")
    @patch("yt_summary.subscriptions.keyword_filter")
    def test_keyword_filter_removes_videos_prints_count(
        self,
        mock_keyword_filter,
        mock_get_durations,
        mock_load_cache,
        mock_get_videos,
        mock_get_channels,
        mock_get_creds,
        mock_oauth_dir,
        caplog,
    ) -> None:
        """Print count when keyword filter removes videos."""
        import logging

        caplog.set_level(logging.INFO)
        mock_oauth_dir.return_value = "/fake/path"
        mock_get_creds.return_value = Mock()
        mock_get_channels.return_value = [{"channel_id": "UC123", "title": "Channel"}]

        now = datetime.now(timezone.utc)
        videos = [
            {
                "video_id": "vid1",
                "title": "Python Video",
                "description": "",
                "published_at": now,
                "channel": "Channel",
            },
            {
                "video_id": "vid2",
                "title": "Sponsored Content",
                "description": "",
                "published_at": now,
                "channel": "Channel",
            },
        ]
        mock_get_videos.return_value = videos
        mock_load_cache.return_value = None
        mock_get_durations.return_value = {"vid1": 600, "vid2": 600}
        # Filter removes one video
        mock_keyword_filter.return_value = (
            [videos[0]],
            {"vid2": "matched exclude keyword: sponsored"},
        )

        run_subscriptions(
            days=7,
            include_keywords=["python"],
            exclude_keywords=["sponsored"],
            model="claude-model",
            lang="en",
            api_key="test-key",
            dry_run=True,
            max_videos=50,
        )

        assert "Keyword filter removed 1 videos" in caplog.text

    @patch("yt_summary.subscriptions.get_oauth_dir")
    @patch("yt_summary.subscriptions.get_credentials")
    @patch("yt_summary.subscriptions.get_subscribed_channels")
    @patch("yt_summary.subscriptions.get_recent_videos")
    @patch("yt_summary.subscriptions.load_cache")
    @patch("yt_summary.subscriptions.get_video_durations")
    def test_applies_max_videos_cap(
        self,
        mock_get_durations,
        mock_load_cache,
        mock_get_videos,
        mock_get_channels,
        mock_get_creds,
        mock_oauth_dir,
        caplog,
    ) -> None:
        """Cap number of videos to process."""
        import logging

        caplog.set_level(logging.INFO)
        mock_oauth_dir.return_value = "/fake/path"
        mock_get_creds.return_value = Mock()
        mock_get_channels.return_value = [{"channel_id": "UC123", "title": "Channel"}]

        now = datetime.now(timezone.utc)
        # Create 100 videos
        videos = [
            {
                "video_id": f"vid{i}",
                "title": f"Video {i}",
                "description": "",
                "published_at": now,
                "channel": "Channel",
            }
            for i in range(100)
        ]
        mock_get_videos.return_value = videos
        mock_load_cache.return_value = None
        mock_get_durations.return_value = {f"vid{i}": 600 for i in range(100)}

        run_subscriptions(
            days=7,
            include_keywords=[],
            exclude_keywords=[],
            model="claude-model",
            lang="en",
            api_key="test-key",
            dry_run=True,
            max_videos=10,
        )

        # Pre-processing cap is removed; dry run shows all candidates
        assert "Filtered to 100 videos to process" in caplog.text

    @patch("yt_summary.subscriptions.get_oauth_dir")
    @patch("yt_summary.subscriptions.get_credentials")
    @patch("yt_summary.subscriptions.get_subscribed_channels")
    @patch("yt_summary.subscriptions.get_recent_videos")
    @patch("yt_summary.subscriptions.load_cache")
    @patch("yt_summary.subscriptions.get_video_durations")
    @patch("yt_summary.subscriptions.fetch_transcript")
    @patch("yt_summary.subscriptions.summarize_transcript")
    @patch("yt_summary.subscriptions.save_to_cache")
    def test_max_videos_caps_successful_not_total(
        self,
        mock_save,
        mock_summarize,
        mock_fetch_transcript,
        mock_get_durations,
        mock_load_cache,
        mock_get_videos,
        mock_get_channels,
        mock_get_creds,
        mock_oauth_dir,
        caplog,
    ) -> None:
        """max_videos limits successful completions, not total attempts."""
        import logging

        from yt_summary.transcript import TranscriptError

        caplog.set_level(logging.INFO)
        mock_oauth_dir.return_value = "/fake/path"
        mock_get_creds.return_value = Mock()
        mock_get_channels.return_value = [{"channel_id": "UC123", "title": "Channel"}]

        now = datetime.now(timezone.utc)
        mock_get_videos.return_value = [
            {
                "video_id": f"vid{i}",
                "title": f"Video {i}",
                "description": "",
                "published_at": now,
                "channel": "Channel",
            }
            for i in range(5)
        ]

        mock_load_cache.return_value = None
        mock_get_durations.return_value = {f"vid{i}": 600 for i in range(5)}
        # First 2 raise TranscriptError, next 3 succeed
        mock_fetch_transcript.side_effect = [
            TranscriptError("No transcript"),
            TranscriptError("No transcript"),
            "Transcript text",
            "Transcript text",
            "Transcript text",
        ]
        mock_summarize.return_value = "Summary text"

        result = run_subscriptions(
            days=7,
            include_keywords=[],
            exclude_keywords=[],
            model="claude-model",
            lang="en",
            api_key="test-key",
            dry_run=False,
            max_videos=2,
        )

        assert result == 0
        assert mock_summarize.call_count == 2
        assert mock_save.call_count == 2
        assert "Processed 2 videos" in caplog.text
        assert "2 no transcript" in caplog.text
        assert "0 error(s)" in caplog.text

    @patch("yt_summary.subscriptions.get_oauth_dir")
    @patch("yt_summary.subscriptions.get_credentials")
    @patch("yt_summary.subscriptions.get_subscribed_channels")
    @patch("yt_summary.subscriptions.get_recent_videos")
    @patch("yt_summary.subscriptions.load_cache")
    @patch("yt_summary.subscriptions.get_video_durations")
    @patch("yt_summary.subscriptions.fetch_transcript")
    @patch("yt_summary.subscriptions.summarize_transcript")
    @patch("yt_summary.subscriptions.save_to_cache")
    def test_continues_on_transcript_error(
        self,
        mock_save,
        mock_summarize,
        mock_fetch_transcript,
        mock_get_durations,
        mock_load_cache,
        mock_get_videos,
        mock_get_channels,
        mock_get_creds,
        mock_oauth_dir,
        caplog,
    ) -> None:
        """Continue processing when transcript fetch fails."""
        import logging

        from yt_summary.transcript import TranscriptError

        caplog.set_level(logging.INFO)
        mock_oauth_dir.return_value = "/fake/path"
        mock_get_creds.return_value = Mock()
        mock_get_channels.return_value = [{"channel_id": "UC123", "title": "Channel"}]

        now = datetime.now(timezone.utc)
        mock_get_videos.return_value = [
            {
                "video_id": "vid1",
                "title": "No Transcript",
                "description": "",
                "published_at": now,
                "channel": "Channel",
            }
        ]

        mock_load_cache.return_value = None
        mock_get_durations.return_value = {"vid1": 600}
        mock_fetch_transcript.side_effect = TranscriptError("No transcript")

        result = run_subscriptions(
            days=7,
            include_keywords=[],
            exclude_keywords=[],
            model="claude-model",
            lang="en",
            api_key="test-key",
            dry_run=False,
            max_videos=50,
        )

        assert result == 0
        assert "Processed 0 videos" in caplog.text
        assert "1 no transcript" in caplog.text

    @patch("yt_summary.subscriptions.get_oauth_dir")
    @patch("yt_summary.subscriptions.get_credentials")
    def test_returns_error_on_auth_failure(self, mock_get_creds, mock_oauth_dir) -> None:
        """Return error code when authentication fails."""
        from yt_summary.youtube_api import YouTubeAPIError

        mock_oauth_dir.return_value = "/fake/path"
        mock_get_creds.side_effect = YouTubeAPIError("Auth failed")

        result = run_subscriptions(
            days=7,
            include_keywords=[],
            exclude_keywords=[],
            model="claude-model",
            lang="en",
            api_key="test-key",
            dry_run=False,
            max_videos=50,
        )

        assert result == 1

    @patch("yt_summary.subscriptions.get_oauth_dir")
    @patch("yt_summary.subscriptions.get_credentials")
    @patch("yt_summary.subscriptions.get_subscribed_channels")
    @patch("yt_summary.subscriptions.get_recent_videos")
    @patch("yt_summary.subscriptions.load_cache")
    @patch("yt_summary.subscriptions.get_video_durations")
    def test_deduplicates_videos(
        self,
        mock_get_durations,
        mock_load_cache,
        mock_get_videos,
        mock_get_channels,
        mock_get_creds,
        mock_oauth_dir,
        caplog,
    ) -> None:
        """Deduplicate videos with same video_id."""
        import logging

        caplog.set_level(logging.INFO)
        mock_oauth_dir.return_value = "/fake/path"
        mock_get_creds.return_value = Mock()
        mock_get_channels.return_value = [
            {"channel_id": "UC123", "title": "Channel 1"},
            {"channel_id": "UC456", "title": "Channel 2"},
        ]

        now = datetime.now(timezone.utc)
        # Same video_id from different channels
        duplicate_video = {
            "video_id": "vid1",
            "title": "Duplicate",
            "description": "",
            "published_at": now,
            "channel": "Channel",
        }
        mock_get_videos.return_value = [duplicate_video]
        mock_load_cache.return_value = None
        mock_get_durations.return_value = {"vid1": 600}

        run_subscriptions(
            days=7,
            include_keywords=[],
            exclude_keywords=[],
            model="claude-model",
            lang="en",
            api_key="test-key",
            dry_run=True,
            max_videos=50,
        )

        assert "Deduplicated to 1 unique videos" in caplog.text

    @patch("yt_summary.subscriptions.get_oauth_dir")
    @patch("yt_summary.subscriptions.get_credentials")
    @patch("yt_summary.subscriptions.get_subscribed_channels")
    @patch("yt_summary.subscriptions.get_recent_videos")
    def test_continues_on_channel_fetch_error(
        self,
        mock_get_videos,
        mock_get_channels,
        mock_get_creds,
        mock_oauth_dir,
        caplog,
    ) -> None:
        """Continue processing when fetching videos from a channel fails."""
        from yt_summary.youtube_api import YouTubeAPIError

        mock_oauth_dir.return_value = "/fake/path"
        mock_get_creds.return_value = Mock()
        mock_get_channels.return_value = [
            {"channel_id": "UC123", "title": "Good Channel"},
            {"channel_id": "UC456", "title": "Bad Channel"},
        ]

        # First channel succeeds, second fails
        mock_get_videos.side_effect = [
            [],  # Good channel returns no videos
            YouTubeAPIError("Channel unavailable"),  # Bad channel fails
        ]

        result = run_subscriptions(
            days=7,
            include_keywords=[],
            exclude_keywords=[],
            model="claude-model",
            lang="en",
            api_key="test-key",
            dry_run=True,
            max_videos=50,
        )

        # Should complete successfully despite one channel failing
        assert result == 0
        assert "Failed to fetch videos from Bad Channel" in caplog.text

    @patch("yt_summary.subscriptions.get_oauth_dir")
    @patch("yt_summary.subscriptions.get_credentials")
    @patch("yt_summary.subscriptions.get_subscribed_channels")
    @patch("yt_summary.subscriptions.get_recent_videos")
    @patch("yt_summary.subscriptions.load_cache")
    @patch("yt_summary.subscriptions.get_video_durations")
    @patch("yt_summary.subscriptions.fetch_transcript")
    @patch("yt_summary.subscriptions.summarize_transcript")
    @patch("yt_summary.subscriptions.save_to_cache")
    def test_continues_on_summarizer_error(
        self,
        mock_save,
        mock_summarize,
        mock_fetch_transcript,
        mock_get_durations,
        mock_load_cache,
        mock_get_videos,
        mock_get_channels,
        mock_get_creds,
        mock_oauth_dir,
        caplog,
    ) -> None:
        """Continue processing when summarization fails."""
        import logging

        from yt_summary.summarizer import SummarizerError

        caplog.set_level(logging.INFO)
        mock_oauth_dir.return_value = "/fake/path"
        mock_get_creds.return_value = Mock()
        mock_get_channels.return_value = [{"channel_id": "UC123", "title": "Channel"}]

        now = datetime.now(timezone.utc)
        mock_get_videos.return_value = [
            {
                "video_id": "vid1",
                "title": "Test Video",
                "description": "",
                "published_at": now,
                "channel": "Channel",
            }
        ]

        mock_load_cache.return_value = None
        mock_get_durations.return_value = {"vid1": 600}
        mock_fetch_transcript.return_value = "Transcript text"
        mock_summarize.side_effect = SummarizerError("API rate limit")

        result = run_subscriptions(
            days=7,
            include_keywords=[],
            exclude_keywords=[],
            model="claude-model",
            lang="en",
            api_key="test-key",
            dry_run=False,
            max_videos=50,
        )

        assert result == 0
        assert "Processed 0 videos" in caplog.text
        assert "1 error(s)" in caplog.text

    @patch("yt_summary.subscriptions.get_oauth_dir")
    @patch("yt_summary.subscriptions.get_credentials")
    @patch("yt_summary.subscriptions.get_subscribed_channels")
    @patch("yt_summary.subscriptions.get_recent_videos")
    @patch("yt_summary.subscriptions.load_cache")
    @patch("yt_summary.subscriptions.get_video_durations")
    @patch("yt_summary.subscriptions.fetch_transcript")
    @patch("yt_summary.subscriptions.summarize_transcript")
    @patch("yt_summary.subscriptions.save_to_cache")
    def test_continues_on_unexpected_error(
        self,
        mock_save,
        mock_summarize,
        mock_fetch_transcript,
        mock_get_durations,
        mock_load_cache,
        mock_get_videos,
        mock_get_channels,
        mock_get_creds,
        mock_oauth_dir,
        caplog,
    ) -> None:
        """Continue processing on unexpected errors during video processing."""
        import logging

        caplog.set_level(logging.INFO)
        mock_oauth_dir.return_value = "/fake/path"
        mock_get_creds.return_value = Mock()
        mock_get_channels.return_value = [{"channel_id": "UC123", "title": "Channel"}]

        now = datetime.now(timezone.utc)
        mock_get_videos.return_value = [
            {
                "video_id": "vid1",
                "title": "Test Video",
                "description": "",
                "published_at": now,
                "channel": "Channel",
            }
        ]

        mock_load_cache.return_value = None
        mock_get_durations.return_value = {"vid1": 600}
        mock_fetch_transcript.side_effect = RuntimeError("Unexpected network error")

        result = run_subscriptions(
            days=7,
            include_keywords=[],
            exclude_keywords=[],
            model="claude-model",
            lang="en",
            api_key="test-key",
            dry_run=False,
            max_videos=50,
        )

        assert result == 0
        assert "Unexpected error: RuntimeError" in caplog.text
        assert "Processed 0 videos" in caplog.text

    @patch("yt_summary.subscriptions.get_oauth_dir")
    @patch("yt_summary.subscriptions.get_credentials")
    def test_returns_error_on_unexpected_exception(self, mock_get_creds, mock_oauth_dir) -> None:
        """Return error code for unexpected exceptions in main workflow."""
        mock_oauth_dir.return_value = "/fake/path"
        mock_get_creds.side_effect = RuntimeError("Unexpected error")

        result = run_subscriptions(
            days=7,
            include_keywords=[],
            exclude_keywords=[],
            model="claude-model",
            lang="en",
            api_key="test-key",
            dry_run=False,
            max_videos=50,
        )

        assert result == 1

    @patch("yt_summary.subscriptions.get_oauth_dir")
    @patch("yt_summary.subscriptions.get_credentials")
    @patch("yt_summary.subscriptions.get_subscribed_channels")
    @patch("yt_summary.subscriptions.get_recent_videos")
    @patch("yt_summary.subscriptions.load_cache")
    @patch("yt_summary.subscriptions.get_video_durations")
    def test_excludes_channels_by_name(
        self,
        mock_get_durations,
        mock_load_cache,
        mock_get_videos,
        mock_get_channels,
        mock_get_creds,
        mock_oauth_dir,
        caplog,
    ) -> None:
        """Exclude channels by name before fetching videos."""
        import logging

        caplog.set_level(logging.INFO)
        mock_oauth_dir.return_value = "/fake/path"
        mock_get_creds.return_value = Mock()
        mock_get_channels.return_value = [
            {"channel_id": "UC123", "title": "@FantasyLofi"},
            {"channel_id": "UC456", "title": "@TechChannel"},
        ]

        now = datetime.now(timezone.utc)
        mock_get_videos.return_value = [
            {
                "video_id": "vid1",
                "title": "Test Video",
                "description": "",
                "published_at": now,
                "channel": "@TechChannel",
            }
        ]
        mock_load_cache.return_value = None
        mock_get_durations.return_value = {"vid1": 600}

        run_subscriptions(
            days=7,
            include_keywords=[],
            exclude_keywords=[],
            model="claude-model",
            lang="en",
            api_key="test-key",
            dry_run=True,
            max_videos=50,
            exclude_channels=["@FantasyLofi"],
        )

        # Should only call get_recent_videos once (for the non-excluded channel)
        assert mock_get_videos.call_count == 1
        assert "Skipping @FantasyLofi (excluded)" in caplog.text
        assert "Excluded 1 channels by name" in caplog.text

    @patch("yt_summary.subscriptions.get_oauth_dir")
    @patch("yt_summary.subscriptions.get_credentials")
    @patch("yt_summary.subscriptions.get_subscribed_channels")
    @patch("yt_summary.subscriptions.get_recent_videos")
    @patch("yt_summary.subscriptions.load_cache")
    @patch("yt_summary.subscriptions.get_video_durations")
    def test_exclude_channels_case_insensitive(
        self,
        mock_get_durations,
        mock_load_cache,
        mock_get_videos,
        mock_get_channels,
        mock_get_creds,
        mock_oauth_dir,
        caplog,
    ) -> None:
        """Exclude channels using case-insensitive name matching."""
        import logging

        caplog.set_level(logging.INFO)
        mock_oauth_dir.return_value = "/fake/path"
        mock_get_creds.return_value = Mock()
        mock_get_channels.return_value = [
            {"channel_id": "UC123", "title": "FantasyLofi"},
            {"channel_id": "UC456", "title": "@TechChannel"},
        ]

        now = datetime.now(timezone.utc)
        mock_get_videos.return_value = [
            {
                "video_id": "vid1",
                "title": "Test Video",
                "description": "",
                "published_at": now,
                "channel": "@TechChannel",
            }
        ]
        mock_load_cache.return_value = None
        mock_get_durations.return_value = {"vid1": 600}

        run_subscriptions(
            days=7,
            include_keywords=[],
            exclude_keywords=[],
            model="claude-model",
            lang="en",
            api_key="test-key",
            dry_run=True,
            max_videos=50,
            exclude_channels=["fantasylofi"],
        )

        # Lowercase exclude name should match title "FantasyLofi"
        assert mock_get_videos.call_count == 1
        assert "Skipping FantasyLofi (excluded)" in caplog.text
        assert "Excluded 1 channels by name" in caplog.text

    @patch("yt_summary.subscriptions.get_oauth_dir")
    @patch("yt_summary.subscriptions.get_credentials")
    @patch("yt_summary.subscriptions.get_subscribed_channels")
    @patch("yt_summary.subscriptions.get_recent_videos")
    @patch("yt_summary.subscriptions.load_cache")
    @patch("yt_summary.subscriptions.get_video_durations")
    def test_exclude_channels_warns_unmatched_name(
        self,
        mock_get_durations,
        mock_load_cache,
        mock_get_videos,
        mock_get_channels,
        mock_get_creds,
        mock_oauth_dir,
        caplog,
    ) -> None:
        """Warn when an exclude_channels name matches no subscription."""
        import logging

        caplog.set_level(logging.WARNING)
        mock_oauth_dir.return_value = "/fake/path"
        mock_get_creds.return_value = Mock()
        mock_get_channels.return_value = [
            {"channel_id": "UC123", "title": "@TechChannel"},
        ]

        now = datetime.now(timezone.utc)
        mock_get_videos.return_value = [
            {
                "video_id": "vid1",
                "title": "Test Video",
                "description": "",
                "published_at": now,
                "channel": "@TechChannel",
            }
        ]
        mock_load_cache.return_value = None
        mock_get_durations.return_value = {"vid1": 600}

        run_subscriptions(
            days=7,
            include_keywords=[],
            exclude_keywords=[],
            model="claude-model",
            lang="en",
            api_key="test-key",
            dry_run=True,
            max_videos=50,
            exclude_channels=["FantasyLofi"],
        )

        assert 'exclude channel "FantasyLofi" not found in subscriptions' in caplog.text

    @patch("yt_summary.subscriptions.get_oauth_dir")
    @patch("yt_summary.subscriptions.get_credentials")
    @patch("yt_summary.subscriptions.get_subscribed_channels")
    @patch("yt_summary.subscriptions.get_recent_videos")
    @patch("yt_summary.subscriptions.load_cache")
    @patch("yt_summary.subscriptions.get_video_durations")
    def test_exclude_channels_empty_by_default(
        self,
        mock_get_durations,
        mock_load_cache,
        mock_get_videos,
        mock_get_channels,
        mock_get_creds,
        mock_oauth_dir,
    ) -> None:
        """Fetch all channels when exclude_channels is not passed."""
        mock_oauth_dir.return_value = "/fake/path"
        mock_get_creds.return_value = Mock()
        mock_get_channels.return_value = [
            {"channel_id": "UC123", "title": "Channel 1"},
            {"channel_id": "UC456", "title": "Channel 2"},
        ]

        now = datetime.now(timezone.utc)
        mock_get_videos.return_value = [
            {
                "video_id": "vid1",
                "title": "Video",
                "description": "",
                "published_at": now,
                "channel": "Channel 1",
            }
        ]
        mock_load_cache.return_value = None
        mock_get_durations.return_value = {"vid1": 600}

        run_subscriptions(
            days=7,
            include_keywords=[],
            exclude_keywords=[],
            model="claude-model",
            lang="en",
            api_key="test-key",
            dry_run=True,
            max_videos=50,
        )

        # Should call get_recent_videos twice (once for each channel)
        assert mock_get_videos.call_count == 2

    @patch("yt_summary.subscriptions.get_oauth_dir")
    @patch("yt_summary.subscriptions.get_credentials")
    @patch("yt_summary.subscriptions.get_subscribed_channels")
    @patch("yt_summary.subscriptions.get_recent_videos")
    @patch("yt_summary.subscriptions.load_cache")
    @patch("yt_summary.subscriptions.get_video_durations")
    def test_skips_shorts(
        self,
        mock_get_durations,
        mock_load_cache,
        mock_get_videos,
        mock_get_channels,
        mock_get_creds,
        mock_oauth_dir,
        caplog,
    ) -> None:
        """Filter out YouTube Shorts (<= 60s) and only process regular videos."""
        import logging

        caplog.set_level(logging.INFO)
        mock_oauth_dir.return_value = "/fake/path"
        mock_get_creds.return_value = Mock()
        mock_get_channels.return_value = [{"channel_id": "UC123", "title": "Channel"}]

        now = datetime.now(timezone.utc)
        short_video = {
            "video_id": "short1",
            "title": "Short Video",
            "description": "",
            "published_at": now,
            "channel": "Channel",
        }
        regular_video = {
            "video_id": "regular1",
            "title": "Regular Video",
            "description": "",
            "published_at": now,
            "channel": "Channel",
        }
        exactly_60_video = {
            "video_id": "exactly60",
            "title": "Exactly 60 Second Video",
            "description": "",
            "published_at": now,
            "channel": "Channel",
        }
        mock_get_videos.return_value = [short_video, regular_video, exactly_60_video]
        mock_load_cache.return_value = None
        # short1 is 45s (Short), regular1 is 600s (regular), exactly60 is 60s (Short boundary)
        mock_get_durations.return_value = {
            "short1": 45,
            "regular1": 600,
            "exactly60": 60,
        }

        result = run_subscriptions(
            days=7,
            include_keywords=[],
            exclude_keywords=[],
            model="claude-model",
            lang="en",
            api_key="test-key",
            dry_run=True,
            max_videos=50,
        )

        assert result == 0
        # Only the regular video (>60s) should remain
        assert "Filtered to 1 videos to process" in caplog.text
        # Both shorts should be logged as skipped
        assert "Skipping Short" in caplog.text
        assert "short1" in caplog.text or "Short Video" in caplog.text
        assert "Filtered 2 Shorts" in caplog.text
