"""Thin GitHub GraphQL client built on httpx.

Pulls a token from the `gh` CLI (or GITHUB_TOKEN env var) and runs GraphQL
queries against the GitHub API, handling pagination for us.
"""

from __future__ import annotations

import os
import subprocess
import time
from typing import Any

import httpx

GRAPHQL_URL = "https://api.github.com/graphql"


def get_token() -> str:
    """Return a GitHub token from GITHUB_TOKEN or the `gh` CLI."""
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    result = subprocess.run(
        ["gh", "auth", "token"], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


class GitHubClient:
    """Run GraphQL queries against GitHub with retry + rate-limit awareness."""

    def __init__(self, token: str | None = None) -> None:
        self._token = token or get_token()
        self._client = httpx.Client(
            base_url="https://api.github.com",
            headers={"Authorization": f"bearer {self._token}"},
            timeout=30.0,
        )

    def query(self, query: str, variables: dict[str, Any] | None = None) -> dict:
        """Run one GraphQL query and return its `data` block, retrying on errors."""
        for attempt in range(6):
            try:
                resp = self._client.post(
                    "/graphql", json={"query": query, "variables": variables or {}}
                )
            except httpx.HTTPError:
                # Transport-level drop (GitHub closing a heavy connection) — back
                # off and retry on a fresh connection.
                time.sleep(2 ** attempt)
                continue
            if resp.status_code == 200:
                payload = resp.json()
                if "errors" in payload:
                    # Secondary rate limit -> back off and retry.
                    if _is_retryable(payload["errors"]):
                        time.sleep(2 ** attempt)
                        continue
                    raise RuntimeError(f"GraphQL errors: {payload['errors']}")
                return payload["data"]
            if resp.status_code in (502, 503, 504, 429):
                time.sleep(2 ** attempt)
                continue
            resp.raise_for_status()
        raise RuntimeError("GraphQL query failed after retries")

    def close(self) -> None:
        self._client.close()


def _is_retryable(errors: list[dict]) -> bool:
    """True if the GraphQL errors look like a transient rate-limit hit."""
    return any(e.get("type") in {"RATE_LIMITED", "SERVICE_UNAVAILABLE"} for e in errors)
