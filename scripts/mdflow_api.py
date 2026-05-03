"""mdFlow REST API CLI.

Provides five commands that map to mdFlow v1 REST endpoints.
All commands print JSON to stdout; errors go to stderr; exit 1 on failure.

API key discovery order:
  1. MDFLOW_API_KEY env var (already set in the environment)
  2. ~/.claude/skills/yt-summary-mdflow/.env
  3. .env in the current working directory

Usage:
  mdflow_api.py search <query> [--include-body]
  mdflow_api.py get <id>
  mdflow_api.py list-children <parent_id>
  mdflow_api.py update <id>          (reads JSON payload from stdin)
  mdflow_api.py bulk-create          (reads JSON payload from stdin)
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Load .env files so MDFLOW_API_KEY is available if not already in env
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv

    # Load in descending priority order (highest first).
    # override=False means the first file to define a variable wins;
    # a variable already in the environment is never overwritten.
    # Priority: env var (already set) > skill .env > cwd .env

    _skill_env = Path.home() / ".claude" / "skills" / "yt-summary-mdflow" / ".env"
    if _skill_env.exists():
        load_dotenv(_skill_env, override=False)

    _cwd_env = Path.cwd() / ".env"
    if _cwd_env.exists():
        load_dotenv(_cwd_env, override=False)

except ImportError:
    # python-dotenv not available; rely on the environment directly
    pass

BASE_URL = "https://app.mdflow.xyz/v1"


def _api_key() -> str:
    key = os.getenv("MDFLOW_API_KEY", "")
    if not key:
        print(
            "ERROR: MDFLOW_API_KEY is not set. "
            "Set it in the environment or in ~/.claude/skills/yt-summary-mdflow/.env",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def _stream_id() -> str | None:
    """Return MDFLOW_STREAM_ID if set; None otherwise."""
    return os.getenv("MDFLOW_STREAM_ID") or None


def _request(method: str, path: str, body: bytes | None = None) -> dict:
    """Make an authenticated HTTP request and return the parsed JSON response."""
    url = BASE_URL + path
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    }
    stream = _stream_id()
    if stream:
        headers["X-Stream-ID"] = stream
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode(errors="replace")
        print(
            f"ERROR: HTTP {exc.code} {exc.reason} — {error_body}",
            file=sys.stderr,
        )
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"ERROR: {exc.reason}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_search(args: list[str]) -> None:
    """GET /search?q=<query>[&include_body=true]"""
    import argparse

    parser = argparse.ArgumentParser(prog="mdflow_api.py search")
    parser.add_argument("query", help="Search query string")
    parser.add_argument(
        "--include-body",
        action="store_true",
        help="Include item body in results",
    )
    parsed = parser.parse_args(args)

    params: dict[str, str] = {"q": parsed.query}
    if parsed.include_body:
        params["include_body"] = "true"

    qs = urllib.parse.urlencode(params)
    result = _request("GET", f"/search?{qs}")
    print(json.dumps(result))


def cmd_get(args: list[str]) -> None:
    """GET /items/<id>"""
    if not args:
        print("ERROR: 'get' requires an item id argument", file=sys.stderr)
        sys.exit(1)
    item_id = args[0]
    result = _request("GET", f"/items/{urllib.parse.quote(item_id, safe='')}")
    print(json.dumps(result))


def cmd_list_children(args: list[str]) -> None:
    """GET /items?parent=<parent_id>&limit=200"""
    if not args:
        print("ERROR: 'list-children' requires a parent_id argument", file=sys.stderr)
        sys.exit(1)
    parent_id = args[0]
    qs = urllib.parse.urlencode({"parent": parent_id, "limit": "200"})
    result = _request("GET", f"/items?{qs}")
    print(json.dumps(result))


def cmd_update(args: list[str]) -> None:
    """PATCH /items/<id>  (reads JSON payload from stdin)"""
    if not args:
        print("ERROR: 'update' requires an item id argument", file=sys.stderr)
        sys.exit(1)
    item_id = args[0]
    payload_raw = sys.stdin.read()
    try:
        payload = json.loads(payload_raw)
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON on stdin: {exc}", file=sys.stderr)
        sys.exit(1)
    body = json.dumps(payload).encode()
    result = _request("PATCH", f"/items/{urllib.parse.quote(item_id, safe='')}", body)
    print(json.dumps(result))


def cmd_bulk_create(args: list[str]) -> None:
    """POST /items/bulk  (reads JSON payload from stdin; must have "items" key)"""
    payload_raw = sys.stdin.read()
    try:
        payload = json.loads(payload_raw)
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON on stdin: {exc}", file=sys.stderr)
        sys.exit(1)
    if "items" not in payload:
        print('ERROR: JSON payload must contain an "items" key', file=sys.stderr)
        sys.exit(1)
    body = json.dumps(payload).encode()
    result = _request("POST", "/items/bulk", body)
    print(json.dumps(result))


COMMANDS = {
    "search": cmd_search,
    "get": cmd_get,
    "list-children": cmd_list_children,
    "update": cmd_update,
    "bulk-create": cmd_bulk_create,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        valid = ", ".join(sorted(COMMANDS))
        print(f"Usage: mdflow_api.py <command> [args]\nCommands: {valid}", file=sys.stderr)
        sys.exit(1)
    command = sys.argv[1]
    COMMANDS[command](sys.argv[2:])


if __name__ == "__main__":
    main()
