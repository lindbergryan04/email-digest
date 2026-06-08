import base64

from email_digest.parsing import (
    BODY_TRUNCATE_CHARS,
    decode_base64url,
    extract_body,
    parse_message,
    strip_html,
)


def b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii")


def test_decode_base64url_roundtrip():
    assert decode_base64url(b64("Hello, world!")) == "Hello, world!"


def test_decode_base64url_handles_utf8():
    assert decode_base64url(b64("café ☕ 🚀")) == "café ☕ 🚀"


def test_strip_html_removes_tags_and_collapses_whitespace():
    html = "<p>Hello   <b>there</b></p>\n<p>friend</p>"
    assert strip_html(html) == "Hello there friend"


def test_strip_html_drops_script_and_style():
    html = "<style>.x{color:red}</style><script>evil()</script><p>visible</p>"
    assert strip_html(html) == "visible"


def test_extract_body_plain_top_level():
    payload = {"mimeType": "text/plain", "body": {"data": b64("plain body")}}
    assert extract_body(payload) == "plain body"


def test_extract_body_prefers_plain_over_html():
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {"mimeType": "text/html", "body": {"data": b64("<p>html</p>")}},
            {"mimeType": "text/plain", "body": {"data": b64("the plain one")}},
        ],
    }
    assert extract_body(payload) == "the plain one"


def test_extract_body_falls_back_to_html_when_no_plain():
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {"mimeType": "text/html", "body": {"data": b64("<p>only <b>html</b></p>")}},
        ],
    }
    assert extract_body(payload) == "only html"


def test_extract_body_recurses_into_nested_parts():
    payload = {
        "mimeType": "multipart/mixed",
        "parts": [
            {
                "mimeType": "multipart/alternative",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": b64("nested plain")}},
                ],
            }
        ],
    }
    assert extract_body(payload) == "nested plain"


def test_extract_body_empty_when_nothing_usable():
    assert extract_body({"mimeType": "image/png", "body": {}}) == ""


def test_parse_message_extracts_fields_case_insensitively():
    msg = {
        "id": "abc",
        "threadId": "thread-1",
        "snippet": "snip",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "Recruiter <r@corp.com>"},
                {"name": "Subject", "value": "Interview"},
                {"name": "Date", "value": "Mon, 8 Jun 2026 12:00:00 -0700"},
            ],
            "body": {"data": b64("hello")},
        },
    }
    parsed = parse_message(msg, "personal")
    assert parsed["account"] == "personal"
    assert parsed["id"] == "abc"
    assert parsed["thread_id"] == "thread-1"
    assert parsed["from"] == "Recruiter <r@corp.com>"
    assert parsed["subject"] == "Interview"
    assert parsed["date"].startswith("Mon, 8 Jun 2026")
    assert parsed["snippet"] == "snip"
    assert parsed["body"] == "hello"


def test_parse_message_missing_headers_default_to_empty():
    msg = {"id": "x", "threadId": "t", "payload": {}}
    parsed = parse_message(msg, "school")
    assert parsed["from"] == ""
    assert parsed["subject"] == ""
    assert parsed["date"] == ""
    assert parsed["snippet"] == ""
    assert parsed["body"] == ""


def test_parse_message_truncates_long_body():
    long_text = "a" * (BODY_TRUNCATE_CHARS + 500)
    msg = {
        "id": "x",
        "threadId": "t",
        "payload": {"mimeType": "text/plain", "body": {"data": b64(long_text)}},
    }
    parsed = parse_message(msg, "personal")
    assert len(parsed["body"]) == BODY_TRUNCATE_CHARS
