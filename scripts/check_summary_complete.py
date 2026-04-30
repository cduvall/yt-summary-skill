"""Check whether a summary body contains all four required sections with content.

CLI: python scripts/check_summary_complete.py < summary_body.txt

Exit codes:
    0 - summary is complete (all four sections present, in order, with content)
    1 - summary is incomplete (prints reason to stderr)
"""

import sys

REQUIRED_HEADINGS = [
    "## Title Evaluation",
    "## Summary",
    "## Top Takeaways",
    "## Protocols & Instructions",
]


def _skip_frontmatter(lines: list[str]) -> list[str]:
    """Return lines with YAML frontmatter removed if present."""
    if not lines or lines[0].rstrip() != "---":
        return lines
    # Find closing ---
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            return lines[i + 1 :]
    # No closing --- found; treat entire body as content
    return lines


def check_complete(body: str) -> tuple[bool, str]:
    """Check whether the body contains all required sections in order with content.

    Returns:
        (True, "") if complete.
        (False, reason) if incomplete.
    """
    lines = body.splitlines()
    lines = _skip_frontmatter(lines)

    heading_indices: dict[str, int] = {}
    for i, raw_line in enumerate(lines):
        line = raw_line.rstrip()
        if line in REQUIRED_HEADINGS and line not in heading_indices:
            heading_indices[line] = i

    # Check all headings are present
    for heading in REQUIRED_HEADINGS:
        if heading not in heading_indices:
            return False, f"missing heading: {heading}"

    # Check headings appear in order
    positions = [heading_indices[h] for h in REQUIRED_HEADINGS]
    if positions != sorted(positions):
        return False, "headings out of order"

    # Check each section has non-empty content
    for idx, heading in enumerate(REQUIRED_HEADINGS):
        start = heading_indices[heading] + 1  # line after the heading

        # End is the line of the next required heading, or EOF
        if idx + 1 < len(REQUIRED_HEADINGS):
            end = heading_indices[REQUIRED_HEADINGS[idx + 1]]
        else:
            end = len(lines)

        section_lines = lines[start:end]
        has_content = any(
            ln.strip()
            and not ln.rstrip().startswith("#")
            and ln.strip() not in ("-", "*", "+", "•")
            for ln in section_lines
        )
        if not has_content:
            return False, f"empty section: {heading}"

    return True, ""


def main() -> None:
    body = sys.stdin.read()
    complete, reason = check_complete(body)
    if complete:
        sys.exit(0)
    else:
        print(reason, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
