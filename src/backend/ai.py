"""AI calls through OpenRouter: Jev (typed yes/no screening) and an LLM (phrasing, onboarding).

The key only comes from the OPENROUTER_API_KEY environment variable (Secret Manager on Cloud Run).
Without it every call returns None and callers use their offline fallback, so the demo never breaks.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://openrouter.ai/api/v1"
JEV_MODEL = os.environ.get("JEV_MODEL", "~typesafe/jev-latest")
LLM_MODEL = os.environ.get("LLM_MODEL", "anthropic/claude-haiku-4.5")
CACHE_FILE = Path(__file__).with_name("ai_cache.json")

_cache: dict = json.loads(CACHE_FILE.read_text()) if CACHE_FILE.exists() else {}
_lock = threading.Lock()


def has_key() -> bool:
    return bool(os.environ.get("OPENROUTER_API_KEY"))


def _hash(*parts) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:24]


def _post(path: str, body: dict, timeout: float) -> dict | None:
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}", "Content-Type": "application/json",
                 "X-Title": "KBC Autopilot prototype"})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 529) and attempt == 0:
                time.sleep(0.8)
                continue
            return None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None
    return None


def jev(state, qs: dict, live: bool) -> dict | None:
    """Ask Jev a set of yes/no questions about one state. Returns {question_id: probability} or None."""
    if not qs:
        return {}
    k = _hash("jev", JEV_MODEL, state, qs)
    if k in _cache:
        return _cache[k]
    if not (live and has_key()):
        return None
    res = _post("/systemone", {"model": JEV_MODEL, "state": state, "questions": qs}, timeout=15)
    if not res or "answers" not in res:
        return None
    out = {q: float(a.get("noul", 0.0)) for q, a in res["answers"].items()}
    with _lock:
        _cache[k] = out
    return out


def screen(state, qs: dict, fallbacks: dict, live: bool) -> tuple[dict, str]:
    """Jev if possible, else the offline fallback. Returns (probabilities, source)."""
    got = jev(state, qs, live)
    if got is not None:
        return {**fallbacks, **got}, "jev"
    return fallbacks, "offline"


def llm_json(system: str, messages: list[dict], live: bool, max_tokens: int = 500) -> dict | None:
    """Chat completion that must return one JSON object."""
    k = _hash("llm", LLM_MODEL, system, messages)
    if k in _cache:
        return _cache[k]
    if not (live and has_key()):
        return None
    res = _post("/chat/completions", {"model": LLM_MODEL, "max_tokens": max_tokens, "temperature": 0.3,
                                      "messages": [{"role": "system", "content": system}, *messages]}, timeout=25)
    try:
        text = res["choices"][0]["message"]["content"]
        out = json.loads(text[text.index("{"): text.rindex("}") + 1])
    except (TypeError, KeyError, IndexError, ValueError):
        return None
    with _lock:
        _cache[k] = out
    return out


# ---------- phrasing the one card a customer sees ----------

PUSHY = re.compile(r"!|\b(urgent|hurry|now or never|don't miss|exclusive|offer|limited|act now|last chance)\b", re.I)

PHRASE_SYSTEM = """You rewrite one short banking-app card for KBC Autopilot, a helpful assistant.
Rules: keep every euro amount exactly as given (same characters). No urgency, no exclamation marks,
no sales words (offer, exclusive, limited). Plain, calm, friendly English. Title max 60 characters, body max 220.
Return only JSON: {"title": "...", "body": "..."}"""


def tone_ok(text: str, required: list[str]) -> bool:
    """A phrasing is only used if it keeps every amount and has no pushy language."""
    return all(r in text for r in required) and not PUSHY.search(text)


def phrase(title: str, body: str, required: list[str], live: bool) -> tuple[str, str]:
    """LLM rewording of the frozen decision. Falls back to the template if anything is off."""
    out = llm_json(PHRASE_SYSTEM, [{"role": "user", "content": json.dumps({"title": title, "body": body})}], live, 300)
    if out and isinstance(out.get("title"), str) and isinstance(out.get("body"), str):
        t, b = out["title"].strip(), out["body"].strip()
        if len(t) <= 80 and len(b) <= 280 and tone_ok(t + " " + b, required):
            return t, b
    return title, body


def save_cache() -> None:
    CACHE_FILE.write_text(json.dumps(_cache, indent=0, sort_keys=True))
