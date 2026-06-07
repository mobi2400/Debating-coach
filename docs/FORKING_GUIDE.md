# Forking guide

The complete walkthrough for taking this project, pointing it at your subjects, and running it on autopilot — every step from "click Fork" to "messages arriving on my phone every morning."

> **No coding background?** You can complete this guide by editing two text files, uploading a few PDFs, and pasting five secrets. The hardest part is patience on the first scheduler run.

---

## Table of contents

1. [The 30-second mental model](#1-the-30-second-mental-model)
2. [Five things you need before you start](#2-five-things-you-need-before-you-start)
3. [Fork the repo](#3-fork-the-repo)
4. [Create your Telegram bot](#4-create-your-telegram-bot)
5. [Get the three API keys](#5-get-the-three-api-keys)
6. [Local setup (optional but recommended)](#6-local-setup-optional-but-recommended)
7. [Rewrite `topics.json` for your subjects](#7-rewrite-topicsjson-for-your-subjects)
8. [Add your own PDFs to the RAG knowledge base](#8-add-your-own-pdfs-to-the-rag-knowledge-base)
9. [Build the FAISS index](#9-build-the-faiss-index)
10. [Test it locally](#10-test-it-locally)
11. [Add the five secrets to your fork on GitHub](#11-add-the-five-secrets-to-your-fork-on-github)
12. [Adjust the schedule for your timezone](#12-adjust-the-schedule-for-your-timezone)
13. [Enable Actions and run your first scheduled job](#13-enable-actions-and-run-your-first-scheduled-job)
14. [Customising further](#14-customising-further)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. The 30-second mental model

DebateIQ wakes up, picks one of your priority subjects for today, researches it from the web and from your own PDFs, builds a structured lesson, and delivers it on Telegram. The night after, it quizzes you. On Sunday, it distils the week.

What you control as a forker:
- **`topics.json`** — the subjects it rotates through.
- **`knowledge_base/pdfs/`** + **`rag/sources.json`** — your private study material that gets mixed into every lesson.
- **`.github/workflows/scheduler.yml`** — when the messages arrive.

Everything else (the LLMs, the retrieval logic, the formatting) works out of the box.

---

## 2. Five things you need before you start

| Item | Cost | Where to get it |
|---|---|---|
| GitHub account | Free | https://github.com |
| Telegram account | Free | The Telegram app |
| Groq API key | Free tier | https://console.groq.com |
| Google AI Studio API key (Gemini) | Free tier | https://aistudio.google.com/app/apikey |
| Tavily API key | Free tier (1000 searches / month) | https://tavily.com |

That's it. No credit card, no hosting, no server.

---

## 3. Fork the repo

1. Open the project on GitHub.
2. Click **Fork** in the top-right corner.
3. Pick your account as the destination. Leave the rest as defaults.

You now have your own copy at `https://github.com/<your-username>/Debating-coach`. Every change you make from here on goes into your fork. The upstream repo never sees your data.

---

## 4. Create your Telegram bot

Detailed walkthrough lives in **[TELEGRAM_SETUP.md](TELEGRAM_SETUP.md)** — the short version:

1. Search **@BotFather** in Telegram. Send `/newbot`. Pick a name and a username ending in `bot`.
2. BotFather replies with a token like `7123456789:AAFxxxx…`. Save it as your `TELEGRAM_BOT_TOKEN`.
3. Send your new bot any message (e.g. `hello`). Open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser. Find `"chat":{"id":123456789}` — that number is your `TELEGRAM_CHAT_ID`.

You only do this once.

---

## 5. Get the three API keys

### Groq
1. Sign up at https://console.groq.com.
2. **API Keys → Create API Key.** Copy the value — Groq shows it only once.

### Google AI Studio (Gemini)
1. Visit https://aistudio.google.com/app/apikey.
2. **Create API key** → choose any Google Cloud project (a default one is fine).
3. Copy the key.

### Tavily
1. Sign up at https://tavily.com.
2. Dashboard → copy the API key shown there.

Save all three somewhere safe. You'll paste them as repo secrets in step 11.

---

## 6. Local setup (optional but recommended)

You can run everything from GitHub Actions without ever touching a terminal — but a quick local test catches misconfigurations in minutes instead of waiting for the next cron tick.

```bash
# 1. Clone your fork
git clone https://github.com/<your-username>/Debating-coach.git
cd Debating-coach

# 2. Install uv (a fast Python package manager) once on your machine
# Windows (PowerShell):
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
# macOS / Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Install the project
uv pip install --system -r requirements.txt

# 4. Create a .env file at the repo root with your secrets
cat > .env <<'ENVEOF'
TELEGRAM_BOT_TOKEN=7123456789:AAFxxxx…
TELEGRAM_CHAT_ID=123456789
GROQ_API_KEY=gsk_xxxx…
GOOGLE_API_KEY=AIzaSyxxxx…
TAVILY_API_KEY=tvly-xxxx…
ENVEOF
```

The `.env` file is in `.gitignore` so it never gets committed.

---

## 7. Rewrite `topics.json` for your subjects

This is where the project becomes yours. `topics.json` has three top-level keys:

```jsonc
{
  "study_scope": "...",          // one sentence describing what you're studying
  "selection_lens": { ... },     // optional — taste rules the LLM uses to filter articles
  "priority_topics": [ ... ]     // the list the scheduler rotates through
}
```

### The shape of one topic

Each entry in `priority_topics` looks like this:

```jsonc
{
  "topic": "constitutional law",
  "keywords": ["Article 19", "fundamental rights", "judicial review"],
  "debate_frames": [
    "individual rights vs collective good",
    "strict construction vs living document"
  ],
  "essential_theoretical_frameworks": [
    "Wednesbury reasonableness",
    "proportionality doctrine"
  ],
  "key_concepts_own_these_precisely": [
    "basic structure doctrine",
    "manifest arbitrariness"
  ],
  "live_cases": ["Kesavananda Bharati", "Puttaswamy"],
  "why_this_matters_for_debate": "Most policy clashes terminate in a constitutional question."
}
```

You don't need every field. The minimum that works is `topic` and `keywords`. Everything else makes the lesson richer.

### Examples for different subjects

The repo ships with debate topics, but the architecture is subject-agnostic. Here are sketches for other domains:

<details>
<summary><b>Medical student preparing for USMLE / NEET-PG</b></summary>

```jsonc
{
  "study_scope": "Daily revision for clinical medicine exams.",
  "priority_topics": [
    {
      "topic": "cardiology",
      "keywords": ["myocardial infarction", "heart failure", "arrhythmia"],
      "essential_theoretical_frameworks": ["Frank-Starling", "preload/afterload"],
      "key_concepts_own_these_precisely": ["ejection fraction", "STEMI vs NSTEMI"],
      "why_this_matters_for_debate": "High-yield, frequently tested across step exams."
    },
    { "topic": "endocrinology", "keywords": ["diabetes", "thyroid", "adrenal"] },
    { "topic": "pharmacology", "keywords": ["beta blockers", "anticoagulants"] }
  ]
}
```

</details>

<details>
<summary><b>UPSC / Civil services aspirant</b></summary>

```jsonc
{
  "study_scope": "Daily current-affairs anchored to GS Mains syllabus.",
  "priority_topics": [
    { "topic": "indian economy", "keywords": ["RBI", "monetary policy", "fiscal deficit"] },
    { "topic": "international relations", "keywords": ["India-China", "QUAD", "SAARC"] },
    { "topic": "indian polity", "keywords": ["constitutional amendment", "federalism"] }
  ]
}
```

</details>

<details>
<summary><b>Software engineer preparing for system-design interviews</b></summary>

```jsonc
{
  "study_scope": "One canonical system-design topic per day, deep.",
  "priority_topics": [
    { "topic": "distributed caching", "keywords": ["Redis", "consistent hashing", "TTL"] },
    { "topic": "consensus protocols", "keywords": ["Raft", "Paxos", "split-brain"] },
    { "topic": "database scaling", "keywords": ["sharding", "read replicas"] }
  ]
}
```

</details>

Save your edits. Commit and push.

---

## 8. Add your own PDFs to the RAG knowledge base

The RAG (retrieval-augmented generation) layer is what makes the lesson *personal* — it mixes your private study material into the prompt. There are three lanes:

| Folder | What goes here |
|---|---|
| `knowledge_base/pdfs/topic_pdfs/` | Subject-specific PDFs (your textbooks, notes, reference material) |
| `knowledge_base/pdfs/debate_frameworks/` | Methodology PDFs (study technique, exam frameworks) |
| `knowledge_base/pdfs/your_past_speeches/` | Optional — anything that captures *your* style (essays, presentations) |

After dropping PDFs into those folders, register them in **`rag/sources.json`**:

```json
{
  "pdfs": [
    { "path": "knowledge_base/pdfs/topic_pdfs/your_textbook.pdf",        "doc_type": "topic_pdf" },
    { "path": "knowledge_base/pdfs/debate_frameworks/exam_strategy.pdf", "doc_type": "debate_format" }
  ],
  "websites": [
    { "url": "https://your-trusted-source.com", "site_type": "news" }
  ],
  "youtube": [
    { "channel_url": "https://www.youtube.com/@your-favourite-channel", "channel_type": "youtube_debate" }
  ]
}
```

### Which `doc_type` to use

| `doc_type` value | Routes to | Use for |
|---|---|---|
| `topic_pdf` | `knowledge_db` | Subject PDFs — chapter notes, textbooks, syllabus material |
| `debate_format` | `style_db` | Methodology PDFs — how to think about the field |
| `english_vocab` | `english_db` | A vocabulary book (we use *Word Power Made Easy*; you can use anything similar) |
| `your_speech` | `style_db` | Your past essays or written work — used to match *your voice* |
| `debate_theory` | `reasoning_db` | Theoretical or analytical books that inform argument structure |

You don't have to use every lane. A pure subject revision setup might only have `topic_pdf` entries.

---

## 9. Build the FAISS index

This step turns your PDFs into searchable vectors. It runs once locally; after that, GitHub Actions caches the result.

```bash
# Build everything in sources.json
python rag/ingest.py

# Or just one lane
python rag/ingest.py --only topic_pdf
python rag/ingest.py --only english_vocab
```

What happens under the hood:
1. Each PDF gets split into chunks (different chunk sizes per `doc_type`).
2. Each chunk gets embedded by Gemini's `gemini-embedding-001` model.
3. The embeddings get saved to `faiss/<store_name>/index.faiss` and `index.pkl`.

Expect a few minutes for the first build. The free Gemini tier handles ~1000 chunks; if you have a huge corpus, run the script multiple times across days or upgrade Gemini.

> **Don't commit `faiss/` to your repo.** It's in `.gitignore` for a reason. GitHub Actions will rebuild it from the same source files on its first run, then cache it forever.

---

## 10. Test it locally

```bash
# Just send a "hello" through Telegram to confirm wiring
python -c "from delivery.telegram import send_message; send_message('Fork is alive.')"

# Run the full daily pipeline against one topic
python main.py --mode daily --topic "your topic here"

# Run the night agent (sends the check-in, waits for your reply)
python main.py --mode night

# Run the weekend distillation
python main.py --mode weekend
```

If a message arrives in your Telegram chat, the wiring works. If `main.py --mode daily` finishes and you receive a multi-section digest, you're done.

> If anything errors, jump to [Troubleshooting](#15-troubleshooting). Common causes: wrong `.env` value, missing PDFs in `knowledge_base/`, exhausted Groq daily quota.

---

## 11. Add the five secrets to your fork on GitHub

On your fork's page:

1. **Settings → Secrets and variables → Actions → New repository secret.**
2. Add each of these one by one with **exactly** the names below:

   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `GROQ_API_KEY`
   - `GOOGLE_API_KEY`
   - `TAVILY_API_KEY`

GitHub encrypts these. They're available to workflows as environment variables and never appear in logs.

---

## 12. Adjust the schedule for your timezone

The shipped schedule is tuned for IST. Open **`.github/workflows/scheduler.yml`** and edit the three cron lines:

```yaml
schedule:
  - cron: "30 2 * * 1-5"   # 08:00 IST  (UTC+5:30)  weekdays - daily
  - cron: "0 17 * * 1-5"   # 22:30 IST                weekdays - night
  - cron: "30 3 * * 0"     # 09:00 IST                Sunday   - weekend
```

GitHub Actions uses **UTC**. Translate your local times to UTC and write them in `minute hour day-of-month month day-of-week` order. https://crontab.guru is the easiest visualiser.

| Mode | Suggested time | Example for US Pacific (UTC-8) |
|---|---|---|
| Daily | 07:00 local | `0 15 * * 1-5` |
| Night | 22:00 local | `0 6 * * 2-6` (next-day UTC) |
| Weekend | Sun 09:00 local | `0 17 * * 0` |

Commit the change. The new schedule takes effect on the next push.

---

## 13. Enable Actions and run your first scheduled job

On a fresh fork, GitHub disables workflows by default as a safety measure.

1. **Go to the Actions tab** on your fork. You'll see a prompt to enable workflows. Click it.
2. **Manually trigger a test run:** Actions → **DebateIQ Scheduler** → **Run workflow** → pick `daily` → **Run workflow**.
3. Watch the run. The first run is slow (~5 min) because it builds the FAISS cache from your PDFs. Every run after that is ~30 seconds before the LLM work starts.
4. If the workflow goes green and a message arrives on Telegram, you're live.

From now on the cron triggers fire automatically.

---

## 14. Customising further

### Change the digest layout

[`agents/format_node.py`](../agents/format_node.py) builds the nine-section digest. Add a section, remove one, rename one — just remember to also update [`delivery/telegram.py`](../delivery/telegram.py) `SECTION_TITLES` so the splitter knows about the new heading.

### Tighten or relax the article-quality filter

[`agents/rank_node.py`](../agents/rank_node.py) has `NEWS_DOMAIN_HINTS` (publishers we boost) and `REFERENCE_DOMAINS` (encyclopedias we demote). Add your preferred sources to the boost list.

### Adjust LLM costs

[`core/llm_pool.py`](../core/llm_pool.py) is the only file where models are instantiated. The role keys (`fast`, `balanced`, `structured`, `reasoning`, `long_ctx`, `best`) are stable — only the model strings change. Swap to cheaper models if you run out of free-tier quota.

### Add a new research tool

Drop a file in [`tools/`](../tools/) that exports a function returning `list[dict]` with keys `title, url, content, source, published`. Then call it from [`agents/research_node.py`](../agents/research_node.py) inside the `ThreadPoolExecutor`.

### Change prompts

Every agent file has the prompt string inline near its `def *_node` function. Edit, commit, push — the next run uses your new prompt.

---

## 15. Troubleshooting

### "I'm not getting any Telegram message"
- Did you start a chat with your bot first? Telegram won't deliver to a chat that has never opened.
- Are `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` set correctly in repo secrets? `TELEGRAM_CHAT_ID` is a number, no quotes.
- Open the failed Actions run and read the **Run DebateIQ** step's logs.

### "The workflow run is green but the digest is mostly placeholder text"
- Your Groq daily token quota is exhausted. Wait for the reset or upgrade.
- Check your fork's Actions logs for `429` errors. The fallback heuristics kicked in.

### "FAISS rebuild is taking forever / failing"
- Gemini's free embedding tier is rate-limited. The ingest script has built-in backoff, but a huge corpus might need a second run.
- Try `python rag/ingest.py --only one_doc_type` to isolate the slow lane.

### "Cron isn't firing"
- GitHub disables scheduled workflows on repos with **no recent activity** (60 days). Push any commit to wake it up.
- Confirm your cron lines are in UTC, not your local time.

### "I made code changes locally and now tests fail"
```bash
DEV_MODE=true DEBATEIQ_PROMPT_CACHE=0 python tests/test_router.py
DEV_MODE=true DEBATEIQ_PROMPT_CACHE=0 python tests/test_daily_e2e.py
```
These exercise the full graph against fake LLMs and stubbed tools. Green here means the wiring is intact.

### Something else?
Open an issue on the upstream repo with: what mode you ran, the full Actions log of the failing step, and which model lane was active. Most problems are quota, missing secrets, or stale cache — easy to fix once we can see the symptom.

---

## What forking does NOT do

- **It does not share your study history.** Your `weekly_log.json` lives in your fork's GitHub Actions cache (private, not visible to anyone with read access to your repo).
- **It does not share your secrets.** Repo secrets are encrypted and scoped to your fork.
- **It does not change the upstream repo.** You can experiment freely; the original is untouched.

See [STATE_PERSISTENCE.md](STATE_PERSISTENCE.md) for the full privacy model.

---

Happy forking. If you build something cool with this and want to share — open a PR adding your `topics.json` template under `docs/topic_recipes/` for others to learn from.
