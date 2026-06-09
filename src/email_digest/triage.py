"""Email triage via Claude's Messages API.

Calls the API directly over HTTP with ``requests`` (which supports Python 3.8)
rather than the anthropic SDK -- the SDK requires Python >=3.9, which would stop
this tool from installing into older environments. The request uses
``output_config`` structured outputs so Claude returns schema-valid JSON, which
is then validated with Pydantic.

The HTTP call is the one impure edge: tests inject a fake ``post``. Any failure
(network, non-200, malformed reply) returns ``{}`` so the caller falls every
email back to manual review and nothing is dropped. ``max_tokens`` is generous
-- the prototype's 8192 truncated the JSON on a full inbox.
"""

from __future__ import annotations

import json
import sys
from typing import List, Literal

import requests
from pydantic import BaseModel

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
MODEL = "claude-haiku-4-5"
MAX_TOKENS = 16000

Importance = Literal["high", "medium", "low", "ignore"]
Category = Literal["internship", "human", "school", "other"]


class EmailJudgment(BaseModel):
    id: str
    importance: Importance
    category: Category
    summary: str
    is_event: bool
    has_free_food: bool


class TriageResult(BaseModel):
    emails: List[EmailJudgment]


# JSON schema sent to Claude via output_config; mirrors TriageResult.
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "emails": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "importance": {"type": "string", "enum": ["high", "medium", "low", "ignore"]},
                    "category": {"type": "string", "enum": ["internship", "human", "school", "other"]},
                    "summary": {"type": "string"},
                    "is_event": {"type": "boolean"},
                    "has_free_food": {"type": "boolean"},
                },
                "required": ["id", "importance", "category", "summary", "is_event", "has_free_food"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["emails"],
    "additionalProperties": False,
}


SYSTEM_PROMPT = """You are an email triage assistant for Ryan, a UC San Diego student actively applying to summer internships. Your goal: surface the few emails that need his attention TODAY and ignore everything else. Err on the side of "ignore" -- Ryan would rather miss a borderline FYI than read 30 items.

For each email, classify it on three axes:

1. importance:
   - "high"    -- Must read today. Direct reply to an internship application, interview invite/scheduling, take-home assessment link (e.g. coderpad.io, hackerrank, codility), recruiter writing directly to Ryan, offer, rejection, time-sensitive academic deadline (grade dispute window, registration closing), urgent message from a real person.
   - "medium"  -- Worth knowing about. Real personal message from a known human, campus safety alert (Timely Warning, evacuation, lockdown), professor/TA writing to him personally, financial-aid action item, dorm package pickup, in-person event he RSVP'd to.
   - "low"     -- Skim later. Mildly relevant info: course platform announcements that aren't deadlines, club/dept events he might want to attend, alumni networking opportunities.
   - "ignore"  -- Don't show. The vast majority of school inbox traffic falls here.

2. category:
   - "internship" -- Direct correspondence about Ryan's job applications (replies, recruiters, assessments, interview scheduling, offers, rejections). NOT generic job-listing emails.
   - "human"      -- Personal message from a real, named individual (friend, family, professor, classmate) addressed to Ryan, not a bulk template.
   - "school"     -- Academic/administrative notices that aren't pure marketing.
   - "other"      -- Everything else.

3. summary: ONE sentence, max 18 words. Plain English, no fluff. If has_free_food is true, the summary MUST specifically name the food (e.g., "free pizza at info session" -- not just "free food provided").

4. is_event: true if the email is an invitation, announcement, or registration link for a gathering Ryan could attend -- in-person or virtual. Examples: info sessions, career fairs, hackathons, networking mixers, club meetings, lectures, workshops, panels, demo days, parties, food pop-ups, study breaks. NOT events: order confirmations or receipts for events already purchased, recurring class meetings, regular office hours, internship application deadlines that aren't gatherings, past events being recapped.

5. has_free_food: true ONLY if the email explicitly states food or drink is provided/free/complimentary. Look for words like: pizza, snacks, boba, lunch, breakfast, dinner, refreshments, coffee, food trucks, catering, "food provided", "we'll feed you", "free food", "drinks provided". If the email is an event but doesn't mention food, this is false.

Decision rules -- apply in order:

A. The "internship -> medium minimum" rule ONLY applies to direct correspondence about Ryan's specific applications. It does NOT apply to:
   - Handshake / LinkedIn / Indeed / WayUp digests of job listings ("X is hiring", "Y new jobs for you") -> ignore
   - Career-center event announcements ("Company info session", "Career fair registration") -> low
   - Profile-reminder nags ("Complete your profile", "Add skills") -> ignore
   - General career newsletters -> ignore

B. Sender domain heuristics:
   - no-reply@, notifications@, newsletter@, team@, marketing@, updates@, digest@ -> presumptively ignore UNLESS the content is clearly a direct reply to an application, an assessment link from a known platform (coderpad.io, hackerrank.com, codility.com, ashbyhq.com, greenhouse.io, lever.co, workday.com, smartrecruiters.com), or a campus safety alert.
   - handshake@*, eventbrite@*, gradescope@*, campuswire@*, canvas@* -> almost always ignore. Exceptions are rare (a recruiter using Handshake to message Ryan directly would still mention his name and be conversational).

C. Always-ignore patterns:
   - Survey requests ("How are we doing?", "UCUES", "Take our 5-minute survey", "Tell us about your experience")
   - Prize drawings, raffles, swag giveaways, gift-card promotions
   - Order/ticket confirmations and receipts (Eventbrite, Amazon, Apple, etc.)
   - Submission confirmations from course platforms (Gradescope, Canvas, Campuswire)
   - "Almost there!" / "Finish your profile" reminders
   - Generic department newsletters and digests
   - Marketing/promotional content from any source
   - Quarterly billing/registration reminders unless there's a specific deadline within 7 days

D. When in doubt between two adjacent levels, pick the LOWER one. Between "low" and "ignore", pick "ignore" unless there's a clear reason it's worth Ryan's attention.

CRITICAL OUTPUT REQUIREMENT: Return exactly one entry per input email. Each output entry MUST include the `id` field from its corresponding input email, copied verbatim. Do not merge, deduplicate, or drop any emails. If two emails look identical, still return separate entries for each (just classify both appropriately -- e.g., both can be "ignore")."""


def build_triage_input(emails):
    """Project parsed emails down to just the fields Claude triages on."""
    return [
        {
            "id": e["id"],
            "from": e["from"],
            "subject": e["subject"],
            "snippet": e["snippet"],
            "body_excerpt": e["body"],
        }
        for e in emails
    ]


def triage_emails(emails, *, api_key, model=MODEL, max_tokens=MAX_TOKENS, post=None):
    """Return ``{email_id: judgment_dict}``.

    Returns ``{}`` on empty input or any failure -- the caller treats missing
    ids as "needs manual review" so nothing is dropped. ``post`` defaults to
    ``requests.post`` and is injected by tests.
    """
    if not emails:
        return {}

    post = post or requests.post
    try:
        resp = post(
            ANTHROPIC_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": max_tokens,
                "system": [
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                "output_config": {"format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
                "messages": [
                    {
                        "role": "user",
                        "content": "Triage these emails (JSON array follows):\n\n"
                        + json.dumps(build_triage_input(emails), indent=2),
                    }
                ],
            },
            timeout=120,
        )
        if resp.status_code != 200:
            print(
                f"[triage] Claude API returned {resp.status_code}: {resp.text[:500]}",
                file=sys.stderr,
            )
            return {}
        data = resp.json()
        text = next(b["text"] for b in data["content"] if b.get("type") == "text")
        result = TriageResult.model_validate_json(text)
    except Exception as exc:  # noqa: BLE001 -- degrade gracefully on any failure
        print(
            f"[triage] Claude call failed ({exc}); falling back to manual review.",
            file=sys.stderr,
        )
        return {}

    return {j.id: j.model_dump() for j in result.emails}
