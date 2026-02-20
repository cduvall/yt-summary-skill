"""YouTube Data API v3 integration with OAuth2."""

import re
import stat
from datetime import datetime
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]


class YouTubeAPIError(Exception):
    """Exception raised when YouTube API operations fail."""

    pass


def get_credentials(oauth_dir: Path, on_token_refresh=None) -> Credentials:
    """
    Load OAuth credentials, refresh if expired, or run browser auth flow.

    Args:
        oauth_dir: Directory containing credentials.json and token.json
        on_token_refresh: Optional callback function(token_json: str) called after token refresh

    Returns:
        Valid OAuth2 credentials

    Raises:
        YouTubeAPIError: If credentials cannot be obtained
    """
    token_path = oauth_dir / "token.json"
    credentials_path = oauth_dir / "credentials.json"

    creds = None

    # Load existing token if available
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    # Refresh or authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                raise YouTubeAPIError(f"Failed to refresh OAuth token: {e}") from e
        else:
            # Need to run OAuth flow
            if not credentials_path.exists():
                raise YouTubeAPIError(
                    f"OAuth credentials not found at {credentials_path}\n"
                    "Please download credentials.json from Google Cloud Console:\n"
                    "1. Go to https://console.cloud.google.com/\n"
                    "2. Enable YouTube Data API v3\n"
                    "3. Create OAuth2 Desktop credentials\n"
                    "4. Download JSON and save to ~/.yt-summary/credentials.json"
                )

            try:
                flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                raise YouTubeAPIError(f"OAuth flow failed: {e}") from e

        # Save the credentials for next run
        oauth_dir.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json())
        # Set file permissions to 0600 (owner read/write only)
        token_path.chmod(stat.S_IRUSR | stat.S_IWUSR)

        # Call token refresh callback if provided
        if on_token_refresh is not None:
            on_token_refresh(creds.to_json())

    return creds


def get_subscribed_channels(credentials: Credentials) -> list[dict]:
    """
    Fetch all subscribed channels for the authenticated user.

    Args:
        credentials: Valid OAuth2 credentials

    Returns:
        List of dicts with keys: channel_id, title

    Raises:
        YouTubeAPIError: If API call fails
    """
    try:
        youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
        channels = []
        next_page_token = None

        while True:
            request = youtube.subscriptions().list(
                part="snippet",
                mine=True,
                maxResults=50,
                pageToken=next_page_token,
            )
            response = request.execute()

            for item in response.get("items", []):
                channels.append(
                    {
                        "channel_id": item["snippet"]["resourceId"]["channelId"],
                        "title": item["snippet"]["title"],
                    }
                )

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

        return channels

    except Exception as e:
        raise YouTubeAPIError(f"Failed to fetch subscriptions: {e}") from e


def get_recent_videos(credentials: Credentials, channel_id: str, since: datetime) -> list[dict]:
    """
    Fetch recent videos from a channel using the uploads playlist.

    Uses the uploads playlist trick: replace 'UC' prefix with 'UU' in channel_id.

    Args:
        credentials: Valid OAuth2 credentials
        channel_id: YouTube channel ID (starts with 'UC')
        since: Only return videos published after this datetime

    Returns:
        List of dicts with keys: video_id, title, description, published_at, channel

    Raises:
        YouTubeAPIError: If API call fails
    """
    try:
        # Convert channel ID to uploads playlist ID
        if channel_id.startswith("UC"):
            uploads_playlist_id = "UU" + channel_id[2:]
        else:
            # Some channels might not follow UC pattern, skip them
            return []

        youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
        videos: list[dict] = []
        next_page_token = None

        while True:
            request = youtube.playlistItems().list(
                part="snippet",
                playlistId=uploads_playlist_id,
                maxResults=50,
                pageToken=next_page_token,
            )
            response = request.execute()

            for item in response.get("items", []):
                published_at_str = item["snippet"]["publishedAt"]
                published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))

                # Stop if we've gone past the 'since' date
                if published_at < since:
                    return videos

                videos.append(
                    {
                        "video_id": item["snippet"]["resourceId"]["videoId"],
                        "title": item["snippet"]["title"],
                        "description": item["snippet"].get("description", ""),
                        "published_at": published_at,
                        "channel": item["snippet"]["channelTitle"],
                    }
                )

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

        return videos

    except Exception as e:
        raise YouTubeAPIError(f"Failed to fetch videos from channel {channel_id}: {e}") from e


def _parse_iso8601_duration(duration: str) -> int:
    """Parse an ISO 8601 duration string to total seconds.

    Args:
        duration: ISO 8601 duration string (e.g. 'PT1H2M3S', 'PT45S', 'PT1M')

    Returns:
        Total duration in seconds
    """
    match = re.fullmatch(
        r"P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",
        duration,
    )
    if not match:
        return 0
    days, hours, minutes, seconds = (int(g) if g else 0 for g in match.groups())
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def get_video_durations(credentials: Credentials, video_ids: list[str]) -> dict[str, int]:
    """Batch-fetch video durations via the YouTube Data API.

    Processes video IDs in pages of 50 (API limit per request).

    Args:
        credentials: Valid OAuth2 credentials
        video_ids: List of YouTube video IDs

    Returns:
        Mapping of video_id to duration in seconds

    Raises:
        YouTubeAPIError: If the API call fails
    """
    if not video_ids:
        return {}

    try:
        youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
        durations: dict[str, int] = {}
        page_size = 50

        for i in range(0, len(video_ids), page_size):
            batch = video_ids[i : i + page_size]
            request = youtube.videos().list(
                part="contentDetails",
                id=",".join(batch),
            )
            response = request.execute()

            for item in response.get("items", []):
                video_id = item["id"]
                content_details = item.get("contentDetails")
                if not content_details or "duration" not in content_details:
                    continue
                durations[video_id] = _parse_iso8601_duration(content_details["duration"])

        return durations

    except Exception as e:
        raise YouTubeAPIError(f"Failed to fetch video durations: {e}") from e
