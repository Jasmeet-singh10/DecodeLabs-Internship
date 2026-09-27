"""
DecodeLabs Project 3 — Multimodal Image Generation Studio
Run: streamlit run app.py
"""

import base64
import io
import os
import random
import time

import requests
import streamlit as st
from PIL import Image

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

STABILITY_URL = "https://api.stability.ai/v2beta/stable-image/generate/core"
OPENAI_URL = "https://api.openai.com/v1/images/generations"

CONNECT_TIMEOUT = 3.05
READ_TIMEOUT = 60
MAX_RETRIES = 3

ASPECT_RATIOS = ["1:1", "16:9", "9:16", "3:2", "2:3", "4:5", "5:4"]

OPENAI_SIZES = {
    "1:1": "1024x1024",
    "16:9": "1536x1024",
    "9:16": "1024x1536",
}

OUTPUT_DIR = "generated_assets"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Networking helpers
# ---------------------------------------------------------------------------

def _sleep_backoff(attempt: int):
    wait = (2 ** attempt) + random.uniform(0, 1)
    time.sleep(wait)


def post_with_retry(url, headers, data=None, files=None, json_body=None):
    """POST with split connect/read timeout and exponential backoff+jitter
    retried only on 429 / 5xx. Connect failures fail fast (no retry)."""
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(
                url,
                headers=headers,
                data=data,
                files=files,
                json=json_body,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )
        except requests.exceptions.ConnectTimeout as e:
            # Network failure -> fail fast, do not retry
            raise RuntimeError(f"Could not connect to API: {e}") from e
        except requests.exceptions.ReadTimeout as e:
            last_exc = e
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"API timed out after {MAX_RETRIES} attempts: {e}") from e
            _sleep_backoff(attempt)
            continue

        if resp.status_code in (429, 500, 502, 503, 504):
            last_exc = RuntimeError(f"Server returned {resp.status_code}")
            if attempt == MAX_RETRIES:
                raise last_exc
            _sleep_backoff(attempt)
            continue

        return resp

    raise last_exc


def stream_to_disk(response: requests.Response, filepath: str, chunk_size: int = 65536):
    """Memory-safe write of a streaming binary response to disk."""
    with open(filepath, "wb") as f:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)


def verify_image(filepath: str) -> bool:
    """Force a full pixel-level decode to catch truncated/corrupted streams."""
    try:
        img = Image.open(filepath)
        img.load()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Provider calls
# ---------------------------------------------------------------------------

def generate_stability(api_key, prompt, negative_prompt, aspect_ratio, output_format="png"):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "image/*",
    }
    data = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "output_format": output_format,
    }
    if negative_prompt:
        data["negative_prompt"] = negative_prompt

    resp = post_with_retry(
        STABILITY_URL,
        headers=headers,
        data=data,
        files={"none": (None, "")},  # forces multipart, required by this endpoint
    )

    if resp.status_code == 403:
        raise RuntimeError("Blocked by content moderation gate (input or output).")
    if resp.status_code != 200:
        raise RuntimeError(f"Stability API error {resp.status_code}: {resp.text[:300]}")

    filename = f"stability_{int(time.time() * 1000)}.{output_format}"
    filepath = os.path.join(OUTPUT_DIR, filename)
    stream_to_disk(resp, filepath)

    if not verify_image(filepath):
        os.remove(filepath)
        raise RuntimeError("Downloaded image failed integrity check (truncated stream).")

    return filepath


def generate_openai(api_key, prompt, aspect_ratio, n=1):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    size = OPENAI_SIZES.get(aspect_ratio, "1024x1024")
    body = {
        "model": "gpt-image-1",
        "prompt": prompt,
        "size": size,
        "n": n,
    }

    resp = post_with_retry(OPENAI_URL, headers=headers, json_body=body)

    if resp.status_code == 400 and "moderation" in resp.text.lower():
        raise RuntimeError("Blocked by content moderation gate.")
    if resp.status_code != 200:
        raise RuntimeError(f"OpenAI API error {resp.status_code}: {resp.text[:300]}")

    payload = resp.json()
    filepaths = []
    for i, item in enumerate(payload.get("data", [])):
        b64 = item["b64_json"]
        raw = base64.b64decode(b64)
        filename = f"openai_{int(time.time() * 1000)}_{i}.png"
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(raw)
        if not verify_image(filepath):
            os.remove(filepath)
            raise RuntimeError("Downloaded image failed integrity check.")
        filepaths.append(filepath)
    return filepaths


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Multimodal Image Generation Studio", layout="wide")
st.title("🎨 Multimodal Image Generation Studio")
st.caption("DecodeLabs — Project 3")

with st.sidebar:
    provider = st.selectbox("Engine", ["Stability AI (Stable Image Core)", "OpenAI (gpt-image-1)"])
    api_key = st.text_input("API Key", type="password")
    aspect_ratio = st.selectbox("Aspect Ratio", ASPECT_RATIOS)
    n_images = st.number_input("Number of images", min_value=1, max_value=4, value=1)

prompt = st.text_area("Prompt", height=100, placeholder="A cyberpunk city skyline at dusk, neon reflections...")
negative_prompt = st.text_input("Negative prompt (Stability only, optional)")

if st.button("Generate", type="primary"):
    if not api_key or not prompt:
        st.error("API key and prompt are required.")
    else:
        results = []
        errors = []
        with st.spinner("Generating..."):
            for i in range(int(n_images)):
                try:
                    if provider.startswith("Stability"):
                        fp = generate_stability(api_key, prompt, negative_prompt, aspect_ratio)
                        results.append(fp)
                    else:
                        fps = generate_openai(api_key, prompt, aspect_ratio, n=1)
                        results.extend(fps)
                except RuntimeError as e:
                    errors.append(str(e))

        if errors:
            for e in errors:
                st.warning(e)

        if results:
            cols = st.columns(min(len(results), 4))
            for col, fp in zip(cols, results):
                with col:
                    st.image(fp, use_container_width=True)
                    with open(fp, "rb") as f:
                        st.download_button("Download", f, file_name=os.path.basename(fp))
