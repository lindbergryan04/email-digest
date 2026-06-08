# email-digest

`email-digest` pulls the last day's mail from your Gmail account(s), has Claude triage every message — importance, category, a one-line summary, whether it's an event, and whether there's free food — and prints a prioritized, color-coded digest to your terminal. It exists so a student drowning in school and recruiter email can see the handful of messages that actually need attention today instead of scrolling an entire inbox. It reads mail through the Gmail API (read-only) and never sends, marks, or deletes anything.

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
