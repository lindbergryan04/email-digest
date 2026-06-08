from unittest.mock import MagicMock

from email_digest.triage import (
    EmailJudgment,
    TriageResult,
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


def test_build_triage_input_projects_only_needed_fields():
    out = build_triage_input([_email("1", **{"from": "r@corp.com"}, subject="Hi")])
    assert out == [
        {"id": "1", "from": "r@corp.com", "subject": "Hi", "snippet": "snip", "body_excerpt": "body text"}
    ]


def test_triage_emails_empty_returns_empty_and_skips_api():
    client = MagicMock()
    assert triage_emails(client, []) == {}
    client.messages.parse.assert_not_called()


def test_triage_emails_maps_ids_to_judgments():
    client = MagicMock()
    client.messages.parse.return_value.parsed_output = TriageResult(
        emails=[
            EmailJudgment(id="1", importance="high", category="internship",
                          summary="interview invite", is_event=False, has_free_food=False),
            EmailJudgment(id="2", importance="ignore", category="other",
                          summary="promo", is_event=False, has_free_food=False),
        ]
    )

    judgments = triage_emails(client, [_email("1"), _email("2")])

    assert set(judgments) == {"1", "2"}
    assert judgments["1"]["importance"] == "high"
    assert judgments["1"]["category"] == "internship"
    assert judgments["2"]["importance"] == "ignore"

    client.messages.parse.assert_called_once()
    _, kwargs = client.messages.parse.call_args
    assert kwargs["model"] == "claude-haiku-4-5"
    assert kwargs["output_format"] is TriageResult
    assert kwargs["max_tokens"] >= 16000


def test_triage_emails_returns_empty_on_api_error():
    client = MagicMock()
    client.messages.parse.side_effect = RuntimeError("boom")
    assert triage_emails(client, [_email("1")]) == {}


def test_triage_emails_returns_empty_on_no_parsed_output():
    client = MagicMock()
    client.messages.parse.return_value.parsed_output = None
    assert triage_emails(client, [_email("1")]) == {}
