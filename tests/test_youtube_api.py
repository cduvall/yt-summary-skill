"""Tests for YouTube Data API integration."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from yt_summary.youtube_api import (
    YouTubeAPIError,
    _parse_iso8601_duration,
    get_credentials,
    get_recent_videos,
    get_subscribed_channels,
    get_video_durations,
)


class TestGetCredentials:
    """Test OAuth credential management."""

    @patch("yt_summary.youtube_api.Credentials")
    def test_loads_valid_existing_token(self, mock_creds_cls, tmp_path: Path) -> None:
        """Load valid token from existing token.json."""
        token_path = tmp_path / "token.json"
        token_path.write_text('{"token": "test"}')

        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds_cls.from_authorized_user_file.return_value = mock_creds

        result = get_credentials(tmp_path)

        assert result == mock_creds
        mock_creds_cls.from_authorized_user_file.assert_called_once()

    @patch("yt_summary.youtube_api.Request")
    @patch("yt_summary.youtube_api.Credentials")
    def test_refreshes_expired_token(
        self, mock_creds_cls, mock_request_cls, tmp_path: Path
    ) -> None:
        """Refresh expired token with valid refresh token."""
        token_path = tmp_path / "token.json"
        token_path.write_text('{"token": "test"}')

        mock_creds = Mock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh-token"
        mock_creds.to_json.return_value = '{"refreshed": true}'
        mock_creds_cls.from_authorized_user_file.return_value = mock_creds

        # After refresh, mark as valid
        def refresh_side_effect(request):
            mock_creds.valid = True

        mock_creds.refresh.side_effect = refresh_side_effect

        result = get_credentials(tmp_path)

        assert result == mock_creds
        mock_creds.refresh.assert_called_once()
        # Should save refreshed token
        assert token_path.read_text() == '{"refreshed": true}'

    @patch("yt_summary.youtube_api.Credentials")
    def test_refresh_token_failure(self, mock_creds_cls, tmp_path: Path) -> None:
        """Raise error when token refresh fails."""
        token_path = tmp_path / "token.json"
        token_path.write_text('{"token": "test"}')

        mock_creds = Mock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh-token"
        mock_creds.refresh.side_effect = Exception("Refresh failed")
        mock_creds_cls.from_authorized_user_file.return_value = mock_creds

        with pytest.raises(YouTubeAPIError, match="Failed to refresh OAuth token"):
            get_credentials(tmp_path)

    @patch("yt_summary.youtube_api.InstalledAppFlow")
    @patch("yt_summary.youtube_api.Credentials")
    def test_runs_oauth_flow_for_new_user(
        self, mock_creds_cls, mock_flow_cls, tmp_path: Path
    ) -> None:
        """Run browser OAuth flow when no token exists."""
        import stat

        credentials_path = tmp_path / "credentials.json"
        credentials_path.write_text('{"client_secret": "test"}')

        mock_creds_cls.from_authorized_user_file.side_effect = FileNotFoundError

        mock_creds = Mock()
        mock_creds.to_json.return_value = '{"new_token": true}'

        mock_flow = Mock()
        mock_flow.run_local_server.return_value = mock_creds
        mock_flow_cls.from_client_secrets_file.return_value = mock_flow

        result = get_credentials(tmp_path)

        assert result == mock_creds
        mock_flow.run_local_server.assert_called_once()
        # Should save new token
        token_path = tmp_path / "token.json"
        assert token_path.exists()
        assert token_path.read_text() == '{"new_token": true}'
        # Should set restrictive permissions (0600)
        mode = token_path.stat().st_mode
        assert mode & stat.S_IRUSR  # Owner can read
        assert mode & stat.S_IWUSR  # Owner can write
        assert not (mode & stat.S_IRGRP)  # Group cannot read
        assert not (mode & stat.S_IROTH)  # Others cannot read

    def test_missing_credentials_file(self, tmp_path: Path) -> None:
        """Raise error when credentials.json is missing."""
        with pytest.raises(YouTubeAPIError, match="OAuth credentials not found"):
            get_credentials(tmp_path)

    @patch("yt_summary.youtube_api.InstalledAppFlow")
    @patch("yt_summary.youtube_api.Credentials")
    def test_oauth_flow_failure(self, mock_creds_cls, mock_flow_cls, tmp_path: Path) -> None:
        """Raise error when OAuth flow fails."""
        credentials_path = tmp_path / "credentials.json"
        credentials_path.write_text('{"client_secret": "test"}')

        mock_creds_cls.from_authorized_user_file.side_effect = FileNotFoundError
        mock_flow_cls.from_client_secrets_file.side_effect = Exception("Flow failed")

        with pytest.raises(YouTubeAPIError, match="OAuth flow failed"):
            get_credentials(tmp_path)


class TestGetSubscribedChannels:
    """Test fetching subscribed channels."""

    @patch("yt_summary.youtube_api.build")
    def test_fetches_single_page(self, mock_build) -> None:
        """Fetch subscriptions with single page of results."""
        mock_youtube = MagicMock()
        mock_build.return_value = mock_youtube

        mock_youtube.subscriptions().list().execute.return_value = {
            "items": [
                {
                    "snippet": {
                        "resourceId": {"channelId": "UC123"},
                        "title": "Tech Channel",
                    }
                },
                {
                    "snippet": {
                        "resourceId": {"channelId": "UC456"},
                        "title": "Science Channel",
                    }
                },
            ]
        }

        mock_creds = Mock()
        result = get_subscribed_channels(mock_creds)

        assert len(result) == 2
        assert result[0] == {"channel_id": "UC123", "title": "Tech Channel"}
        assert result[1] == {"channel_id": "UC456", "title": "Science Channel"}

    @patch("yt_summary.youtube_api.build")
    def test_fetches_multiple_pages(self, mock_build) -> None:
        """Fetch subscriptions with pagination."""
        mock_youtube = MagicMock()
        mock_build.return_value = mock_youtube

        # Simulate two pages
        page1 = {
            "items": [
                {
                    "snippet": {
                        "resourceId": {"channelId": "UC1"},
                        "title": "Channel 1",
                    }
                }
            ],
            "nextPageToken": "token123",
        }

        page2 = {
            "items": [
                {
                    "snippet": {
                        "resourceId": {"channelId": "UC2"},
                        "title": "Channel 2",
                    }
                }
            ]
        }

        mock_youtube.subscriptions().list().execute.side_effect = [page1, page2]

        mock_creds = Mock()
        result = get_subscribed_channels(mock_creds)

        assert len(result) == 2
        assert result[0]["channel_id"] == "UC1"
        assert result[1]["channel_id"] == "UC2"

    @patch("yt_summary.youtube_api.build")
    def test_api_error(self, mock_build) -> None:
        """Raise error when API call fails."""
        mock_build.side_effect = Exception("API error")

        mock_creds = Mock()
        with pytest.raises(YouTubeAPIError, match="Failed to fetch subscriptions"):
            get_subscribed_channels(mock_creds)


class TestGetRecentVideos:
    """Test fetching recent videos from a channel."""

    @patch("yt_summary.youtube_api.build")
    def test_fetches_recent_videos(self, mock_build) -> None:
        """Fetch videos newer than since date."""
        mock_youtube = MagicMock()
        mock_build.return_value = mock_youtube

        now = datetime.now(timezone.utc)
        since = now - timedelta(days=7)

        mock_youtube.playlistItems().list().execute.return_value = {
            "items": [
                {
                    "snippet": {
                        "resourceId": {"videoId": "vid123"},
                        "title": "Recent Video",
                        "description": "Test description",
                        "publishedAt": now.isoformat().replace("+00:00", "Z"),
                        "channelTitle": "Test Channel",
                    }
                }
            ]
        }

        mock_creds = Mock()
        result = get_recent_videos(mock_creds, "UC123", since)

        assert len(result) == 1
        assert result[0]["video_id"] == "vid123"
        assert result[0]["title"] == "Recent Video"
        assert result[0]["channel"] == "Test Channel"

    @patch("yt_summary.youtube_api.build")
    def test_stops_at_since_date(self, mock_build) -> None:
        """Stop fetching when videos are older than since date."""
        mock_youtube = MagicMock()
        mock_build.return_value = mock_youtube

        now = datetime.now(timezone.utc)
        since = now - timedelta(days=7)
        old_date = now - timedelta(days=10)

        mock_youtube.playlistItems().list().execute.return_value = {
            "items": [
                {
                    "snippet": {
                        "resourceId": {"videoId": "old123"},
                        "title": "Old Video",
                        "description": "",
                        "publishedAt": old_date.isoformat().replace("+00:00", "Z"),
                        "channelTitle": "Test Channel",
                    }
                }
            ]
        }

        mock_creds = Mock()
        result = get_recent_videos(mock_creds, "UC123", since)

        assert len(result) == 0

    @patch("yt_summary.youtube_api.build")
    def test_skips_non_uc_channels(self, mock_build) -> None:
        """Return empty list for channels not starting with UC."""
        mock_creds = Mock()
        result = get_recent_videos(mock_creds, "HC123", datetime.now(timezone.utc))

        assert len(result) == 0
        mock_build.assert_not_called()

    @patch("yt_summary.youtube_api.build")
    def test_converts_uc_to_uu(self, mock_build) -> None:
        """Convert UC channel ID to UU uploads playlist ID."""
        mock_youtube = MagicMock()
        mock_build.return_value = mock_youtube

        mock_youtube.playlistItems().list().execute.return_value = {"items": []}

        mock_creds = Mock()
        get_recent_videos(mock_creds, "UCabcdef", datetime.now(timezone.utc))

        # Check that playlistId was converted from UC to UU
        call_kwargs = mock_youtube.playlistItems().list.call_args[1]
        assert call_kwargs["playlistId"] == "UUabcdef"

    @patch("yt_summary.youtube_api.build")
    def test_api_error(self, mock_build) -> None:
        """Raise error when API call fails."""
        mock_build.side_effect = Exception("API error")

        mock_creds = Mock()
        with pytest.raises(YouTubeAPIError, match="Failed to fetch videos"):
            get_recent_videos(mock_creds, "UC123", datetime.now(timezone.utc))


class TestParseISO8601Duration:
    """Test ISO 8601 duration string parsing."""

    def test_hours_minutes_seconds(self) -> None:
        """Parse combined hours, minutes, and seconds."""
        assert _parse_iso8601_duration("PT1H2M3S") == 3723

    def test_seconds_only(self) -> None:
        """Parse duration with seconds only."""
        assert _parse_iso8601_duration("PT45S") == 45

    def test_minutes_only(self) -> None:
        """Parse duration with minutes only."""
        assert _parse_iso8601_duration("PT1M") == 60

    def test_zero_duration(self) -> None:
        """Parse zero-length duration."""
        assert _parse_iso8601_duration("PT0S") == 0

    def test_minutes_and_seconds(self) -> None:
        """Parse combined minutes and seconds."""
        assert _parse_iso8601_duration("PT10M30S") == 630

    def test_invalid_format_returns_zero(self) -> None:
        """Return 0 for strings that do not match ISO 8601 duration format."""
        assert _parse_iso8601_duration("invalid") == 0

    def test_empty_string_returns_zero(self) -> None:
        """Return 0 for empty string."""
        assert _parse_iso8601_duration("") == 0


class TestGetVideoDurations:
    """Test batch video duration fetching."""

    @patch("yt_summary.youtube_api.build")
    def test_single_page(self, mock_build) -> None:
        """Return correct video_id-to-seconds mapping for a single API page."""
        mock_youtube = MagicMock()
        mock_build.return_value = mock_youtube

        mock_youtube.videos().list().execute.return_value = {
            "items": [
                {"id": "vid1", "contentDetails": {"duration": "PT10M"}},
                {"id": "vid2", "contentDetails": {"duration": "PT1H2M3S"}},
            ]
        }

        mock_creds = Mock()
        result = get_video_durations(mock_creds, ["vid1", "vid2"])

        assert result == {"vid1": 600, "vid2": 3723}

    @patch("yt_summary.youtube_api.build")
    def test_pagination_more_than_50_ids(self, mock_build) -> None:
        """Make multiple API calls when video_ids exceeds the 50-item page size."""
        mock_youtube = MagicMock()
        mock_build.return_value = mock_youtube

        # Build 60 video IDs: vid0 through vid59
        video_ids = [f"vid{i}" for i in range(60)]

        # First page (ids 0-49): return 50 items all with PT10M
        page1_items = [
            {"id": f"vid{i}", "contentDetails": {"duration": "PT10M"}} for i in range(50)
        ]
        # Second page (ids 50-59): return 10 items all with PT30S
        page2_items = [
            {"id": f"vid{i}", "contentDetails": {"duration": "PT30S"}} for i in range(50, 60)
        ]

        mock_youtube.videos().list().execute.side_effect = [
            {"items": page1_items},
            {"items": page2_items},
        ]

        mock_creds = Mock()
        result = get_video_durations(mock_creds, video_ids)

        # Should have made exactly 2 API calls (one per page)
        assert mock_youtube.videos().list().execute.call_count == 2
        assert len(result) == 60
        assert result["vid0"] == 600
        assert result["vid59"] == 30

    @patch("yt_summary.youtube_api.build")
    def test_api_error_raises_youtube_api_error(self, mock_build) -> None:
        """Raise YouTubeAPIError when the API call fails."""
        mock_build.side_effect = Exception("quota exceeded")

        mock_creds = Mock()
        with pytest.raises(YouTubeAPIError, match="Failed to fetch video durations"):
            get_video_durations(mock_creds, ["vid1"])

    @patch("yt_summary.youtube_api.build")
    def test_empty_input_returns_empty_dict(self, mock_build) -> None:
        """Return empty dict without making any API call for empty input."""
        mock_creds = Mock()
        result = get_video_durations(mock_creds, [])

        assert result == {}
        mock_build.assert_not_called()
