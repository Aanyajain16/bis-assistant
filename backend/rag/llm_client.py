"""
llm_client.py
-------------
Thin wrapper around the LLM API. Swapping providers means editing
ONLY this file - main.py and prompt.py never change.

If no API key is configured, or the API call fails for any reason
(network, invalid key, rate limit, provider outage), this falls back
to a clearly-labeled DEMO MODE that builds an answer directly from the
retrieved evidence text, so the app can still be demonstrated end-to-end.
"""

import requests

from rag import config

LLM_PROVIDER = config.LLM_PROVIDER.lower()
LLM_API_KEY = config.LLM_API_KEY
LLM_MODEL = config.LLM_MODEL

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class LLMError(Exception):
    pass


def _call_anthropic(system_prompt: str, user_prompt: str) -> str:
    if not LLM_API_KEY:
        raise LLMError("LLM_API_KEY is not set")

    response = requests.post(
        ANTHROPIC_URL,
        headers={
            "x-api-key": LLM_API_KEY,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        },
        json={
            "model": LLM_MODEL,
            "max_tokens": 1000,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        },
        timeout=30,
    )

    if response.status_code != 200:
        raise LLMError(f"Anthropic API returned {response.status_code}: {response.text[:300]}")

    data = response.json()
    text_blocks = [block["text"] for block in data.get("content", []) if block.get("type") == "text"]
    if not text_blocks:
        raise LLMError("Anthropic API returned no text content")
    return "\n".join(text_blocks)


def _demo_answer(user_prompt: str, evidence_chunks: list[dict], question: str) -> str:
    """
    Offline fallback used when no real LLM call succeeds. Builds a
    plain, honest answer directly from evidence text - never invents
    anything not present in the chunks.
    """
    if not evidence_chunks:
        return (
            "[DEMO MODE - LLM not connected]\n\n"
            "The available BIS knowledge base does not contain enough information "
            "to answer this question confidently. Please add relevant BIS documents "
            "to backend/data/bis_documents/ and re-run ingestion, or connect a real "
            "LLM API key in .env."
        )

    excerpt_lines = []
    for i, chunk in enumerate(evidence_chunks[:3], start=1):
        meta = chunk["metadata"]
        page_info = f" (page {meta.get('page')})" if meta.get("page") not in (None, "N/A") else ""
        excerpt = chunk["text"][:400].strip()
        excerpt_lines.append(f"{i}. From \"{meta.get('title')}\"{page_info}: {excerpt}...")

    return (
        "[DEMO MODE - LLM not connected, showing retrieved evidence directly]\n\n"
        f"Regarding: \"{question}\"\n\n"
        "The following relevant excerpts were found in the BIS knowledge base:\n\n"
        + "\n\n".join(excerpt_lines)
        + "\n\nConnect a real LLM_API_KEY in .env to get a natural-language answer "
          "synthesized from this evidence instead of raw excerpts."
    )


def generate_answer(system_prompt: str, user_prompt: str, evidence_chunks: list[dict], question: str) -> tuple[str, bool]:
    """
    Returns (answer_text, used_demo_mode).
    Tries the configured real provider first; falls back to demo mode
    on any failure so the prototype never just crashes mid-demo.
    """
    if LLM_PROVIDER == "demo" or not LLM_API_KEY:
        return _demo_answer(user_prompt, evidence_chunks, question), True

    try:
        if LLM_PROVIDER == "anthropic":
            answer = _call_anthropic(system_prompt, user_prompt)
            return answer, False
        else:
            raise LLMError(f"Unknown LLM_PROVIDER '{LLM_PROVIDER}'")
    except (LLMError, requests.RequestException) as e:
        print(f"[llm_client] Falling back to demo mode: {e}")
        return _demo_answer(user_prompt, evidence_chunks, question), True
