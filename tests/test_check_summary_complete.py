"""Tests for scripts/check_summary_complete.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from check_summary_complete import check_complete  # noqa: E402

COMPLETE_BODY = """\
## Title Evaluation
The title accurately reflects the content.

## Summary
A concise summary of the video.

## Top Takeaways
- Key point one
- Key point two

## Protocols & Instructions
1. Step one
2. Step two
"""

FRONTMATTER_BODY = """\
---
video_id: abc123
title: Test Video
---
## Title Evaluation
The title accurately reflects the content.

## Summary
A concise summary of the video.

## Top Takeaways
- Key point one

## Protocols & Instructions
None mentioned.
"""


class TestCheckComplete:
    def test_complete_body(self) -> None:
        """A body with all four sections and content is complete."""
        ok, reason = check_complete(COMPLETE_BODY)
        assert ok is True
        assert reason == ""

    def test_complete_with_frontmatter(self) -> None:
        """Frontmatter is skipped; headings after it are found."""
        ok, reason = check_complete(FRONTMATTER_BODY)
        assert ok is True
        assert reason == ""

    def test_missing_heading(self) -> None:
        """A body missing one required heading is incomplete."""
        body = """\
## Summary
Some summary text.

## Top Takeaways
- Point one

## Protocols & Instructions
None mentioned.
"""
        ok, reason = check_complete(body)
        assert ok is False
        assert "missing heading" in reason
        assert "## Title Evaluation" in reason

    def test_empty_section(self) -> None:
        """A section with no non-blank, non-heading content is incomplete."""
        body = """\
## Title Evaluation
## Summary
Some summary text.

## Top Takeaways
- Point one

## Protocols & Instructions
None mentioned.
"""
        ok, reason = check_complete(body)
        assert ok is False
        assert "empty section" in reason
        assert "## Title Evaluation" in reason

    def test_out_of_order(self) -> None:
        """Headings present but in wrong order is incomplete."""
        body = """\
## Summary
Some text.

## Title Evaluation
Eval text.

## Top Takeaways
- Point.

## Protocols & Instructions
None mentioned.
"""
        ok, reason = check_complete(body)
        assert ok is False
        assert "out of order" in reason

    def test_empty_bullet_is_not_content(self) -> None:
        """A section with only an empty bullet line has no real content."""
        body = """\
## Title Evaluation
Eval text.

## Summary
Summary text.

## Top Takeaways
-

## Protocols & Instructions
None mentioned.
"""
        ok, reason = check_complete(body)
        assert ok is False
        assert "empty section" in reason
        assert "## Top Takeaways" in reason
