"""
DecodeLabs Project 4 — Intelligent Code Reviewer & Explainer (Streamlit app)
Run: streamlit run app_code_reviewer.py
"""

import os
import random
import time

import requests
import streamlit as st

GEMINI_MODELS = ["gemini-3.8-flash", "gemini-3.5-flash-lite"]
GEMINI_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
CONNECT_TIMEOUT = 3.05
READ_TIMEOUT = 60
MAX_RETRIES = 3

SYSTEM_INSTRUCTION = """You are a cold, analytical Senior Code Quality Assurance Engineer.

You only output valid code blocks and direct bullet points.
Do not write friendly greetings, preambles, or sign-offs.

You MUST return your response in exactly this structure, with both
section headers present verbatim:

## BUG_REPORT
- Direct, concise bullet points detailing syntax anomalies, logical
  vulnerabilities, and performance bugs. If none are found, state
  "No issues detected."

## REFACTORED_CODE
A single, valid Markdown-fenced code block containing the corrected,
compilable code with the original language tag.
"""

SUPPORTED_EXTENSIONS = {".py": "python", ".js": "javascript", ".java": "java"}


# ---------------------------------------------------------------------------
# Networking
# ---------------------------------------------------------------------------

def _sleep_backoff(attempt: int):
    wait = min((2 ** attempt) + random.uniform(0, 1), 30)
    time.sleep(wait)


def _call_model(api_key: str, model: str, code: str, language: str) -> str:
    """Try a single model, with retries on 429/5xx. Raises RuntimeError on
    exhaustion so the caller can fall back to the next model."""
    headers = {"Content-Type": "application/json"}
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": [
            {
                "role": "user",
                "parts": [{"text": f"Review the following {language} code:\n\n```{language}\n{code}\n```"}],
            }
        ],
        "generationConfig": {"temperature": 0.2},
    }
    url = f"{GEMINI_URL_TEMPLATE.format(model=model)}?key={api_key}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
        except requests.exceptions.ConnectTimeout as e:
            raise RuntimeError(f"Could not connect to Gemini API: {e}") from e
        except requests.exceptions.ReadTimeout:
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"{model} timed out after {MAX_RETRIES} attempts.")
            _sleep_backoff(attempt)
            continue

        if resp.status_code in (429, 500, 502, 503, 504):
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"{model} returned {resp.status_code} after {MAX_RETRIES} attempts.")
            _sleep_backoff(attempt)
            continue

        if resp.status_code == 400 and "safety" in resp.text.lower():
            raise RuntimeError("Blocked by content safety filters.")
        if resp.status_code != 200:
            raise RuntimeError(f"{model} error {resp.status_code}: {resp.text[:300]}")

        payload = resp.json()
        try:
            candidate = payload["candidates"][0]
            if candidate.get("finishReason") == "SAFETY":
                raise RuntimeError("Response blocked by output safety filter.")
            return candidate["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            raise RuntimeError(f"Unexpected response shape from {model}.")

    raise RuntimeError(f"Failed to get a response from {model}.")


def call_gemini(api_key: str, code: str, language: str) -> str:
    """Try each model in GEMINI_MODELS in order, falling back to the next
    one if the current model is overloaded or unavailable."""
    errors = []
    for model in GEMINI_MODELS:
        try:
            return _call_model(api_key, model, code, language)
        except RuntimeError as e:
            errors.append(str(e))
            continue
    raise RuntimeError("All models failed:\n" + "\n".join(errors))


def validate_structure(text: str) -> bool:
    return "## BUG_REPORT" in text and "## REFACTORED_CODE" in text


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Intelligent Code Reviewer", layout="wide")
st.title("🧠 Intelligent Code Reviewer & Explainer")
st.caption("DecodeLabs — Project 4")

with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password", value=os.environ.get("GEMINI_API_KEY", ""))

uploaded = st.file_uploader("Upload a code file", type=["py", "js", "java"])
pasted_code = st.text_area("...or paste code directly", height=250, placeholder="def add(a, b)\n    return a+b")
language_override = None

code = None
language = None

if uploaded is not None:
    ext = os.path.splitext(uploaded.name)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        st.error(f"Unsupported file type '{ext}'. Supported: .py, .js, .java")
    else:
        try:
            code = uploaded.read().decode("utf-8")
            language = SUPPORTED_EXTENSIONS[ext]
        except UnicodeDecodeError:
            st.error("Could not decode file as UTF-8 (binary or unsupported encoding).")
elif pasted_code.strip():
    language = st.selectbox("Language", ["python", "javascript", "java"])
    code = pasted_code

if st.button("Review Code", type="primary"):
    if not api_key:
        st.error("API key is required.")
    elif not code or not code.strip():
        st.error("Upload a file or paste some code first.")
    else:
        with st.spinner("Analyzing..."):
            try:
                response_text = call_gemini(api_key, code, language)
            except RuntimeError as e:
                st.error(str(e))
                response_text = None

        if response_text:
            if not validate_structure(response_text):
                st.warning("Model response missing required section headers — showing raw output.")
                st.text(response_text)
            else:
                st.markdown(response_text)
