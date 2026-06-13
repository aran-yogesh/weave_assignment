"""Recompute ONLY the `ai_authoring` field on the existing dataset.

The detector reads PR body + commit trailers/authors — a tiny slice of each PR.
Re-tuning it doesn't need a full re-pull of reviews/files/comments, so this
re-fetches just those fields with a minimal query (big pages) and patches the
`ai_authoring` field of each record in data/posthog_prs.jsonl in place.

Run from pipeline/:  python3 patch_ai.py
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib

import extract
from ai_authoring import detect_ai_authoring
from github_client import GitHubClient

PAGE = 100  # minimal payload -> safe to page large

QUERY = """
query($q: String!, $cursor: String) {
  search(query: $q, type: ISSUE, first: %d, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes {
      ... on PullRequest {
        number
        bodyText
        commits(first: 10) {
          nodes { commit { messageBody authors(first: 5) { nodes { name email } } } }
        }
      }
    }
  }
}
""" % PAGE


def ai_for(pr: dict) -> dict:
    """Run the detector on one minimal PR node."""
    messages = [c["commit"]["messageBody"] for c in pr["commits"]["nodes"]]
    authors = [
        f"{a.get('name', '')} {a.get('email', '')}"
        for c in pr["commits"]["nodes"]
        for a in c["commit"]["authors"]["nodes"]
    ]
    return detect_ai_authoring(pr["bodyText"], messages, authors)


def fetch_ai_map() -> dict[int, dict]:
    """Return {pr_number: ai_authoring} for every PR in the 90-day window."""
    client = GitHubClient()
    until = dt.datetime.now(dt.timezone.utc).date()
    since = until - dt.timedelta(days=extract.DAYS_BACK)
    out: dict[int, dict] = {}
    for w_start, w_end in extract.windows(since, until):
        q = f"repo:{extract.OWNER}/{extract.NAME} is:pr closed:{w_start}..{w_end} sort:created-asc"
        cursor = None
        while True:
            data = client.query(QUERY, {"q": q, "cursor": cursor})
            search = data["search"]
            for node in search["nodes"]:
                if node:
                    out[node["number"]] = ai_for(node)
            if not search["pageInfo"]["hasNextPage"]:
                break
            cursor = search["pageInfo"]["endCursor"]
        print(f"  {w_start}..{w_end}: {len(out)} cumulative", flush=True)
    client.close()
    return out


def main() -> None:
    """Patch ai_authoring on every record, reporting coverage and any changes."""
    ai_map = fetch_ai_map()
    path = pathlib.Path(__file__).resolve().parents[1] / "data" / "posthog_prs.jsonl"
    records = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]

    patched, missing, changed = 0, 0, 0
    for r in records:
        new = ai_map.get(r["number"])
        if new is None:
            missing += 1
            continue
        if new != r["ai_authoring"]:
            changed += 1
        r["ai_authoring"] = new
        patched += 1

    path.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    print(f"\nRecords: {len(records)} | patched: {patched} | changed: {changed} | "
          f"not refetched (kept old): {missing}")


if __name__ == "__main__":
    main()
