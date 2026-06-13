"""Detect which AI tool (if any) helped author a PR, and at what autonomy level.

PostHog tags AI authorship two ways: a "Agent context" block in the PR body
and a `Generated-By:` / `Co-Authored-By:` footer in commit messages. This
module reads those signals out of free text into a small structured record.
"""

from __future__ import annotations

import re

# Map a canonical tool name to the substrings that identify it (lowercased).
_TOOL_PATTERNS = {
    "PostHog Code": ["posthog code"],
    "Claude Code": ["claude code", "claude-code", "claude"],
    "Cursor": ["cursor"],
    "GitHub Copilot": ["copilot"],
    "Codex": ["codex"],
    "Devin": ["devin"],
}

_AUTONOMY_RE = re.compile(r"autonomy:\s*([^\n]+)", re.IGNORECASE)
_AGENT_HINTS = ("i'm an agent", "🤖 agent context", "agent context", "generated-by:")


def detect_ai_authoring(body_text: str, commit_bodies: list[str]) -> dict:
    """Return {ai_authored, tools, autonomy} parsed from PR body + commit text."""
    haystack = (body_text or "").lower()
    for cb in commit_bodies:
        haystack += "\n" + (cb or "").lower()

    tools = sorted(
        {name for name, pats in _TOOL_PATTERNS.items() if any(p in haystack for p in pats)}
    )

    autonomy = None
    match = _AUTONOMY_RE.search(body_text or "")
    if match:
        autonomy = match.group(1).strip()

    ai_authored = bool(tools) or any(h in haystack for h in _AGENT_HINTS)
    return {"ai_authored": ai_authored, "tools": tools, "autonomy": autonomy}
