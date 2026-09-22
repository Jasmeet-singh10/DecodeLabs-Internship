import os
import random
import time
import uuid

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session
from google import genai

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

MODEL = "gemini-3.6-flash"

MAX_HISTORY_MESSAGES = 20

RETRYABLE_MARKERS = ("503", "UNAVAILABLE", "overloaded", "high demand")
MAX_RETRIES = 3
BASE_DELAY_SECONDS = 1.5


def call_gemini_with_retry(history):
    """Call the API, retrying with exponential backoff on transient
    'server overloaded' errors. Re-raises immediately on anything else
    (bad request, auth failure, etc.) since retrying those won't help."""
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            return client.models.generate_content(model=MODEL, contents=history)
        except Exception as exc:
            last_error = exc
            if not any(marker in str(exc) for marker in RETRYABLE_MARKERS):
                raise
            if attempt == MAX_RETRIES - 1:
                break
            delay = BASE_DELAY_SECONDS * (2 ** attempt) + random.uniform(0, 0.5)
            time.sleep(delay)
    raise last_error

SESSIONS: dict[str, list[dict]] = {}


def get_history(session_id: str) -> list[dict]:
    return SESSIONS.setdefault(session_id, [])


def prune_history(history: list[dict]) -> None:
    """FIFO sliding window — drop the oldest messages once we're over the cap."""
    overflow = len(history) - MAX_HISTORY_MESSAGES
    if overflow > 0:
        del history[:overflow]


@app.route("/")
def index():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()

    if not user_message:
        return jsonify({"error": "Message can't be empty."}), 400

    session_id = session.get("session_id")
    if not session_id:
        return jsonify({"error": "No active session — reload the page."}), 400

    history = get_history(session_id)

    history.append({"role": "user", "parts": [{"text": user_message}]})

    try:
        response = call_gemini_with_retry(history)
    except Exception as exc:
        history.pop()
        message = str(exc)
        print(f"[Gemini API error] {message}")
        if any(marker in message for marker in RETRYABLE_MARKERS):
            friendly = "The AI is a bit busy right now — please try again in a moment."
        else:
            friendly = "Something went wrong talking to the model."
        return jsonify({"error": friendly}), 502

    assistant_text = response.text

    history.append({"role": "model", "parts": [{"text": assistant_text}]})

    prune_history(history)

    return jsonify({
        "reply": assistant_text,
        "history_length": len(history),
    })


@app.route("/api/reset", methods=["POST"])
def reset():
    session_id = session.get("session_id")
    if session_id:
        SESSIONS[session_id] = []
    return jsonify({"status": "reset"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
