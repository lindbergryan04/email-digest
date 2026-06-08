"""Command-line entry point for email-digest.

Kept import-light and side-effect-free so ``email-digest --help`` / ``--version``
run with no network access and no secrets. The real fetch/triage wiring lands
in later sections.
"""

from __future__ import annotations

import argparse

from email_digest import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="email-digest",
        description=(
            "Pull recent email from your configured Gmail accounts, triage it "
            "with Claude, and print a prioritized terminal digest."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    build_parser().parse_args(argv)
    print("email-digest: scaffold in place — fetch/triage wiring lands in upcoming commits.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
