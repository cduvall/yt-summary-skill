"""Video filtering using keyword-based criteria."""

import re


def keyword_filter(
    videos: list[dict],
    include_keywords: list[str],
    exclude_keywords: list[str],
) -> tuple[list[dict], dict[str, str]]:
    """
    Filter videos by keyword matching on title.

    Args:
        videos: List of video dicts with 'title' key
        include_keywords: Videos must match at least one (case-insensitive). Empty = include all.
        exclude_keywords: Videos must match none (case-insensitive)

    Returns:
        Tuple of (filtered list of videos, dict mapping video_id (or title) to removal reason)
    """
    filtered = []
    reasons: dict[str, str] = {}

    for video in videos:
        text = video.get("title", "")
        key = video.get("video_id") or video.get("title", "")

        # Exclude filter: must match none
        if exclude_keywords:
            matched_exclude = next(
                (
                    kw
                    for kw in exclude_keywords
                    if re.search(r"\b" + re.escape(kw) + r"\b", text, re.IGNORECASE)
                ),
                None,
            )
            if matched_exclude is not None:
                reasons[key] = f"matched exclude keyword: {matched_exclude}"
                continue

        # Include filter: must match at least one (if list is not empty)
        if include_keywords:
            matched_include = next(
                (
                    kw
                    for kw in include_keywords
                    if re.search(r"\b" + re.escape(kw) + r"\b", text, re.IGNORECASE)
                ),
                None,
            )
            if matched_include is None:
                reasons[key] = "no include keyword matched"
                continue

        filtered.append(video)

    return filtered, reasons
