# Meta WhatsApp Cloud API setup

DebateIQ uses the Meta WhatsApp Cloud API (free tier: 1000 conversations / month, no SMS confusion).

## 1. Create a Meta app

1. https://developers.facebook.com → log in → Create App.
2. App type: **Business**. Name it anything (e.g. `DebateIQ`).
3. From the app dashboard → "Add Products" → find **WhatsApp** → "Set Up".

## 2. Get credentials

The WhatsApp setup screen gives you:
- **Phone Number ID** — Meta's test number (free).
- **WhatsApp Business Account ID** (informational).
- **Temporary access token** — expires in 24 hours.

For a permanent token (do this once):
1. Meta Business Suite → **Business Settings → Users → System Users**.
2. Create a system user, then **Generate Token**.
3. Permission: `whatsapp_business_messaging`.
4. No expiry. Copy it.

## 3. Verify your personal number

While on the free tier, Meta only delivers to numbers you pre-verify.
- WhatsApp → API Setup → **To** field → add your personal number.
- Enter the verification code you receive on WhatsApp.

You can add up to 5 verified recipients.

## 4. Local `.env`

```env
WHATSAPP_TOKEN=EAA…your_permanent_system_user_token…
WHATSAPP_PHONE_NUMBER_ID=123456789012345
YOUR_WHATSAPP_NUMBER=91XXXXXXXXXX

GROQ_API_KEY=…
GOOGLE_API_KEY=…
TAVILY_API_KEY=…
```

`YOUR_WHATSAPP_NUMBER` format: country code + number, **no `+`, no spaces**.

## 5. GitHub Actions secrets

Add the same three secrets (`WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `YOUR_WHATSAPP_NUMBER`) to the repo at `Settings → Secrets → Actions`. The scheduler workflow already reads them.

## 6. Two-way replies (night quiz)

Meta Cloud API has no "list incoming messages" endpoint — it only pushes via webhook. There are three usable strategies:

### Option A — skip replies (simplest)
Do nothing. `wait_for_reply()` times out and the night agent falls into bedtime mode every night. You still get the digest and bedtime recap, you just don't get the interactive quiz.

### Option B — Render free-tier webhook (recommended)
Deploy `webhook_server.py` (template below) on Render.com's free tier. Point Meta's WhatsApp webhook at `https://your-app.onrender.com/webhook`. The server writes each incoming user reply into `memory/reply_flag.txt`, which `wait_for_reply()` polls.

```python
# webhook_server.py — drop on Render (free tier).
from flask import Flask, request
from pathlib import Path
import os

app = Flask(__name__)
VERIFY_TOKEN = os.environ["WHATSAPP_VERIFY_TOKEN"]
FLAG = Path("/tmp/reply_flag.txt")  # adjust to your shared store

@app.get("/webhook")
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Forbidden", 403

@app.post("/webhook")
def receive():
    try:
        msg = request.json["entry"][0]["changes"][0]["value"]["messages"][0]
        FLAG.write_text(msg["text"]["body"])
    except Exception:
        pass
    return "OK", 200
```

For this to work with the scheduled run, the webhook needs to write the flag file into the same location the GH Actions runner will read. The simplest pattern: have the webhook commit the flag back to the repo (or use a free Redis like Upstash + a small `get_reply()` helper).

### Option C — manual flag
For testing, set `memory/reply_flag.txt` manually before the scheduled night run. Whatever text it contains will be treated as the user's reply.

## 7. Free-tier limits to know

| | |
|---|---|
| Conversations / month | 1000 |
| Messages / conversation | unlimited (one 24h window per recipient) |
| Verified recipients | up to 5 |
| Rate limit | 80 messages / second |

A daily digest + night ping + weekend brain dump uses ~3 conversations per recipient per week — well under the free cap.
