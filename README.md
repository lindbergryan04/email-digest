# email-digest

`email-digest` pulls the last day's mail from your Gmail account(s), has Claude triage every message — importance, category, a one-line summary, whether it's an event, and whether there's free food — and prints a prioritized, color-coded digest to your terminal. It exists so a student drowning in school and recruiter email can see the handful of messages that actually need attention today instead of scrolling an entire inbox. It reads mail through the Gmail API (read-only) and never sends, marks, or deletes anything. It's built to run once each morning — automatically, when you first open your laptop (see [Automation](#automation-macos)) — so the day starts with a one-screen digest instead of a full inbox.

## Usage

Install it with `uv`:

```bash
uv add "git+https://github.com/lindbergryan04/email-digest.git"
# or run it without adding it to a project:
uvx --from "git+https://github.com/lindbergryan04/email-digest.git" email-digest --help
```

### One-time setup

Configuration lives in `~/.email-digest` (override the location with `EMAIL_DIGEST_HOME`):

1. Add your Anthropic API key:
   ```bash
   mkdir -p ~/.email-digest
   echo 'ANTHROPIC_API_KEY=sk-ant-...' > ~/.email-digest/.env
   ```
2. Download a **Desktop** OAuth client from the Google Cloud Console (with the Gmail API enabled) and save it as `~/.email-digest/credentials.json`.
3. Authorize each Gmail account once (opens a browser, stores a token locally):
   ```bash
   email-digest --authorize personal
   email-digest --authorize school
   ```

### Daily use

```bash
email-digest
```

Pulls everything since the last run (capped at 7 days), triages it, and prints the digest: an inbox section sorted by urgency, followed by an "upcoming events" section with free-food events starred (⭐).

Handy flags:

```bash
email-digest --accounts personal     # just one account
email-digest --lookback-hours 72     # force a 3-day window instead of "since last run"
email-digest --no-save               # don't advance the .last_run marker
```

`email-digest --help` lists every option and runs with no network access or credentials.

## How it prioritizes

Claude scores every message into one of four levels, and the digest shows them top-down:

- **Level 1 — Urgent:** things that need you *today* — direct internship/recruiter correspondence (interview invites, take-home assessments, offers, rejections) and time-sensitive academic deadlines, plus any urgent message from a real person.
- **Level 2 — Important:** real, personal messages from actual people — a friend, a professor or TA writing to you directly, family — along with campus safety alerts, financial-aid action items, and things you RSVP'd to.
- **Level 3 — FYI:** worth a skim but not pressing — course announcements, club and department events, networking invites.
- **Ignored (hidden):** the bulk of an inbox — newsletters, promotions, job-listing *digests* (LinkedIn/Handshake "new jobs for you"), surveys, receipts, and "finish your profile" nags. These are tallied at the bottom but not shown.

In short, it surfaces **real people and genuine internship correspondence first** and buries the automated noise. It deliberately errs toward hiding things — you'd rather miss a borderline FYI than scroll past thirty of them. Separately, anything that's an event you could attend is pulled into an **Upcoming events** list, and events that mention free food are starred (⭐) and floated to the top.

## Automation (macOS)

The digest is meant to greet you once a day, not to be run by hand. On macOS a small **LaunchAgent opens your digest in a fresh Ghostty window each morning** — at 8am, or the first time your laptop wakes after that — so it's the first thing you see when you sit down. It fires once a day, and the incremental window means it only ever shows mail you haven't seen yet.

Set it up once, from a clone of this repo:

```bash
bash automation/install.sh
```

That drops a small launcher into `~/.email-digest/`, installs the LaunchAgent, and loads it. Try it immediately with `launchctl start com.email-digest`. To remove it:

```bash
launchctl unload ~/Library/LaunchAgents/com.email-digest.plist && rm ~/Library/LaunchAgents/com.email-digest.plist
```

Prefer a different terminal or time? Edit [`automation/com.email-digest.plist`](automation/com.email-digest.plist) (swap `Ghostty.app`, or change the `StartCalendarInterval` hour) and re-run `install.sh`.

