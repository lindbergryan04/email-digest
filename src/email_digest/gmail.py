"""Fetch recent inbox email via the Gmail API.

``build_query`` and ``fetch_recent_emails`` are unit-tested against a mocked
service. Credential loading and service building are the impure edges (token
files + network) and import the Google libraries lazily, so importing this
module -- and running ``--help`` -- needs no credentials or network.

The fetch is deliberately resilient: a failed listing returns ``[]`` and a
single message that fails to load or parse is skipped, so one bad email can't
sink the whole digest.
"""

from __future__ import annotations

import sys
from pathlib import Path

from email_digest.parsing import parse_message

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
MAX_EMAILS_PER_ACCOUNT = 100


def build_query(after_ts: int) -> str:
    """Gmail search query for inbox messages newer than a unix timestamp."""
    return f"after:{after_ts} in:inbox"


def fetch_recent_emails(
    service,
    account: str,
    after_ts: int,
    *,
    max_results: int = MAX_EMAILS_PER_ACCOUNT,
) -> list[dict]:
    """Return parsed emails newer than ``after_ts`` for one account."""
    messages_api = service.users().messages()
    try:
        resp = messages_api.list(
            userId="me", q=build_query(after_ts), maxResults=max_results
        ).execute()
    except Exception as exc:  # noqa: BLE001 -- never let a listing error crash the run
        print(f"[{account}] Gmail list failed: {exc}", file=sys.stderr)
        return []

    emails: list[dict] = []
    for m in resp.get("messages", []):
        mid = m["id"]
        try:
            msg = messages_api.get(userId="me", id=mid, format="full").execute()
            emails.append(parse_message(msg, account))
        except Exception as exc:  # noqa: BLE001 -- skip a single bad message, keep going
            print(f"[{account}] skipped message {mid}: {exc}", file=sys.stderr)
            continue
    return emails


def load_credentials(token_path: Path):
    """Load OAuth credentials from a token file, refreshing if expired."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        Path(token_path).write_text(creds.to_json())
    return creds


def build_service(creds):
    """Build a read-only Gmail API service client from credentials."""
    from googleapiclient.discovery import build

    return build("gmail", "v1", credentials=creds, cache_discovery=False)
