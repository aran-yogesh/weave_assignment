"""Unit tests for the tightened AI-authoring detector.

Run: python3 test_ai_authoring.py  (plain asserts, no test framework needed)
The key property: prose mentions of "cursor"/"claude"/"codex" must NOT count;
only structured trailers, co-author identities, and the agent block do.
"""

from ai_authoring import detect_ai_authoring


def ai(body="", messages=None, authors=None):
    """Shorthand: run the detector and return its result dict."""
    return detect_ai_authoring(body, messages or [], authors or [])


def test_prose_cursor_not_flagged():
    # "cursor" as ordinary text (DB/editor cursor) must not count.
    r = ai(body="Move the cursor to the end and fix the database cursor leak.")
    assert r["ai_authored"] is False, r
    assert r["tools"] == [], r


def test_prose_claude_mention_not_flagged():
    r = ai(messages=["I asked Claude about this approach but wrote it myself."])
    assert r["ai_authored"] is False, r


def test_coauthored_by_claude_flagged():
    r = ai(messages=["feat: thing\n\nCo-Authored-By: Claude <noreply@anthropic.com>"])
    assert r["ai_authored"] is True, r
    assert r["tools"] == ["Claude Code"], r


def test_coauthored_by_human_not_flagged():
    r = ai(messages=["fix: bug\n\nCo-authored-by: John Doe <john@example.com>"])
    assert r["ai_authored"] is False, r
    assert r["tools"] == [], r


def test_generated_by_unnamed_flags_authored_no_tool():
    r = ai(messages=["chore: x\n\nGenerated-By: internal-agent-v2"])
    assert r["ai_authored"] is True, r
    assert r["tools"] == [], r


def test_coauthor_identity_cursor():
    r = ai(authors=["Cursor Agent cursor@cursor.com"])
    assert r["ai_authored"] is True, r
    assert r["tools"] == ["Cursor"], r


def test_coauthor_email_copilot():
    r = ai(authors=["Copilot copilot@github.com"])
    assert r["ai_authored"] is True, r
    assert r["tools"] == ["GitHub Copilot"], r


def test_agent_block_flags_ai_but_does_not_attribute_tools_from_prose():
    # The agent block marks AI authorship, but tool names mentioned in its prose
    # (often describing reviewers, e.g. "the codex bot") must NOT be attributed.
    body = ("Summary.\n\n🤖 Agent context\n"
            "Authored with PostHog Code. Reviewed by the codex bot and cursor swarm.\n")
    r = ai(body=body)
    assert r["ai_authored"] is True, r
    assert r["tools"] == [], r  # tools come only from trailers/identities


def test_tool_attributed_from_real_trailer_even_with_agent_block():
    body = "Change.\n\n🤖 Agent context\nReviewed by the codex bot.\n"
    r = ai(body=body, messages=["feat\n\nGenerated-By: PostHog Code"])
    assert r["ai_authored"] is True, r
    assert r["tools"] == ["PostHog Code"], r  # codex (a reviewer) not attributed


def test_codex_prose_without_block_not_flagged():
    r = ai(body="We considered the codex of rules here.")
    assert r["ai_authored"] is False, r


def test_human_name_containing_cursor_word_boundary():
    # A trailer naming a human whose text happens to include 'cursor' as a
    # substring of a larger word must not match (word boundary).
    r = ai(messages=["fix\n\nCo-authored-by: Precursors Team <team@x.com>"])
    assert r["tools"] == [], r
    assert r["ai_authored"] is False, r


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)} passed")
