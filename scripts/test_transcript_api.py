#!/usr/bin/env python3
"""
Simple integration test for youtube-transcript-api.
Tests transcript fetching in isolation from the rest of the application.
"""

import sys

from youtube_transcript_api import YouTubeTranscriptApi


def test_transcript(video_id: str = "y6YTk0C5pBY") -> None:
    """
    Fetch and print transcript for a YouTube video.

    Args:
        video_id: YouTube video ID to test
    """
    print(f"\n{'='*70}")
    print(f"Testing youtube-transcript-api with video ID: {video_id}")
    print(f"{'='*70}\n")

    try:
        # Step 1: Fetch the transcript for the given video_id
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id)

        # Step 2: Reconstruct the full transcript as a single string, then print line by line
        for entry in transcript:
            print(entry)
            # text_line = entry.get("text", "")
            # print(text_line)
            # full_text += text_line + "\n"

        return

    except Exception as e:
        print(f"✗ Error: {type(e).__name__}")
        print(f"  Message: {e}\n")
        print(f"{'-'*70}")
        print("Full traceback:")
        print(f"{'-'*70}")
        import traceback

        traceback.print_exc()
        print(f"{'='*70}\n")
        sys.exit(1)


if __name__ == "__main__":
    # Use command line argument if provided, otherwise use default
    video_id = sys.argv[1] if len(sys.argv) > 1 else "y6YTk0C5pBY"
    test_transcript(video_id)
