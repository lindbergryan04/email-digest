import json
from unittest.mock import MagicMock

from email_digest.triage import (
    OUTPUT_SCHEMA,
    build_triage_input,
    triage_emails,
)


def _email(eid, **kw):
    base = {
        "id": eid,
        "account": "personal",
        "thread_id": "t",
        "from": "a@b.com",
        "subject": "subject",
        "date": "",
        "snippet": "snip",
        "body": "body text",
    }
    base.update(kw)
    return base


def _ok_response(emails_json):
    """A fake requests.Response carrying the Anthropic Messages API shape."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "content": [{"type": "text", "text": json.dumps({"emails": emails_json})}]
    }
    return resp


def test_build_triage_input_projects_only_needed_fields():
    out = build_triage_input([_email("1", **{"from": "r@corp.com"}, subject="Hi")])
    assert out == [
        {"id": "1", "from": "r@corp.com", "subject": "Hi", "snippet": "snip", "body_excerpt": "body text"}
    ]


def test_triage_emails_empty_returns_empty_and_skips_api():
    post = MagicMock()
    assert triage_emails([], api_key="k", post=post) == {}
    post.assert_not_called()


def test_triage_emails_maps_ids_to_judgments():
    post = MagicMock(return_value=_ok_response([
        {"id": "1", "importance": "high", "category": "internship",
         "summary": "interview", "is_event": False, "has_free_food": False},
        {"id": "2", "importance": "ignore", "category": "other",
         "summary": "promo", "is_event": False, "has_free_food": False},
    ]))

    judgments = triage_emails([_email("1"), _email("2")], api_key="test-key", post=post)

    assert set(judgments) == {"1", "2"}
    assert judgments["1"]["importance"] == "high"
    assert judgments["1"]["category"] == "internship"
    assert judgments["2"]["importance"] == "ignore"

    post.assert_called_once()
    url = post.call_args.args[0]
    body = post.call_args.kwargs["json"]
    headers = post.call_args.kwargs["headers"]
    assert url.endswith("/v1/messages")
    assert body["model"] == "claude-haiku-4-5"
    assert body["max_tokens"] >= 16000
    assert body["output_config"]["format"]["schema"] == OUTPUT_SCHEMA
    assert headers["x-api-key"] == "test-key"
    assert headers["anthropic-version"]


def test_triage_emails_returns_empty_on_http_error():
    resp = MagicMock()
    resp.status_code = 500
    resp.text = "internal error"
    post = MagicMock(return_value=resp)
    assert triage_emails([_email("1")], api_key="k", post=post) == {}


def test_triage_emails_returns_empty_on_malformed_response():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"content": []}  # no text block
    post = MagicMock(return_value=resp)
    assert triage_emails([_email("1")], api_key="k", post=post) == {}
