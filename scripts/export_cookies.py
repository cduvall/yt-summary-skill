#!/usr/bin/env python3
"""Export YouTube and Google cookies from Comet browser to Netscape format.

Reads the Chromium cookie database, decrypts cookie values using the
encryption key from macOS Keychain, and writes a Netscape-format cookie file
suitable for yt-dlp and youtube-transcript-api.

Usage:
    python scripts/export_cookies.py                  # writes cookies.txt
    python scripts/export_cookies.py -o /tmp/out.txt  # custom output path
"""

import argparse
import hashlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

COOKIE_DB = Path.home() / "Library/Application Support/Comet/Default/Cookies"
KEYCHAIN_SERVICE = "Comet Safe Storage"
DOMAINS = (".youtube.com", ".google.com", "youtube.com", "google.com")

# Chromium KDF parameters for macOS
SALT = b"saltysalt"
ITERATIONS = 1003
KEY_LENGTH = 16
IV = b" " * 16  # 16 spaces


def get_encryption_key() -> bytes:
    """Retrieve the cookie encryption key from macOS Keychain."""
    result = subprocess.run(
        ["security", "find-generic-password", "-w", "-s", KEYCHAIN_SERVICE],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Error: Could not find '{KEYCHAIN_SERVICE}' in Keychain.", file=sys.stderr)
        sys.exit(1)
    password = result.stdout.strip().encode("utf-8")
    return hashlib.pbkdf2_hmac("sha1", password, SALT, ITERATIONS, dklen=KEY_LENGTH)


def get_meta_version(cursor: sqlite3.Cursor) -> int:
    """Get the cookie database meta version for hash_prefix detection."""
    try:
        cursor.execute("SELECT value FROM meta WHERE key = 'version'")
        row = cursor.fetchone()
        return int(row[0]) if row else 0
    except sqlite3.OperationalError:
        return 0


def decrypt_value(encrypted: bytes, key: bytes, *, hash_prefix: bool = False) -> str:
    """Decrypt a Chromium v10 AES-CBC encrypted cookie value.

    Args:
        encrypted: Raw encrypted value from the cookies table
        key: Derived AES key
        hash_prefix: If True, strip 32-byte SHA256 hash prefix after decryption
                     (Chromium meta_version >= 24)
    """
    if not encrypted:
        return ""

    if encrypted[:3] != b"v10":
        # Unencrypted (old format)
        return encrypted.decode("utf-8", errors="replace")

    # Strip "v10" prefix — the remaining bytes are AES-CBC ciphertext
    ciphertext = encrypted[3:]
    if not ciphertext:
        return ""

    cipher = Cipher(algorithms.AES(key), modes.CBC(IV), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(ciphertext) + decryptor.finalize()

    # Remove PKCS7 padding
    padding_len = decrypted[-1]
    if (
        isinstance(padding_len, int)
        and 1 <= padding_len <= 16
        and all(b == padding_len for b in decrypted[-padding_len:])
    ):
        decrypted = decrypted[:-padding_len]

    # Chromium meta_version >= 24 prepends a 32-byte SHA256 hash
    if hash_prefix:
        decrypted = decrypted[32:]

    return decrypted.decode("utf-8", errors="replace")


def export_cookies(output_path: str) -> None:
    """Export cookies to Netscape format file."""
    if not COOKIE_DB.exists():
        print(f"Error: Cookie database not found at {COOKIE_DB}", file=sys.stderr)
        sys.exit(1)

    key = get_encryption_key()

    # Copy DB to temp file (browser may have it locked)
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = tmp.name
    shutil.copy2(COOKIE_DB, tmp_path)

    try:
        conn = sqlite3.connect(tmp_path)
        cursor = conn.cursor()

        meta_version = get_meta_version(cursor)
        hash_prefix = meta_version >= 24

        # Build domain filter
        placeholders = ",".join("?" for _ in DOMAINS)
        query = f"""
            SELECT host_key, path, is_secure, expires_utc, name, encrypted_value, is_httponly
            FROM cookies
            WHERE host_key IN ({placeholders})
            ORDER BY host_key, name
        """
        cursor.execute(query, DOMAINS)
        rows = cursor.fetchall()

        # Also match subdomains
        subdomain_rows = []
        for domain in DOMAINS:
            if domain.startswith("."):
                cursor.execute(
                    "SELECT host_key, path, is_secure, expires_utc, name, encrypted_value, is_httponly "
                    "FROM cookies WHERE host_key LIKE ?",
                    (f"%{domain}",),
                )
                subdomain_rows.extend(cursor.fetchall())

        all_rows = list({(r[0], r[4]): r for r in rows + subdomain_rows}.values())
        conn.close()

        if not all_rows:
            print("Warning: No cookies found for YouTube/Google domains.", file=sys.stderr)

        with open(output_path, "w") as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.write("# https://curl.haxx.se/rfc/cookie_spec.html\n\n")

            for host, path, is_secure, expires, name, encrypted_value, is_httponly in all_rows:
                value = decrypt_value(encrypted_value, key, hash_prefix=hash_prefix)
                # Chromium stores expires_utc as microseconds since 1601-01-01
                # Convert to Unix epoch
                if expires:
                    unix_expires = int((expires / 1_000_000) - 11644473600)
                    if unix_expires < 0:
                        unix_expires = 0
                else:
                    unix_expires = 0

                secure = "TRUE" if is_secure else "FALSE"
                domain_flag = "TRUE" if host.startswith(".") else "FALSE"
                prefix = "#HttpOnly_" if is_httponly else ""
                f.write(
                    f"{prefix}{host}\t{domain_flag}\t{path}\t{secure}\t{unix_expires}\t{name}\t{value}\n"
                )

        print(f"Exported {len(all_rows)} cookies to {output_path}")

    finally:
        Path(tmp_path).unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export YouTube/Google cookies from Comet browser")
    parser.add_argument(
        "-o", "--output", default="cookies.txt", help="Output file path (default: cookies.txt)"
    )
    args = parser.parse_args()
    export_cookies(args.output)


if __name__ == "__main__":
    main()
