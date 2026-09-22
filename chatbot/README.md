# Custom AI Chatbot with Memory — DecodeLabs Project 1

## Description

A Flask web app that talks to Gemini and remembers the conversation
within a browser session, by maintaining an in-memory list of
`{role, parts}` messages and resending that full list on every turn.

## How to Run

```bash
cd chatbot
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# then edit .env and paste in your GEMINI_API_KEY (get one at aistudio.google.com/apikey)

python app.py
```

Open http://127.0.0.1:5000 in your browser.

## How it maps to the assignment

| Requirement | Where it lives |
|---|---|
| Connect to a frontier LLM via official SDK | `client = genai.Client(api_key=...)` in `app.py`, using Google's `google-genai` Python SDK |
| In-memory list/array for conversation history | `SESSIONS` dict in `app.py` — one list per browser session |
| Append every user input + model response | `history.append(...)` calls in `/api/chat`, once before the API call (role `user`) and once after (role `model`) |
| Input validation gate | The `if not user_message:` check rejects empty/whitespace input with a 400, both server-side (`app.py`) and client-side (`script.js`) |
| Sliding window / token-budget protection | `prune_history()` — FIFO trims the oldest messages once history exceeds `MAX_HISTORY_MESSAGES` |
| Session state management | Flask's signed cookie session holds a `session_id`; the actual history stays server-side in RAM, keyed by that id |
| Resilience to transient API errors | `call_gemini_with_retry()` retries on 503/"UNAVAILABLE"/overloaded errors with exponential backoff before giving up |

**Note on the API:** the model's error responses (`'status': 'UNAVAILABLE'`) and the "role: user / model" schema in the assignment slides both match Google's Gemini API — so this project is built against `google-genai`, not Anthropic's SDK. If your class briefing mentioned a different provider, swap `client.models.generate_content(...)` in `app.py` for that provider's equivalent call; the surrounding history/validation/pruning logic stays the same either way.

Restarting the server clears everyone's history — that's expected for
this project's scope (in-memory only, no database). The slide deck's
Firestore/Postgres sections are about a *persistence* layer, which is
a natural "next step" beyond this project, not part of Project 1's
stated requirements.

## Testing the memory ("System Audit") scenario

This mirrors the exact test the training deck describes:

1. Send: `My name is Vipin` → expect a short acknowledgment.
2. Send: `Write a short poem about technology` → a longer, unrelated
   reply that pads out the history.
3. Send: `What is my name?` → Claude should correctly answer `Vipin`,
   proving it's reading the full history array, not just the latest
   message.

Watch the "messages in memory" counter in the header climb as you
chat, and hit **reset** to clear the session and start over.

## Possible extensions (optional, beyond the base requirement)

- Swap the in-memory dict for Postgres/Firestore so history survives
  a restart (see the deck's "Enterprise Scale" section).
- Show a running token-count estimate next to the message counter.
- Stream the response token-by-token instead of waiting for the full
  reply.
