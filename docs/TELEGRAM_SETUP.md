# Telegram bot setup

DebateIQ delivers digests through a Telegram bot. Free, unlimited, pull-based replies (no webhook).

## 1. Create the bot

1. Open Telegram, search for **@BotFather**.
2. Send these in order:
   ```
   /newbot
   DebateIQ
   DebateIQBot
   ```
3. BotFather replies with a token like `7123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`. Save it.

## 2. Get your chat id

1. In Telegram, search your new bot and send it any message (e.g. `hello`).
2. Open in a browser, swapping in the token:
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
3. Find `"chat": { "id": 123456789 }` in the JSON. That number is your chat id.

## 3. Local `.env`

```env
TELEGRAM_BOT_TOKEN=7123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TELEGRAM_CHAT_ID=123456789

GROQ_API_KEY=…
GOOGLE_API_KEY=…
TAVILY_API_KEY=…
```

Any old `TWILIO_*` or `WHATSAPP_*` variables can be removed.

## 4. GitHub Actions secrets

Repo → Settings → Secrets → Actions. Add:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

The scheduler workflow reads both.

## 5. Test locally

```bash
python -c "from delivery.telegram import send_message, wait_for_reply; \
send_message('DebateIQ connected. Reply within 2 minutes to test.'); \
print('Reply:', wait_for_reply(2))"
```

You should see the message on your phone within a second. Reply to the bot and the script should print what you typed.

## 6. Two-way replies — how the night agent works

The Telegram Bot API has a `get_updates` pull endpoint that returns new messages on demand. The night agent simply asks every ~10 seconds whether you've replied yet, up to its timeout. No webhook server is needed — this works fine on a stateless GitHub Actions runner.

If you don't reply within the window, `wait_for_reply()` returns `"no"` and the agent falls into bedtime mode.

## 7. Limits

| | Telegram |
|---|---|
| Messages / day | unlimited |
| Conversations | unlimited |
| Rate limit (personal bot) | ~30 messages/second |
| Token expiry | never |
| Verified recipient list | not required |
