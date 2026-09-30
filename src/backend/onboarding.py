"""'Where do you want to fly to?' Goal sparring with an LLM; an offline extractor keeps the demo working without a key."""
from __future__ import annotations

import json
import math
import re
from datetime import date

import ai
from core import TODAY, add_months, eur, fmt_month
from engine import pace_for, validate_goals

MAX_TURNS = 6

SYSTEM = """You are the onboarding guide of KBC Autopilot, a calm helper in a Belgian banking app.
Goal: in a few short turns, agree on the customer's financial goals ("flight plan").
- "now" goals (stopovers) are within 6 months; "long" goals (destinations) are later.
- Ask about both. One short question per turn. Max 60 words per reply. Plain, warm English. No sales, no products, no exclamation marks.
- Use the customer summary to sanity-check targets. If a deadline is unrealistic at their usual monthly room, say so kindly and suggest a realistic date.
- Only financial goals. Politely steer back if they talk about something else.
Customer summary (pseudonymised): {summary}
Today is {today}.
Always answer with only this JSON:
{{"reply": "...", "goals": [{{"horizon": "now|long", "type": "save_for|buffer|avoid_overdraft|pay_off|budget_cap|raise_capital|care_for_family|other",
"title": "max 40 chars", "target_eur": 1234, "deadline": "YYYY-MM-DD", "priority": 1}}]}}
"goals" is the full current draft (max 5), keep earlier goals unless the customer changes them."""


def turn(history: list[dict], summary: dict, live: bool) -> dict:
    """One onboarding turn. history = [{"role": "user"|"assistant", "content": str}, ...]."""
    user_turns = sum(1 for m in history if m["role"] == "user")
    system = SYSTEM.format(summary=json.dumps(summary), today=TODAY)
    for _ in range(2):   # one retry if the model returns something invalid
        out = ai.llm_json(system, history, live)
        if out is None:
            break
        try:
            goals = validate_goals(out.get("goals", []))
            reply = str(out.get("reply", "")).strip()[:400]
            if reply:
                return result(reply, goals, summary, user_turns, "live")
        except ValueError:
            continue
    reply, goals = offline(history, summary)
    return result(reply, goals, summary, user_turns, "offline")


def result(reply: str, goals: list[dict], summary: dict, user_turns: int, source: str) -> dict:
    return {"reply": reply, "goals": plan(goals, summary), "turns_left": max(0, MAX_TURNS - user_turns), "source": source}


def plan(goals: list[dict], summary: dict) -> list[dict]:
    """Attach the pace and ETA the flight plan shows. Maths in code, never in the model."""
    paces = pace_for(goals, summary["monthly_room"])
    out = []
    for g, pace in zip(goals, paces):
        eta = add_months(TODAY, math.ceil(g["target_eur"] / pace)) if pace > 0 else None
        out.append({**g, "deadline": str(g["deadline"]), "monthly_eur": pace, "eta": str(eta) if eta else None,
                    "on_course": bool(eta and eta <= g["deadline"])})
    return out


# ---------- offline extractor ----------

TOPICS = [  # key, type, title, words, default target (None = from spending), default months
    ("trip", "save_for", "Trip", ("trip", "travel", "holiday", "vacation", "ski", "citytrip", "reis", "vakantie"), 1500, 5),
    ("home", "save_for", "Own home", ("house", "home", "flat", "apartment", "appartement", "huis"), 40000, 72),
    ("buffer", "buffer", "Safety buffer", ("buffer", "emergency", "safety", "rainy", "unexpected"), None, 18),
    ("car", "save_for", "Car", ("car", "auto"), 12000, 24),
    ("studies", "save_for", "Studies", ("study", "studies", "school", "university", "course"), 5000, 36),
    ("business", "raise_capital", "Own business", ("business", "startup", "company", "shop"), 20000, 24),
    ("family", "care_for_family", "Family", ("family", "parents", "mother", "father", "kids", "children", "wedding"), 5000, 24),
    ("debt", "pay_off", "Pay off debt", ("debt", "loan", "pay off", "credit card"), 3000, 12),
]
MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august", "september",
          "october", "november", "december")
NUMBER = re.compile(r"(?:€\s*)?(\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?)\s*(k\b|thousand)?", re.I)


def when(text: str) -> date | None:
    t = text.lower()
    for i, m in enumerate(MONTHS):
        if m in t or re.search(rf"\b{m[:3]}\b", t):
            y = TODAY.year + (1 if i + 1 <= TODAY.month else 0)
            ym = re.search(r"\b(20[2-4]\d)\b", t)
            return date(int(ym.group(1)) if ym else y, i + 1, 1)
    if y := re.search(r"\b(20[2-4]\d)\b", t):
        return date(int(y.group(1)), 6, 30)
    if n := re.search(r"\bin (\d+) years?\b", t):
        return add_months(TODAY, 12 * int(n.group(1)))
    if n := re.search(r"\bin (\d+) months?\b", t):
        return add_months(TODAY, int(n.group(1)))
    return None


def amounts(text: str) -> list[tuple[int, float]]:
    out = []
    for m in NUMBER.finditer(text):
        raw = m.group(1).replace(".", "").replace(",", "") if re.search(r"[.,]\d{3}\b", m.group(1)) \
            else m.group(1).replace(",", ".")
        v = float(raw) * (1000 if m.group(2) else 1)
        if 2020 <= v <= 2050 and not m.group(2) and "€" not in m.group(0):
            continue   # a year, not an amount
        if v >= 50:
            out.append((m.start(), v))
    return out


def offline(history: list[dict], summary: dict) -> tuple[str, list[dict]]:
    goals: dict[str, dict] = {}
    last = None
    for msg in (m["content"] for m in history if m["role"] == "user"):
        low = msg.lower()
        found = sorted((low.find(w), t) for t in TOPICS for w in t[3] if w in low)
        seen = []
        for pos, t in found:
            if t[0] in seen:
                continue
            seen.append(t[0])
            nxt = [s for s, o in found if s > pos and o[0] != t[0]]
            clause = msg[pos: min(nxt) if nxt else len(msg)]
            key, gtype, title, _, target, months = t
            g = goals.get(key) or {"title": title, "type": gtype,
                                   "target_eur": target or round(3 * summary["monthly_spend"], -2),
                                   "deadline": add_months(TODAY, months)}
            if a := amounts(clause):
                g["target_eur"] = a[0][1]
            if d := when(clause):
                g["deadline"] = d
            goals[key] = g
            last = key
        if not seen and last:   # a follow-up like "make it 2032" or "600 is fine" changes the last goal
            if d := when(msg):
                goals[last]["deadline"] = d
            if a := amounts(msg):
                goals[last]["target_eur"] = a[0][1]

    draft = []
    for p, g in enumerate(list(goals.values())[:5], start=1):
        deadline = max(g["deadline"], add_months(TODAY, 1))
        draft.append({"title": g["title"], "type": g["type"], "target_eur": g["target_eur"], "deadline": deadline,
                      "priority": p, "horizon": "now" if (deadline - TODAY).days <= 183 else "long"})
    return reply_for(draft, summary), draft


def reply_for(draft: list[dict], summary: dict) -> str:
    if not draft:
        return ("Where do you want to fly to? Tell me what you're working towards, soon and later. "
                "For example a trip this winter, a safety buffer, or your own home one day.")
    room = summary["monthly_room"]
    for g, pace in zip(draft, pace_for(draft, room)):
        eta = add_months(TODAY, math.ceil(g["target_eur"] / pace)) if pace > 0 else None
        if eta is None:
            return (f"Right now there's little room left at the end of the month, so {g['title']} has no arrival date yet. "
                    "Want to start small, or first build a safety buffer?")
        if eta > g["deadline"]:
            return (f"At your usual spare {eur(room, 0)} a month, {g['title']} arrives around {fmt_month(eta, 'en')}, "
                    f"later than {fmt_month(g['deadline'], 'en')}. Aim for {fmt_month(eta, 'en')}, or pick a smaller target?")
    has_now = any(g["horizon"] == "now" for g in draft)
    has_long = any(g["horizon"] == "long" for g in draft)
    if not has_now:
        return "Good destination. Anything coming up in the next few months, a stopover on the way?"
    if not has_long:
        return "Nice stopover. And further ahead, where would you like to be in a few years?"
    return "Your flight plan is ready. Check the route, adjust anything, and confirm when it looks right."
