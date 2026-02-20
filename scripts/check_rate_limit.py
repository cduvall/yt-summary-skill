#!/usr/bin/env python3
"""Check YouTube rate limit headers."""

import requests
from youtube_transcript_api import YouTubeTranscriptApi

video_id = "y6YTk0C5pBY"

try:
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    first_transcript = next(iter(transcript_list))

    # Try to fetch and catch the response
    print(f"Attempting to fetch transcript for {video_id}...")
    transcript_data = first_transcript.fetch()

except Exception as e:
    print(f"Error: {e}")
    print("\nLooking for rate limit headers...")

    # Try to get headers from the actual request
    try:
        # Get the source of the fetch method to understand how requests are made
        response = requests.get(
            f"https://www.youtube.com/api/timedtext?v={video_id}&caps=asr&lang=en",
            headers={"User-Agent": "Mozilla/5.0"},
        )

        print(f"Status Code: {response.status_code}")
        print("\nResponse Headers:")
        for key, value in response.headers.items():
            if "retry" in key.lower() or "rate" in key.lower() or "limit" in key.lower():
                print(f"  {key}: {value}")

        # Check for Retry-After header
        if "Retry-After" in response.headers:
            retry_after = response.headers["Retry-After"]
            print(f"\n⏱️  Retry-After: {retry_after} seconds")
        else:
            print("\nNo Retry-After header found")
            print("You may need to wait 60-300 seconds before trying again")

    except Exception as e2:
        print(f"Could not check headers: {e2}")
