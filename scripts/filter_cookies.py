#!/usr/bin/env python3
"""Filter a Netscape cookie file to only YouTube/Google auth cookies.

Keeps only the cookies yt-dlp needs for authenticated YouTube access,
stripping everything else (banking, shopping, etc.).

Usage:
    python scripts/filter_cookies.py INPUT_FILE [OUTPUT_FILE]

If OUTPUT_FILE is omitted, writes to INPUT_FILE with .youtube.txt suffix.
"""

import sys
from pathlib import Path

# Domains yt-dlp needs for YouTube authentication
YOUTUBE_DOMAINS = {
    ".youtube.com",
    "youtube.com",
    ".google.com",
    "google.com",
    ".googleapis.com",
    "googleapis.com",
    "accounts.google.com",
    "www.youtube.com",
}

# Cookie names that matter for YouTube auth
# If empty, keep all cookies from matching domains
YOUTUBE_COOKIE_NAMES = {
    "SID",
    "HSID",
    "SSID",
    "APISID",
    "SAPISID",
    "__Secure-1PSID",
    "__Secure-3PSID",
    "__Secure-1PAPISID",
    "__Secure-3PAPISID",
    "__Secure-1PSIDTS",
    "__Secure-3PSIDTS",
    "__Secure-1PSIDCC",
    "__Secure-3PSIDCC",
    "LOGIN_INFO",
    "PREF",
    "YSC",
    "VISITOR_INFO1_LIVE",
    "VISITOR_PRIVACY_METADATA",
    "GPS",
    "NID",
    "CONSENT",
    "SOCS",
}


def filter_cookies(input_path: str, output_path: str | None = None) -> None:
    input_file = Path(input_path)
    if not input_file.exists():
        print(f"Error: {input_file} not found", file=sys.stderr)
        sys.exit(1)

    if output_path is None:
        output_file = input_file.with_suffix(".youtube.txt")
    else:
        output_file = Path(output_path)

    kept = 0
    total = 0
    lines_out = ["# Netscape HTTP Cookie File\n"]

    with open(input_file) as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            # Skip comments but NOT #HttpOnly_ lines (Netscape cookie format)
            if stripped.startswith("#") and not stripped.startswith("#HttpOnly_"):
                continue

            total += 1
            parts = stripped.split("\t")
            if len(parts) < 7:
                continue

            domain = parts[0].removeprefix("#HttpOnly_")
            cookie_name = parts[5]

            # Match domain
            domain_match = any(domain == d or domain.endswith(d) for d in YOUTUBE_DOMAINS)
            if not domain_match:
                continue

            # Match cookie name (if whitelist is set)
            if YOUTUBE_COOKIE_NAMES and cookie_name not in YOUTUBE_COOKIE_NAMES:
                continue

            lines_out.append(line if line.endswith("\n") else line + "\n")
            kept += 1

    output_file.write_text("".join(lines_out))
    print(f"Filtered {total} cookies -> {kept} YouTube auth cookies")
    print(f"Written to: {output_file}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} INPUT_FILE [OUTPUT_FILE]", file=sys.stderr)
        sys.exit(1)

    filter_cookies(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
