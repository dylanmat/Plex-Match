#!/usr/bin/env python3
"""Quick connectivity test for Plex community API.

Usage:
  python test_api.py --token YOUR_TOKEN
  PLEX_TOKEN=YOUR_TOKEN python test_api.py
"""

from __future__ import annotations

import argparse
import os
import sys

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test Plex API connectivity.")
    parser.add_argument(
        "--token",
        default=os.getenv("PLEX_TOKEN", "").strip(),
        help="Plex token (defaults to PLEX_TOKEN environment variable).",
    )
    parser.add_argument(
        "--url",
        default="https://community.plex.tv/api",
        help="API URL to test.",
    )
    parser.add_argument("--timeout", type=float, default=15.0, help="Request timeout in seconds.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.token:
        print("ERROR: Missing token. Pass --token or set PLEX_TOKEN.")
        return 2

    headers = {"X-Plex-Token": args.token, "Accept": "application/json"}
    print(f"Testing Plex API: {args.url}")
    print(f"Using timeout: {args.timeout:.1f}s")

    try:
        response = httpx.get(args.url, headers=headers, timeout=args.timeout)
    except httpx.HTTPError as exc:
        print(f"REQUEST FAILED: {exc}")
        return 1

    print(f"HTTP {response.status_code}")
    content_type = response.headers.get("content-type", "unknown")
    print(f"Content-Type: {content_type}")

    if response.is_success:
        preview = response.text[:300].replace("\n", " ").strip()
        print("SUCCESS: API request completed.")
        if preview:
            print(f"Body preview: {preview}")
        return 0

    print("FAILURE: API request returned a non-success status.")
    print(f"Response body (first 300 chars): {response.text[:300]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
