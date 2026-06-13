"""Detect which AI tool (if any) co-authored a PR — from STRUCTURED signals only.

Over-counting comes from scanning free prose for tool names: "cursor" matches a
database cursor, "claude" matches any casual mention. To avoid that, this reads
only signals that explicitly name a tool:

  1. Git commit-message trailers — `Co-Authored-By:` / `Generated-By:` /
     `Assisted-By:` lines whose value names a known AI tool.
  2. Commit co-author identities (GitHub parses `Co-authored-by` trailers into a
     commit's authors), matched by word boundary against tool names/emails.
  3. PostHog's templated "🤖 Agent context" block in the PR body.

Tool names are matched with word boundaries, so the tool "Cursor" never matches
the word "cursor" inside ordinary text.
"""

from __future__ import annotations

import re

# Canonical tool name -> word-boundary pattern that identifies it.
_TOOL_PATTERNS = {
    "PostHog Code": re.compile(r"\bposthog[\s-]?code\b", re.I),
    "Claude Code": re.compile(r"\bclaude\b", re.I),
    "Cursor": re.compile(r"\bcursor\b", re.I),
    "GitHub Copilot": re.compile(r"\bcopilot\b", re.I),
    "Codex": re.compile(r"\bcodex\b", re.I),
    "Devin": re.compile(r"\bdevin\b", re.I),
}

# Commit-trailer keys that signal machine/agent involvement.
_TRAILER_KEYS = ("co-authored-by", "generated-by", "assisted-by", "authored-by", "created-by")
# Trailers whose mere presence implies generation, even if no tool is named.
_GENERATION_KEYS = ("generated-by", "created-by")
_TRAILER_RE = re.compile(r"^\s*([A-Za-z][A-Za-z-]*)\s*:\s*(.+?)\s*$")

# PostHog's templated agent block (structured marker, not prose).
_AGENT_BLOCK_RE = re.compile(r"🤖\s*agent context", re.I)
_AUTONOMY_RE = re.compile(r"autonomy:\s*([^\n]+)", re.IGNORECASE)


def _tools_in(text: str) -> set[str]:
    """Return the tool names whose word-boundary pattern matches the text."""
    return {name for name, rx in _TOOL_PATTERNS.items() if rx.search(text or "")}


def detect_ai_authoring(body_text: str, commit_messages: list[str], commit_authors: list[str]) -> dict:
    """Return {ai_authored, tools, autonomy} from structured trailers + identities.

    body_text is the PR body; commit_messages are commit message bodies (where
    trailers live); commit_authors are co-author display names/emails.
    """
    tools: set[str] = set()
    ai_authored = False

    # 1. Commit-message trailers (Co-Authored-By / Generated-By / ...).
    for msg in commit_messages:
        for line in (msg or "").splitlines():
            m = _TRAILER_RE.match(line)
            if not m:
                continue
            key, value = m.group(1).lower(), m.group(2)
            if key not in _TRAILER_KEYS:
                continue
            found = _tools_in(value)
            if found:
                tools |= found
                ai_authored = True
            elif key in _GENERATION_KEYS:
                ai_authored = True  # explicit generation trailer, tool unnamed

    # 2. Commit co-author identities (GitHub parses these from Co-authored-by).
    for ident in commit_authors:
        found = _tools_in(ident)
        if found:
            tools |= found
            ai_authored = True

    # 3. PostHog's templated agent-context block marks the PR as AI-authored,
    #    but we do NOT read tool names from its prose — that text mentions other
    #    tools as reviewers ("reviewed by the codex bot"), which would mis-
    #    attribute. Tools come only from the high-precision trailer/identity
    #    signals above.
    body = body_text or ""
    if _AGENT_BLOCK_RE.search(body):
        ai_authored = True

    autonomy = None
    am = _AUTONOMY_RE.search(body)
    if am:
        autonomy = am.group(1).strip()

    return {"ai_authored": ai_authored, "tools": sorted(tools), "autonomy": autonomy}
