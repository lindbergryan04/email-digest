"""Parse Gmail API message payloads into flat dicts, and extract readable text.

All pure: these operate on the dict structures the Gmail API returns, so they're
tested with synthetic message fixtures -- no network, no real mail.
"""

from __future__ import annotations

import base64
import re

BODY_TRUNCATE_CHARS = 1500


def parse_message(msg: dict, account: str) -> dict:
    """Flatten a Gmail ``messages.get`` payload into the fields we use."""
    headers = {
        h["name"].lower(): h["value"]
        for h in msg.get("payload", {}).get("headers", [])
    }
    return {
        "account": account,
        "id": msg["id"],
        "thread_id": msg["threadId"],
        "from": headers.get("from", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
        "snippet": msg.get("snippet", ""),
        "body": extract_body(msg.get("payload", {}))[:BODY_TRUNCATE_CHARS],
    }


def extract_body(payload: dict) -> str:
    """Walk MIME parts; prefer text/plain, fall back to stripped text/html."""
    mime = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")

    if mime == "text/plain" and body_data:
        return decode_base64url(body_data)

    parts = payload.get("parts", [])
    for p in parts:
        if p.get("mimeType") == "text/plain":
            data = p.get("body", {}).get("data")
            if data:
                return decode_base64url(data)

    for p in parts:
        if "parts" in p:
            nested = extract_body(p)
            if nested:
                return nested

    if mime == "text/html" and body_data:
        return strip_html(decode_base64url(body_data))
    for p in parts:
        if p.get("mimeType") == "text/html":
            data = p.get("body", {}).get("data")
            if data:
                return strip_html(decode_base64url(data))

    return ""


def decode_base64url(data: str) -> str:
    """Decode Gmail's URL-safe base64 body data to text."""
    return base64.urlsafe_b64decode(data.encode("ascii")).decode("utf-8", errors="replace")


def strip_html(html: str) -> str:
    """Crudely strip HTML to readable text: drop script/style, tags, collapse ws."""
    text = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
