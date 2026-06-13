"""Compute per-engineer impact metrics from extracted PRs and write data.json.

Impact thesis: impact = force multiplication. The cleanest thing GitHub data
can prove is review/unblocking influence — one person measurably helping another
with names and timestamps. The scored composite is built only from review-graph
signals; authorship stats (throughput, AI use, merge rate, reverts) are shown as
context, never scored.

Run from the pipeline/ dir (after extract.py): python metrics.py
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import statistics
from collections import Counter, defaultdict

DATA_DIR = pathlib.Path(__file__).resolve().parents[1] / "data"
IN_FILE = DATA_DIR / "posthog_prs.jsonl"
OUT_FILE = pathlib.Path(__file__).resolve().parents[1] / "frontend" / "public" / "data.json"
META_FILE = DATA_DIR / "extract_meta.json"

MIN_AUTHORED = 3            # "active engineer" threshold
REVERT_WINDOW_H = 48        # a revert within this many hours is a red flag
MEANINGFUL = {"APPROVED", "CHANGES_REQUESTED", "COMMENTED"}
SUBSTANTIVE = {"CHANGES_REQUESTED", "COMMENTED"}

# Weights for the six scored review dimensions (sum = 1.0).
WEIGHTS = {
    "unblocking": 0.30,      # distinct other authors whose PRs they reviewed
    "reciprocity": 0.20,     # reviews given / reviews received
    "review_depth": 0.15,    # substantive reviews / total reviews given
    "responsiveness": 0.15,  # median time-to-first-review (inverted)
    "involvement": 0.10,     # comments left on others' PRs
    "volume": 0.10,          # total reviews given
}

# File patterns that mark a PR as generated/trivial — excluded from scoring.
_GENERATED = ("__snapshots__", ".ambr", ".snap", "pnpm-lock.yaml", "yarn.lock",
              "package-lock.json", "poetry.lock", "go.sum", "Cargo.lock")

_FMT = "%Y-%m-%dT%H:%M:%SZ"


def _parse(ts: str | None) -> dt.datetime | None:
    """Parse a GitHub ISO timestamp to a datetime, or None."""
    return dt.datetime.strptime(ts, _FMT) if ts else None


def _hours(a: str | None, b: str | None) -> float | None:
    """Hours from timestamp a to timestamp b, or None if either is missing."""
    da, db = _parse(a), _parse(b)
    if da and db:
        return (db - da).total_seconds() / 3600
    return None


def is_generated(pr: dict) -> bool:
    """True if the PR looks machine-generated (snapshots/lockfiles) or automated."""
    if "automated" in pr.get("labels", []):
        return True
    paths = pr.get("paths_sampled") or []
    if paths and all(any(g in p for g in _GENERATED) for p in paths):
        return True
    return False


def is_scorable(pr: dict) -> bool:
    """True if the PR should count toward scoring (human, non-chore, non-generated)."""
    if pr["author"]["is_bot"] or not pr["author"]["login"]:
        return False
    if pr["work_type"] == "chore":
        return False
    return not is_generated(pr)


def percentiles(values: dict[str, float]) -> dict[str, float]:
    """Percentile-rank each value against the pool (min->0, max->100)."""
    n = len(values)
    if n <= 1:
        return {k: 100.0 for k in values}
    pool = list(values.values())
    return {
        k: round(100 * sum(1 for x in pool if x < v) / (n - 1), 1)
        for k, v in values.items()
    }


def detect_reverts(prs: list[dict]) -> dict[str, list[dict]]:
    """Map author login -> their PRs reverted within REVERT_WINDOW_H hours.

    GitHub revert PRs are titled `Revert "<original title>"`; we match that
    quoted title back to a recently-merged original and check the time gap.
    """
    merged_by_title: dict[str, list[dict]] = defaultdict(list)
    for pr in prs:
        if pr["state"] == "MERGED":
            merged_by_title[pr["title"]].append(pr)

    reverts: dict[str, list[dict]] = defaultdict(list)
    for pr in prs:
        title = pr["title"] or ""
        low = title.lower()
        if pr["state"] != "MERGED" or not low.startswith("revert"):
            continue
        # Extract the quoted original title.
        start = title.find('"')
        end = title.rfind('"')
        if start == -1 or end <= start:
            continue
        original_title = title[start + 1:end]
        candidates = [
            o for o in merged_by_title.get(original_title, [])
            if o["number"] != pr["number"] and o["merged_at"] and pr["merged_at"]
            and o["merged_at"] < pr["merged_at"]
        ]
        if not candidates:
            continue
        original = max(candidates, key=lambda o: o["merged_at"])
        gap = _hours(original["merged_at"], pr["merged_at"])
        if gap is not None and gap <= REVERT_WINDOW_H:
            author = original["author"]["login"]
            if author:
                reverts[author].append(
                    {"number": original["number"], "title": original["title"],
                     "reverted_by": pr["number"], "hours": round(gap, 1)}
                )
    return reverts


def first_human_review(pr: dict) -> dict | None:
    """Return the earliest meaningful human review on a PR (not the author's)."""
    author = pr["author"]["login"]
    revs = [
        r for r in pr["reviews"]
        if not r["is_bot"] and r["login"] != author
        and r.get("state") in MEANINGFUL and r.get("at")
    ]
    return min(revs, key=lambda r: r["at"]) if revs else None


def build() -> dict:
    """Read PRs, compute all metrics, and return the dashboard data object."""
    prs = [json.loads(line) for line in IN_FILE.read_text().splitlines() if line.strip()]
    if META_FILE.exists():
        meta = json.loads(META_FILE.read_text())
    else:
        # Derive meta from the data if the extract summary isn't present yet.
        dates = sorted(p["closed_at"][:10] for p in prs if p.get("closed_at"))
        meta = {
            "repo": "PostHog/posthog",
            "since": dates[0] if dates else "",
            "until": dates[-1] if dates else "",
            "days": 90,
            "prs_total": len(prs),
            "prs_merged": sum(1 for p in prs if p["state"] == "MERGED"),
            "prs_closed_unmerged": sum(1 for p in prs if p["state"] == "CLOSED"),
        }

    # --- authorship aggregates (for activity + context) over human PRs ---
    authored: dict[str, list[dict]] = defaultdict(list)
    names: dict[str, str] = {}
    for pr in prs:
        a = pr["author"]
        if a["is_bot"] or not a["login"]:
            continue
        authored[a["login"]].append(pr)
        if a.get("name"):
            names[a["login"]] = a["name"]

    reverts = detect_reverts(prs)

    # --- review-graph aggregates over SCORABLE PRs ---
    given = Counter()                          # total reviews given
    substantive = Counter()                    # substantive reviews given
    unblocked: dict[str, set] = defaultdict(set)   # distinct authors unblocked
    received = Counter()                       # reviews received
    involvement = Counter()                    # comments on others' PRs
    ttfr_per_reviewer: dict[str, list] = defaultdict(list)  # latencies per reviewer
    reviewed_for: dict[str, Counter] = defaultdict(Counter)
    dir_ttfr: dict[str, list] = defaultdict(list)  # first-review latency per dir
    area_count = Counter()                         # PRs touching each top-level area

    for pr in prs:
        if not is_scorable(pr):
            continue
        author = pr["author"]["login"]

        # Real top-level directories this PR touched (skip root-level files).
        real_dirs = {p.split("/")[0] for p in pr["paths_sampled"] if "/" in p}
        for d in real_dirs:
            area_count[d] += 1

        # First human review latency -> reviewer responsiveness + dir chokepoints.
        fhr = first_human_review(pr)
        if fhr:
            lat = _hours(pr["created_at"], fhr["at"])
            if lat is not None and lat >= 0:
                for d in real_dirs:
                    dir_ttfr[d].append(lat)

        # Per-reviewer: count their first review on this PR for responsiveness.
        seen_first: dict[str, str] = {}
        for r in pr["reviews"]:
            if r["is_bot"] or r["login"] == author or r.get("state") not in MEANINGFUL:
                continue
            rv = r["login"]
            given[rv] += 1
            received[author] += 1
            unblocked[rv].add(author)
            reviewed_for[rv][author] += 1
            if r.get("state") in SUBSTANTIVE:
                substantive[rv] += 1
            if r.get("at") and (rv not in seen_first or r["at"] < seen_first[rv]):
                seen_first[rv] = r["at"]
        for rv, at in seen_first.items():
            lat = _hours(pr["created_at"], at)
            if lat is not None and lat >= 0:
                ttfr_per_reviewer[rv].append(lat)

        # Comments on others' PRs -> involvement.
        for c in pr["comments"]:
            if not c["is_bot"] and c["login"] != author:
                involvement[c["login"]] += 1

    # --- define active engineers: >= MIN_AUTHORED scorable authored PRs ---
    active = sorted(
        login for login, prs_a in authored.items()
        if sum(1 for p in prs_a if is_scorable(p)) >= MIN_AUTHORED
    )

    # --- raw metric vectors over the active pool ---
    m_unblock = {l: len(unblocked[l]) for l in active}
    m_recip = {l: given[l] / max(received[l], 1) for l in active}
    m_depth = {l: (substantive[l] / given[l] if given[l] else 0.0) for l in active}
    m_invol = {l: involvement[l] for l in active}
    m_volume = {l: given[l] for l in active}
    median_ttfr = {
        l: (statistics.median(ttfr_per_reviewer[l]) if ttfr_per_reviewer[l] else None)
        for l in active
    }
    # Responsiveness: lower latency is better. Non-reviewers get worst rank.
    worst = max((v for v in median_ttfr.values() if v is not None), default=0) + 1
    m_resp = {l: -(median_ttfr[l] if median_ttfr[l] is not None else worst) for l in active}

    # --- percentiles per dimension ---
    p_unblock = percentiles(m_unblock)
    p_recip = percentiles(m_recip)
    p_depth = percentiles(m_depth)
    p_resp = percentiles(m_resp)
    p_invol = percentiles(m_invol)
    p_volume = percentiles(m_volume)

    def composite(l: str) -> float:
        """Weighted sum of dimension percentiles -> 0-100 impact score."""
        return round(
            WEIGHTS["unblocking"] * p_unblock[l]
            + WEIGHTS["reciprocity"] * p_recip[l]
            + WEIGHTS["review_depth"] * p_depth[l]
            + WEIGHTS["responsiveness"] * p_resp[l]
            + WEIGHTS["involvement"] * p_invol[l]
            + WEIGHTS["volume"] * p_volume[l],
            1,
        )

    engineers = []
    for l in active:
        prs_a = authored[l]
        scorable_a = [p for p in prs_a if is_scorable(p)]
        merged = sum(1 for p in prs_a if p["state"] == "MERGED")
        closed_un = sum(1 for p in prs_a if p["state"] == "CLOSED")
        ai_prs = [p for p in prs_a if p["ai_authoring"]["ai_authored"]]
        ai_tools = sorted({t for p in ai_prs for t in p["ai_authoring"]["tools"]})
        wt_mix = Counter(p["work_type"] or "other" for p in prs_a)
        sizes = [p["additions"] + p["deletions"] for p in prs_a]

        engineers.append({
            "login": l,
            "name": names.get(l, l),
            "association": (scorable_a[0]["author"]["association"] if scorable_a else None),
            "score": composite(l),
            "metrics": {
                "distinct_unblocked": m_unblock[l],
                "reviews_given": given[l],
                "reviews_received": received[l],
                "reciprocity": round(m_recip[l], 2),
                "substantive_given": substantive[l],
                "substantive_ratio": round(m_depth[l], 2),
                "median_ttfr_hours": (round(median_ttfr[l], 1) if median_ttfr[l] is not None else None),
                "involvement_comments": involvement[l],
            },
            "percentiles": {
                "unblocking": p_unblock[l],
                "reciprocity": p_recip[l],
                "review_depth": p_depth[l],
                "responsiveness": p_resp[l],
                "involvement": p_invol[l],
                "volume": p_volume[l],
            },
            "context": {
                "authored_total": len(prs_a),
                "merged": merged,
                "closed_unmerged": closed_un,
                "merge_rate": round(merged / (merged + closed_un), 2) if (merged + closed_un) else None,
                "throughput": merged,
                "ai_authored_pct": round(100 * len(ai_prs) / len(prs_a)) if prs_a else 0,
                "ai_tools": ai_tools,
                "work_type_mix": dict(wt_mix.most_common()),
                "median_pr_size": int(statistics.median(sizes)) if sizes else 0,
                "reverts": reverts.get(l, []),
            },
            "reviewed_for": [
                {"login": who, "count": n} for who, n in reviewed_for[l].most_common(12)
            ],
        })

    engineers.sort(key=lambda e: e["score"], reverse=True)
    for i, e in enumerate(engineers, 1):
        e["rank"] = i
        e["known_for"] = known_for(e)

    # --- team panel ---
    # Where the work is: PR volume by top-level codebase area this quarter.
    # A team-activity view (which areas are busiest), not a per-person judgment.
    areas = [{"dir": d, "pr_count": n} for d, n in area_count.most_common(7)]
    # Chokepoint directories: highest median time-to-first-review (>=5 PRs).
    chokepoints = sorted(
        (
            {"dir": d, "median_ttfr_hours": round(statistics.median(v), 1), "pr_count": len(v)}
            for d, v in dir_ttfr.items() if len(v) >= 5
        ),
        key=lambda d: d["median_ttfr_hours"], reverse=True,
    )[:6]

    scatter = [
        {"login": e["login"], "name": e["name"], "size": e["context"]["median_pr_size"],
         "score": e["score"], "rank": e["rank"], "is_top5": e["rank"] <= 5}
        for e in engineers
    ]

    return {
        "meta": {
            **{k: meta[k] for k in ("repo", "since", "until", "days",
                                    "prs_total", "prs_merged", "prs_closed_unmerged")},
            "generated_at": dt.datetime.now(dt.timezone.utc).strftime(_FMT),
            "active_engineers": len(active),
            "weights": WEIGHTS,
            "filters_note": "Bots excluded everywhere; chore & generated PRs excluded from scoring.",
        },
        "engineers": engineers,
        "scatter": scatter,
        "team": {"areas": areas, "chokepoints": chokepoints},
    }


def known_for(e: dict) -> str:
    """Write a one-line 'known for' summary from an engineer's standout signals."""
    m, p = e["metrics"], e["percentiles"]
    parts = [f"Unblocked {m['distinct_unblocked']} engineers"]
    best = max(p, key=p.get)
    if best == "responsiveness" and m["median_ttfr_hours"] is not None:
        parts.append(f"fast reviewer (~{m['median_ttfr_hours']}h to first review)")
    elif best == "volume":
        parts.append(f"{m['reviews_given']} reviews given")
    elif best == "review_depth":
        parts.append(f"deep reviews ({int(m['substantive_ratio'] * 100)}% substantive)")
    elif best == "reciprocity":
        parts.append(f"gives {m['reciprocity']}× more review than received")
    elif best == "involvement":
        parts.append(f"{m['involvement_comments']} comments on others' PRs")
    else:
        parts.append(f"{m['reviews_given']} reviews given")
    return " · ".join(parts)


def main() -> None:
    """Build the data object and write it to frontend/public/data.json."""
    data = build()
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(data, indent=2))
    print(f"Wrote {OUT_FILE}")
    print(f"  active engineers: {data['meta']['active_engineers']}")
    print("  top 5:")
    for e in data["engineers"][:5]:
        print(f"    {e['rank']}. {e['name']} ({e['login']}) score={e['score']} — {e['known_for']}")


if __name__ == "__main__":
    main()
