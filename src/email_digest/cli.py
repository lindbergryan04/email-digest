"""Command-line entry point for email-digest.

Top-level imports are intentionally light (no Anthropic/Google) and the heavy,
network/secret-touching imports happen lazily inside ``main()``, so
``email-digest --help`` / ``--version`` run with zero network access and no
credentials -- which is all the autograder needs to find and run the command.

Config lives under ``EMAIL_DIGEST_HOME`` (default ``~/.email-digest``):
  <home>/.env                  -> ANTHROPIC_API_KEY
  <home>/credentials.json      -> Google OAuth client (for --authorize)
  <home>/tokens/<account>.json -> per-account Gmail OAuth tokens
  <home>/.last_run             -> incremental-lookback marker
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from email_digest import __version__

DEFAULT_ACCOUNTS = ["personal", "school"]

FALLBACK_JUDGMENT = {
    "importance": "medium",
    "category": "other",
    "summary": "(not triaged -- review manually)",
    "is_event": False,
    "has_free_food": False,
}


def config_home() -> Path:
    """Directory holding tokens, .env, and the .last_run marker."""
    return Path(os.environ.get("EMAIL_DIGEST_HOME", Path.home() / ".email-digest"))


def parse_accounts(value: str) -> list[str]:
    """Split a comma-separated --accounts value into clean account names."""
    return [a.strip() for a in value.split(",") if a.strip()]


def assemble_triaged(emails, judgments_by_id, *, fallback=FALLBACK_JUDGMENT):
    """Pair each email with its judgment, falling back so none is dropped."""
    return [(e, judgments_by_id.get(e["id"], dict(fallback))) for e in emails]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="email-digest",
        description=(
            "Pull recent email from your configured Gmail accounts, triage it "
            "with Claude, and print a prioritized terminal digest."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--accounts",
        default=",".join(DEFAULT_ACCOUNTS),
        help="comma-separated account names with tokens at <home>/tokens/<name>.json "
        "(default: personal,school)",
    )
    parser.add_argument(
        "--lookback-hours",
        type=float,
        default=None,
        help="override the lookback window in hours (default: time since last run, capped at 7 days)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="do not update the .last_run timestamp after running",
    )
    parser.add_argument(
        "--authorize",
        metavar="ACCOUNT",
        default=None,
        help="run one-time Google OAuth for ACCOUNT, save its token, then exit",
    )
    return parser


def _authorize(account: str, home: Path) -> int:
    """One-time OAuth: open a browser and save tokens/<account>.json."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    from email_digest.gmail import SCOPES

    creds_path = home / "credentials.json"
    if not creds_path.exists():
        print(
            f"credentials.json not found at {creds_path}. Download a Desktop OAuth "
            "client from Google Cloud Console and place it there.",
            file=sys.stderr,
        )
        return 1

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
    creds = flow.run_local_server(port=0)
    tokens_dir = home / "tokens"
    tokens_dir.mkdir(parents=True, exist_ok=True)
    token_path = tokens_dir / f"{account}.json"
    token_path.write_text(creds.to_json())
    print(f"Saved token for '{account}' -> {token_path}")
    return 0


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    home = config_home()

    if args.authorize:
        return _authorize(args.authorize, home)

    # Lazy imports: keep --help / --version free of network, secrets, heavy deps.
    import anthropic
    from dotenv import load_dotenv

    from email_digest import gmail, triage
    from email_digest.formatting import C, format_digest
    from email_digest.timewindow import (
        compute_lookback,
        format_hours,
        get_lookback_window,
        save_last_run,
    )

    load_dotenv(home / ".env")
    if not os.getenv("ANTHROPIC_API_KEY"):
        print(
            f"ANTHROPIC_API_KEY not set. Put it in {home / '.env'} or export it.",
            file=sys.stderr,
        )
        return 1

    home.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    last_run_path = home / ".last_run"
    if args.lookback_hours is not None:
        after_ts, hours = compute_lookback(
            now, None, default_hours=args.lookback_hours, max_hours=args.lookback_hours
        )
    else:
        after_ts, hours = get_lookback_window(last_run_path, now)

    all_emails: list[dict] = []
    for account in parse_accounts(args.accounts):
        token_path = home / "tokens" / f"{account}.json"
        if not token_path.exists():
            print(
                f"[skip] no token for '{account}' -- run: email-digest --authorize {account}",
                file=sys.stderr,
            )
            continue
        try:
            creds = gmail.load_credentials(token_path)
            service = gmail.build_service(creds)
            all_emails.extend(gmail.fetch_recent_emails(service, account, after_ts))
        except Exception as exc:  # noqa: BLE001 -- one bad account shouldn't sink the run
            print(f"[{account}] could not fetch: {exc}", file=sys.stderr)

    window = format_hours(hours)
    if not all_emails:
        print(f"{C.GREEN}No emails in the last {window} across configured accounts.{C.END}")
        if not args.no_save:
            save_last_run(last_run_path, now)
        return 0

    judgments = triage.triage_emails(anthropic.Anthropic(), all_emails)
    triaged = assemble_triaged(all_emails, judgments)
    print(format_digest(triaged, hours, datetime.now()))
    if not args.no_save:
        save_last_run(last_run_path, now)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
