import re
from datetime import datetime, timezone

from email_digest.formatting import format_digest, organize_digest

NOW = datetime(2026, 6, 8, 9, 30, tzinfo=timezone.utc)
ANSI = re.compile(r"\033\[[0-9;]*m")


def plain(s: str) -> str:
    return ANSI.sub("", s)


def make(
    subject,
    importance,
    category="other",
    *,
    is_event=False,
    food=False,
    account="personal",
    sender="x@y.com",
    summary="summary",
):
    email = {"subject": subject, "from": sender, "account": account, "id": subject}
    judgment = {
        "importance": importance,
        "category": category,
        "summary": summary,
        "is_event": is_event,
        "has_free_food": food,
    }
    return email, judgment


def test_organize_excludes_ignored():
    inbox, events, ignored = organize_digest([make("keep", "high"), make("drop", "ignore")])
    assert [e["subject"] for e, _ in inbox] == ["keep"]
    assert events == []
    assert ignored == 1


def test_organize_sorts_inbox_by_importance():
    triaged = [make("lo", "low"), make("hi", "high"), make("med", "medium")]
    inbox, _, _ = organize_digest(triaged)
    assert [e["subject"] for e, _ in inbox] == ["hi", "med", "lo"]


def test_organize_separates_events_food_first():
    triaged = [
        make("plain-event", "low", is_event=True, food=False),
        make("food-event", "low", is_event=True, food=True),
        make("inbox-item", "high"),
    ]
    inbox, events, _ = organize_digest(triaged)
    assert [e["subject"] for e, _ in inbox] == ["inbox-item"]
    assert [e["subject"] for e, _ in events] == ["food-event", "plain-event"]


def test_format_digest_shows_shown_hides_ignored():
    triaged = [
        make("Interview invite", "high", "internship", summary="reply about your application"),
        make("Spam promo", "ignore"),
    ]
    text = plain(format_digest(triaged, 24, NOW))
    assert "Interview invite" in text
    assert "Spam promo" not in text
    assert "URGENT" in text
    assert "1 newsletter" in text


def test_format_digest_marks_free_food_event():
    triaged = [make("Info session", "low", "school", is_event=True, food=True, summary="free pizza")]
    out = format_digest(triaged, 24, NOW)
    text = plain(out)
    assert "UPCOMING EVENTS" in text
    assert "Info session" in text
    assert "⭐" in out


def test_format_digest_empty_state():
    text = plain(format_digest([make("promo", "ignore")], 6, NOW))
    assert "Nothing important" in text
    assert "1 newsletter" in text


def test_format_digest_header_uses_injected_now():
    text = plain(format_digest([make("x", "high")], 24, NOW))
    assert "Monday, June 08, 2026" in text
