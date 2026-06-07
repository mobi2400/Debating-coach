# State persistence — how memory survives between scheduler runs

DebateIQ is an open-source project. Anyone can fork it, plug in their own topics, secrets, and run it on the free GitHub Actions tier. This doc explains how your *personal* study state is kept out of git history while still surviving across runs.

## The two stateful things

| Path | What it holds | How big |
|---|---|---|
| `faiss/` | Vector indexes built from your PDFs / sources | a few MB |
| `memory/weekly_log.json` | Your topics studied, quiz scores, distilled lessons | tens of KB |

Both are listed in `.gitignore`. Neither is ever committed to the repo.

## How they survive

The scheduler workflow ([`.github/workflows/scheduler.yml`](../.github/workflows/scheduler.yml)) uses **GitHub Actions cache** for both.

Each cache entry is:
- **Scoped to your fork** — your fork's cache is never readable by anyone else, including the upstream repo.
- **Kept for 7 days of inactivity** — a daily-running scheduler refreshes the cache every run, so in practice it never expires.
- **Up to 10 GB per repo** — far more than DebateIQ needs.

## Why we don't commit state back

An earlier version of the workflow had a `git commit` step that pushed `weekly_log.json` to `main` after every run. That worked but had two real problems for an open-source project:

1. **Your study history lived in public git history.** Topics, quiz scores, coaching prose, vocabulary — all readable.
2. **Forkers inherited that history.** Cloning the repo cloned someone else's diary.

Switching to Actions cache fixes both. The repo stays clean; each fork has its own private state.

## What happens on a fresh fork

| First run | Subsequent runs |
|---|---|
| FAISS cache miss → `rag/ingest.py` rebuilds the index (one-time embedding cost) | Cache hit → index loads instantly |
| `weekly_log.json` cache miss → empty log starts | Cache hit → previous days' memory restored |
| Night agent has nothing to quiz on | Night agent quizzes on today's daily output |

So you'll get one slow first run, then everything is fast and stateful.

## If you want longer-term persistence

Actions cache is fine for daily use but is not a database. If you want to keep state across, say, a six-month gap of inactivity:

- **Option A — store in a private second repo.** Add a secret `STATE_REPO_TOKEN` (a personal access token with `contents:write` on a private repo), then add a step at the end of the workflow that pushes `memory/weekly_log.json` to that private repo. The public repo stays clean.
- **Option B — use a free key-value store.** Upstash Redis has a generous free tier; the night agent could read/write the log there instead of using a local file.

We don't ship either path by default because Actions cache is enough for typical daily use, and both options need credentials beyond what a fresh fork has.

## Threat model in plain English

What an attacker who can read your fork can see: the code, your `topics.json`, and the workflow runs (job logs, not the actual digest). What they cannot see: secrets, cache entries, or any past digest content. Logs are sanitised in the workflow — the digest body is sent to Telegram, never printed.

That's the privacy story. Fork freely.
