"""Render triaged emails into a prioritized, color-coded terminal digest.

``organize_digest`` is pure selection/sorting logic (easy to test); ``format_digest``
renders it with ANSI color. ``now`` is injected so the header is deterministic.
"""

from __future__ import annotations

from datetime import datetime

from email_digest.timewindow import format_hours

_IMPORTANCE_ORDER = {"high": 0, "medium": 1, "low": 2}
_SHOWN = ("high", "medium", "low")


class C:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    END = "\033[0m"


LEVEL_INFO = {
    "high": ("LEVEL 1 -- URGENT", C.RED + C.BOLD),
    "medium": ("LEVEL 2 -- IMPORTANT", C.YELLOW),
    "low": ("LEVEL 3 -- FYI", C.DIM),
}

CATEGORY_TAG = {
    "internship": f"{C.MAGENTA}[internship]{C.END}",
    "human": f"{C.BLUE}[personal]{C.END}",
    "school": f"{C.CYAN}[school]{C.END}",
    "other": f"{C.DIM}[other]{C.END}",
}


def organize_digest(triaged):
    """Split ``(email, judgment)`` pairs into sorted inbox items, sorted events,
    and the count of ignored emails. Pure -- no rendering."""
    shown = [(e, j) for e, j in triaged if j["importance"] in _SHOWN]
    inbox_items = [(e, j) for e, j in shown if not j.get("is_event", False)]
    events = [(e, j) for e, j in shown if j.get("is_event", False)]
    ignored_count = sum(1 for _, j in triaged if j["importance"] == "ignore")

    inbox_items.sort(key=lambda x: _IMPORTANCE_ORDER[x[1]["importance"]])
    events.sort(
        key=lambda x: (
            0 if x[1].get("has_free_food", False) else 1,
            _IMPORTANCE_ORDER[x[1]["importance"]],
        )
    )
    return inbox_items, events, ignored_count


def format_digest(triaged, lookback_hours: float, now: datetime) -> str:
    """Render the full digest string (with ANSI color)."""
    window = format_hours(lookback_hours)
    when = now.strftime("%A, %B %d, %Y -- %I:%M %p")
    header = f"Email digest -- {when}  (last {window})"
    out = [
        f"{C.BOLD}{C.CYAN}{'=' * 60}{C.END}",
        f"{C.BOLD}{C.CYAN}{header}{C.END}",
        f"{C.BOLD}{C.CYAN}{'=' * 60}{C.END}",
        "",
    ]

    inbox_items, events, ignored_count = organize_digest(triaged)

    if not inbox_items and not events:
        out.append(f"  {C.GREEN}Nothing important in the last {window}.{C.END}")
        if ignored_count:
            out.append(f"  {C.DIM}({ignored_count} newsletter(s)/promo(s) ignored){C.END}")
        return "\n".join(out)

    if inbox_items:
        current = None
        item_num = 0
        for email, j in inbox_items:
            if j["importance"] != current:
                current = j["importance"]
                item_num = 0
                label, color = LEVEL_INFO[current]
                out.append(f"{color}--- {label} ---{C.END}")
                out.append("")
            item_num += 1
            _, color = LEVEL_INFO[j["importance"]]
            out.append(f"{color}{item_num}.{C.END} {C.BOLD}{email['subject'][:65]}{C.END}")
            out.append(f"   from {email['from'][:50]}  ({email['account']}) {CATEGORY_TAG[j['category']]}")
            out.append(f"   {C.DIM}-> {j['summary']}{C.END}")
            out.append("")

    if events:
        out.append(f"{C.MAGENTA}{C.BOLD}--- UPCOMING EVENTS ---{C.END}")
        out.append("")
        for i, (email, j) in enumerate(events, start=1):
            has_food = j.get("has_free_food", False)
            marker = f"{C.YELLOW}⭐{C.END}" if has_food else " "
            summary_color = C.YELLOW + C.BOLD if has_food else C.DIM
            out.append(f"{marker} {C.BOLD}{i}. {email['subject'][:60]}{C.END}")
            out.append(f"     from {email['from'][:50]}  ({email['account']}) {CATEGORY_TAG[j['category']]}")
            out.append(f"     {summary_color}-> {j['summary']}{C.END}")
            out.append("")

    if ignored_count:
        out.append(f"{C.DIM}({ignored_count} newsletter(s)/promo(s) ignored){C.END}")
    return "\n".join(out)
