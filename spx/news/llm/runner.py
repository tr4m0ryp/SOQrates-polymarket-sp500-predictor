"""Provider-agnostic LLM runner for the news layer (OpenAI-compatible).

One code path covers every candidate: Gemini (OpenAI-compat endpoint),
Groq, OpenRouter, DeepSeek - they all speak chat-completions. Configure:

  LLM_BASE_URL   e.g. https://generativelanguage.googleapis.com/v1beta/openai
                      https://api.groq.com/openai/v1
                      https://openrouter.ai/api/v1
  LLM_API_KEY    provider key
  LLM_MODEL      e.g. gemini-2.5-flash / llama-3.3-70b-versatile

Optional fallback chain (tried in order on failure):
  LLM_FALLBACK_BASE_URL / LLM_FALLBACK_API_KEY / LLM_FALLBACK_MODEL

Usage budget by design: ~12 calls/night (1 Group-A + <=11 Group-B), small
prompts - fits every free tier researched 2026-07 (Gemini ~1500/day,
Groq 1k/day, OpenRouter 50/day).
"""
import json
import os
import time
import urllib.request


class LlmError(RuntimeError):
    pass


def _providers():
    out = []
    for prefix in ("LLM", "LLM_FALLBACK"):
        base = os.environ.get(f"{prefix}_BASE_URL", "")
        key = os.environ.get(f"{prefix}_API_KEY", "")
        model = os.environ.get(f"{prefix}_MODEL", "")
        if base and key and model:
            out.append({"base": base.rstrip("/"), "key": key, "model": model})
    if not out:
        raise LlmError("no provider configured - set LLM_BASE_URL, "
                       "LLM_API_KEY, LLM_MODEL")
    return out


def _call(provider: dict, system: str, user_payload: dict,
          timeout: int = 90) -> str:
    body = {
        "model": provider["model"],
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user_payload)},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        f"{provider['base']}/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {provider['key']}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        res = json.load(r)
    msg = res["choices"][0]["message"]
    content = msg.get("content")
    if content:
        return content
    # Reasoning models (gpt-oss, nemotron and friends) put their chain in
    # `reasoning_content` and return content=None when the token budget runs
    # out before they emit an answer. Verified on NVIDIA 2026-08-13:
    # gpt-oss-120b at max_tokens=64 returns None, at 512 returns the answer.
    # Surface that as a named failure instead of a NoneType error three
    # frames deeper in the JSON validator.
    if msg.get("reasoning_content"):
        raise LlmError(
            f"{provider['model']} returned reasoning but no content "
            f"(finish_reason={res['choices'][0].get('finish_reason')}); "
            f"the token budget was consumed before an answer was emitted")
    raise LlmError(f"{provider['model']} returned an empty message")


def run(system: str, user_payload: dict, validator, retries: int = 2) -> dict:
    """Call providers in order; validate/clamp output; retry on bad JSON."""
    last = None
    for provider in _providers():
        for attempt in range(retries):
            try:
                raw = _call(provider, system, user_payload)
                out = validator(raw)
                out["_provider"] = f"{provider['model']}"
                return out
            except Exception as e:
                last = e
                time.sleep(2 * (attempt + 1))
    raise LlmError(f"all providers failed: {last}")
