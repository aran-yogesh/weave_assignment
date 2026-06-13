"""Extract every closed PR (merged AND closed-unmerged) from the last 90 days.

Windowing by `closed:` date captures both merged and closed-unmerged PRs in
one sweep (a merged PR is also closed). Writes one JSON record per PR to
data/posthog_prs.jsonl plus a summary to data/extract_meta.json.

Run from the pipeline/ dir: python extract.py
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib

from ai_authoring import detect_ai_authoring
from github_client import GitHubClient

OWNER, NAME = "PostHog", "posthog"
WINDOW_DAYS = 5          # keep each window safely under the 1000-result search cap
DAYS_BACK = 90
PAGE_SIZE = 30

DATA_DIR = pathlib.Path(__file__).resolve().parents[1] / "data"
OUT_FILE = DATA_DIR / "posthog_prs.jsonl"
META_FILE = DATA_DIR / "extract_meta.json"

# One page of closed PRs with every signal the dashboard needs.
QUERY = """
query($q:String!, $cursor:String) {
  rateLimit { remaining }
  search(query:$q, type:ISSUE, first:%d, after:$cursor) {
    issueCount
    pageInfo { hasNextPage endCursor }
    nodes {
      ... on PullRequest {
        number title bodyText state authorAssociation
        createdAt mergedAt closedAt additions deletions changedFiles
        author { login __typename ... on User { name } }
        mergedBy { login }
        reactions { totalCount }
        labels(first:15) { nodes { name } }
        files(first:30) { totalCount nodes { path } }
        reviews(first:30) { nodes { author { login __typename } state submittedAt } }
        comments(first:30) { nodes { author { login __typename } createdAt } }
        reviewThreads { totalCount }
        closingIssuesReferences { totalCount }
        commits(first:10) {
          totalCount
          nodes { commit { messageBody authors(first:5) { nodes { name email } } } }
        }
        statusCommit: commits(last:1) {
          nodes { commit { statusCheckRollup { state } } }
        }
      }
    }
  }
}
""" % PAGE_SIZE


def windows(since: dt.date, until: dt.date):
    """Yield (start, end) inclusive date ranges of WINDOW_DAYS, oldest first."""
    start = since
    while start <= until:
        end = min(start + dt.timedelta(days=WINDOW_DAYS - 1), until)
        yield start, end
        start = end + dt.timedelta(days=1)


def _people(nodes: list[dict], time_key: str | None = None) -> list[dict]:
    """Flatten review/comment author nodes into {login, is_bot, ...} records."""
    out = []
    for n in nodes:
        a = n.get("author")
        if not a:
            continue
        rec = {"login": a["login"], "is_bot": a["__typename"] == "Bot"}
        if "state" in n:
            rec["state"] = n["state"]
        if "submittedAt" in n:
            rec["at"] = n["submittedAt"]
        if time_key and n.get(time_key):
            rec["at"] = n[time_key]
        out.append(rec)
    return out


def _top_dirs(paths: list[str]) -> list[str]:
    """Derive distinct top-level directories touched (first path segment)."""
    return sorted({p.split("/")[0] for p in paths if p})


def _cycle_hours(created: str, merged: str | None) -> float | None:
    """Hours between PR creation and merge, or None if not merged."""
    if not created or not merged:
        return None
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    delta = dt.datetime.strptime(merged, fmt) - dt.datetime.strptime(created, fmt)
    return round(delta.total_seconds() / 3600, 1)


_WORK_TYPES = {"feat", "fix", "chore", "refactor", "docs", "test", "perf", "ci", "revert"}


def _work_type(title: str) -> str | None:
    """Parse the conventional-commit prefix (feat/fix/chore/...) from a title."""
    head = title.split("(")[0].split(":")[0].strip().lower()
    return head if head in _WORK_TYPES else None


def transform(pr: dict) -> dict:
    """Turn a raw GraphQL PR node into a flat, analysis-ready record."""
    paths = [f["path"] for f in pr["files"]["nodes"]]
    # Commit message bodies carry the trailers; co-author name+email are the
    # structured identities GitHub parses from `Co-authored-by` lines.
    commit_messages = [c["commit"]["messageBody"] for c in pr["commits"]["nodes"]]
    commit_authors = [
        f"{a.get('name', '')} {a.get('email', '')}"
        for c in pr["commits"]["nodes"]
        for a in c["commit"]["authors"]["nodes"]
    ]

    status_nodes = pr["statusCommit"]["nodes"]
    ci = None
    if status_nodes and status_nodes[0]["commit"]["statusCheckRollup"]:
        ci = status_nodes[0]["commit"]["statusCheckRollup"]["state"]

    author = pr["author"] or {}
    title = pr["title"] or ""

    return {
        "number": pr["number"],
        "title": title,
        "state": pr["state"],  # MERGED or CLOSED (closed-unmerged)
        "work_type": _work_type(title),
        "author": {
            "login": author.get("login"),
            "name": author.get("name"),
            "is_bot": author.get("__typename") == "Bot",
            "association": pr["authorAssociation"],
        },
        "created_at": pr["createdAt"],
        "merged_at": pr["mergedAt"],
        "closed_at": pr["closedAt"],
        "merged_by": (pr["mergedBy"] or {}).get("login"),
        "cycle_hours": _cycle_hours(pr["createdAt"], pr["mergedAt"]),
        "additions": pr["additions"],
        "deletions": pr["deletions"],
        "changed_files": pr["changedFiles"],
        "dirs": _top_dirs(paths),
        "paths_sampled": paths,
        "reviews": _people(pr["reviews"]["nodes"]),
        "comments": _people(pr["comments"]["nodes"], time_key="createdAt"),
        "review_threads": pr["reviewThreads"]["totalCount"],
        "reactions": pr["reactions"]["totalCount"],
        "ci_status": ci,
        "closes_issues": pr["closingIssuesReferences"]["totalCount"],
        "commits": pr["commits"]["totalCount"],
        "labels": [l["name"] for l in pr["labels"]["nodes"]],
        "ai_authoring": detect_ai_authoring(pr["bodyText"], commit_messages, commit_authors),
    }


def fetch_window(client: GitHubClient, w_start, w_end, target) -> int:
    """Fetch one date window to its own checkpoint file; return PR count.

    Writes to a .tmp file and renames on success, so a half-written window is
    never mistaken for a complete one on resume.
    """
    q = f"repo:{OWNER}/{NAME} is:pr closed:{w_start}..{w_end} sort:created-asc"
    cursor, count = None, 0
    tmp = target.with_suffix(".tmp")
    with tmp.open("w") as fh:
        while True:
            data = client.query(QUERY, {"q": q, "cursor": cursor})
            search = data["search"]
            for node in search["nodes"]:
                if not node:
                    continue
                fh.write(json.dumps(transform(node)) + "\n")
                count += 1
            if not search["pageInfo"]["hasNextPage"]:
                break
            cursor = search["pageInfo"]["endCursor"]
    tmp.rename(target)
    return count


def main() -> None:
    """Extract all closed PRs window-by-window, resuming completed windows."""
    client = GitHubClient()
    until = dt.datetime.now(dt.timezone.utc).date()
    since = until - dt.timedelta(days=DAYS_BACK)
    win_dir = DATA_DIR / "windows"
    win_dir.mkdir(parents=True, exist_ok=True)

    window_files = []
    for w_start, w_end in windows(since, until):
        target = win_dir / f"{w_start}.jsonl"
        if target.exists():
            n = sum(1 for _ in target.open())
            print(f"  {w_start}..{w_end}: cached ({n} PRs)", flush=True)
        else:
            n = fetch_window(client, w_start, w_end, target)
            print(f"  {w_start}..{w_end}: {n:4} PRs fetched", flush=True)
        window_files.append(target)

    # Concatenate all window checkpoints into the final dataset.
    total, merged, closed_unmerged = 0, 0, 0
    with OUT_FILE.open("w") as out:
        for wf in window_files:
            for line in wf.open():
                out.write(line)
                total += 1
                if '"state": "MERGED"' in line:
                    merged += 1
                else:
                    closed_unmerged += 1

    META_FILE.write_text(
        json.dumps(
            {
                "repo": f"{OWNER}/{NAME}",
                "since": since.isoformat(),
                "until": until.isoformat(),
                "days": DAYS_BACK,
                "prs_total": total,
                "prs_merged": merged,
                "prs_closed_unmerged": closed_unmerged,
                "output": str(OUT_FILE),
            },
            indent=2,
        )
    )
    print(f"\nDone. {total} PRs ({merged} merged, {closed_unmerged} closed-unmerged)", flush=True)
    client.close()


if __name__ == "__main__":
    main()
