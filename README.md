# Personal Morning News Agent

A local AI editor that delivers a concise, personalized intelligence briefing at
7:00 AM. It collects current reporting, ranks it for importance and personal
relevance, removes duplicate and previously sent stories, asks Gemini to make
the final editorial selection, and emails a source-linked digest.

## What It Does

- Covers global affairs, AI and technology, and India.
- Combines configurable RSS feeds with optional NewsAPI coverage.
- Uses a strict allowlist of established wire services and major publications;
  unknown and small-scale outlets are removed before AI analysis.
- Gives the strongest preference to Reuters, Associated Press, BBC, Financial
  Times, Bloomberg, The Hindu, The Indian Express, and Press Trust of India.
- Scores stories by freshness, source quality, impact, and your interests.
- Deduplicates the same event across publishers.
- Tracks independent corroboration and labels evidence confidence.
- Remembers sent stories for 14 days.
- Learns topics and sources you favor or dislike from explicit feedback.
- Produces an executive summary, connecting patterns, counterpoint, signal level,
  relevance, and what to watch next.
- Can scan for unusually important, multi-source breaking developments.
- Always includes original links and saves an HTML preview.
- Falls back to deterministic ranked summaries if Gemini is unavailable.
- Logs each run to `data/agent.log`.

## Setup

1. Install Python 3.11 or newer.
2. Install the dependency:

   ```powershell
   python -m pip install -r requirements.txt
   ```

   On Windows, `tzdata` supplies IANA timezone definitions. The agent also has
   a built-in India Standard Time fallback, so a missing timezone package will
   not abort delivery.

3. Copy `.env.example` to `.env` and add your keys. Gmail requires a Google App
   Password, not your normal account password. `NEWS_API_KEY` is optional.
   Without a Gemini key, the deterministic ranked fallback still delivers.
4. Edit `config.json`. Adding your name, occupation, interests, and priority
   topics materially improves the editorial choices.
5. Test without sending:

   ```powershell
   python main.py --dry-run --ignore-history
   ```

   Open `output/latest_digest.html` to inspect the final email.
6. Send a real test:

   ```powershell
   python main.py --ignore-history
   ```

## Schedule It For 7:00 AM

Run PowerShell:

```powershell
.\install_schedule.ps1
```

To also install conservative 30-minute breaking-news scans:

```powershell
.\install_schedule.ps1 -InstallAlerts
```

Alerts require both a high ranking score and at least two matching sources.

If Python is not on PATH:

```powershell
.\install_schedule.ps1 -PythonPath "C:\path\to\python.exe"
```

The Windows task uses the computer's local timezone. Keep Windows set to India
Standard Time if you want delivery at 7:00 AM IST. It is configured to wake the
computer, retry transient failures, and run after wake-up if the scheduled time
was missed. The computer must be powered on and have internet access.

## Useful Commands

```powershell
# Preview only
python main.py --dry-run

# Preview while ignoring the sent-story memory
python main.py --dry-run --ignore-history

# Inspect the scheduled task
Get-ScheduledTask -TaskName "Personal Morning News Agent"

# Run the scheduled task immediately
Start-ScheduledTask -TaskName "Personal Morning News Agent"

# Teach the ranking system
python main.py feedback --like-topic "AI agents"
python main.py feedback --dislike-topic "smartphone rumors"
python main.py feedback --trust-source "Reuters"
python main.py feedback --mute-source "Example Clickbait Site"

# Inspect learned preferences and operational state
python main.py status

# Test the high-priority alert detector without sending
python main.py alert-scan --dry-run
```

Secrets stay in `.env`; do not commit that file.

## Run In The Cloud With The PC Shut Down

The included GitHub Actions workflow runs on GitHub's servers every day at
7:00 AM in the `Asia/Kolkata` timezone. It restores the agent's sent-story
memory between runs and retains each preview and run log for seven days.

1. Create a new **private** empty repository on GitHub.
2. Push this folder:

   ```powershell
   .\setup_github_cloud.ps1 -RepositoryUrl "https://github.com/YOUR_NAME/YOUR_REPO.git"
   ```

3. In the repository, open **Settings > Secrets and variables > Actions** and
   create these repository secrets:

   - `GEMINI_API_KEY`
   - `GMAIL_ADDRESS`
   - `GMAIL_APP_PASSWORD`
   - `DIGEST_RECIPIENT`
   - `NEWS_API_KEY` (optional)

4. Open **Actions > Morning Intelligence > Run workflow**. Select `dry_run`
   for the first test. Download the generated artifact and inspect
   `latest_digest.html`.
5. Run it once without `dry_run` to verify email delivery.

After cloud delivery succeeds, remove the local task to avoid duplicate emails:

```powershell
Unregister-ScheduledTask -TaskName "Personal Morning News Agent" -Confirm:$false
```

GitHub may occasionally start scheduled workflows a few minutes after the
configured time. For stricter execution timing, deploy the same code as a
Google Cloud Run Job and trigger it with Cloud Scheduler.
