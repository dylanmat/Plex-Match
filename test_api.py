#!/usr/bin/env python3
"""Quick Plex GraphQL connectivity test.

Usage:
  python test_api.py --token YOUR_TOKEN
  PLEX_TOKEN=YOUR_TOKEN python test_api.py
"""

from __future__ import annotations

import argparse
import os
import sys

import httpx

API_URL = "https://community.plex.tv/api"
USERS_QUERY = "query Users { users { id title username friend } }"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test Plex GraphQL connectivity.")
    parser.add_argument("--token", default=os.getenv("PLEX_TOKEN", "").strip(), help="Plex token.")
    parser.add_argument("--url", default=API_URL, help="GraphQL API URL to test.")
    parser.add_argument("--timeout", type=float, default=15.0, help="Request timeout in seconds.")
    return parser.parse_args()


def header_variants(token: str) -> list[dict[str, str]]:
    base = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Plex-Product": "PlexMatch",
        "X-Plex-Version": "0.1.7",
        "X-Plex-Client-Identifier": "plexmatch-cli",
    }
    return [{**base, "X-Plex-Token": token}, {**base, "Authorization": f"Bearer {token}"}]


def main() -> int:
    args = parse_args()
    if not args.token:
        print("ERROR: Missing token. Pass --token or set PLEX_TOKEN.")
        return 2

    payload = {"query": USERS_QUERY, "variables": {}}
    print(f"Testing Plex GraphQL API: {args.url}")

    for idx, headers in enumerate(header_variants(args.token), start=1):
        auth_name = "X-Plex-Token" if "X-Plex-Token" in headers else "Authorization: Bearer"
        print(f"Attempt {idx}: auth via {auth_name}")
        try:
            response = httpx.post(args.url, json=payload, headers=headers, timeout=args.timeout)
        except httpx.HTTPError as exc:
            print(f"REQUEST FAILED: {exc}")
            continue

        print(f"HTTP {response.status_code}")
        if response.status_code == 401:
            print("Unauthorized, trying next auth header variant.")
            continue

        if not response.is_success:
            print(f"FAILURE: {response.text[:300]}")
            return 1

        data = response.json().get("data", {})
        users = data.get("users") or data.get("friends") or []
        print(f"SUCCESS: GraphQL request completed, users returned: {len(users)}")
        return 0

    print("FAILURE: All auth variants failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
