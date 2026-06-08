from unittest.mock import MagicMock

from email_digest.gmail import build_query, fetch_recent_emails


def _service(list_resp, messages_by_id):
    """A mock Gmail service: users().messages().list/get(...).execute()."""
    service = MagicMock()
    messages_api = service.users.return_value.messages.return_value
    messages_api.list.return_value.execute.return_value = list_resp

    def fake_get(userId, id, format):
        call = MagicMock()
        value = messages_by_id[id]
        if isinstance(value, Exception):
            call.execute.side_effect = value
        else:
            call.execute.return_value = value
        return call

    messages_api.get.side_effect = fake_get
    return service


def _full_msg(mid, subject):
    return {
        "id": mid,
        "threadId": "t-" + mid,
        "snippet": "snip",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "Subject", "value": subject},
                {"name": "From", "value": "a@b.com"},
            ],
            "body": {},
        },
    }


def test_build_query_filters_inbox_after_timestamp():
    assert build_query(1749200000) == "after:1749200000 in:inbox"


def test_fetch_returns_parsed_emails_for_listed_ids():
    service = _service(
        {"messages": [{"id": "m1"}, {"id": "m2"}]},
        {"m1": _full_msg("m1", "Hello"), "m2": _full_msg("m2", "World")},
    )
    emails = fetch_recent_emails(service, "personal", 123)
    assert [e["id"] for e in emails] == ["m1", "m2"]
    assert emails[0]["subject"] == "Hello"
    assert emails[0]["account"] == "personal"


def test_fetch_empty_when_no_messages():
    service = _service({}, {})
    assert fetch_recent_emails(service, "school", 123) == []


def test_fetch_skips_messages_that_fail_to_load():
    service = _service(
        {"messages": [{"id": "ok"}, {"id": "bad"}]},
        {"ok": _full_msg("ok", "Good"), "bad": ValueError("boom")},
    )
    emails = fetch_recent_emails(service, "personal", 123)
    assert [e["id"] for e in emails] == ["ok"]


def test_fetch_returns_empty_when_list_call_fails():
    service = MagicMock()
    service.users.return_value.messages.return_value.list.return_value.execute.side_effect = RuntimeError("api down")
    assert fetch_recent_emails(service, "personal", 123) == []
