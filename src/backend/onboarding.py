"""Goal sparring with an LLM; an offline extractor keeps the demo working without a key."""
from __future__ import annotations

import json
import math
import re
from datetime import date

import ai
from core import TODAY, add_months, eur, fmt_month
from engine import pace_for, validate_goals

MAX_TURNS = 6

SYSTEM = """You are the sparring partner of KBC Autopilot, a calm helper in a Belgian banking app.
Goal: in a few short turns, agree on concrete goals: what the customer saves for, how much, by when, and how much a month.
- "now" goals are within 6 months; "long" goals are later.
- Spar, don't interrogate: challenge a vague goal with one concrete number or date. One short question per turn. Max 60 words per reply.
  Plain, warm English. No sales, no products, no exclamation marks.
- Use the customer summary to sanity-check targets. If a deadline is unrealistic at their usual monthly room, say so kindly and suggest a realistic date or monthly amount.
- "suggestions" in the summary are goals Autopilot noticed in their life. Mention at most one when relevant; add it only if the customer says yes.
- Only financial goals. Politely steer back if they talk about something else.
Customer summary (pseudonymised): {summary}
Current draft (the customer may have edited amounts, dates or monthly amounts by hand; keep those unless they change them): {draft}
Today is {today}.
Always answer with only this JSON:
{{"reply": "...", "goals": [{{"horizon": "now|long", "type": "save_for|buffer|avoid_overdraft|pay_off|budget_cap|raise_capital|care_for_family|other",
"title": "max 40 chars", "target_eur": 1234, "deadline": "YYYY-MM-DD", "priority": 1, "monthly_eur": 0}}]}}
"goals" is the full current draft (max 5). "monthly_eur" is the customer's own monthly amount, 0 when they left it to Autopilot."""


def turn(history: list[dict], summary: dict, live: bool, draft: list[dict] | None = None) -> dict:
    """One onboarding turn. history = [{"role": "user"|"assistant", "content": str}, ...]; draft = current goals (validated)."""
    draft = draft or []
    user_turns = sum(1 for m in history if m["role"] == "user")
    system = SYSTEM.format(summary=json.dumps(summary), today=TODAY, draft=json.dumps(draft, default=str))
    for _ in range(2):   # one retry if the model returns something invalid
        out = ai.llm_json(system, history, live, model=ai.SPAR_MODEL)
        if out is None:
            break
        try:
            goals = validate_goals(out.get("goals", []))
            reply = str(out.get("reply", "")).strip()[:400]
            if reply:
                return result(reply, goals, summary, user_turns, "live")
        except ValueError:
            continue
    reply, goals = offline(history, summary, draft)
    return result(reply, goals, summary, user_turns, "offline")


def result(reply: str, goals: list[dict], summary: dict, user_turns: int, source: str) -> dict:
    return {"reply": reply, "goals": plan(goals, summary), "turns_left": max(0, MAX_TURNS - user_turns), "source": source}


def plan(goals: list[dict], summary: dict) -> list[dict]:
    """Attach the pace and expected date the goal list shows. Maths in code, never in the model."""
    paces = pace_for(goals, summary["monthly_room"])
    out = []
    for g, pace in zip(goals, paces):
        eta = add_months(TODAY, math.ceil(g["target_eur"] / pace)) if pace > 0 else None
        out.append({**g, "deadline": str(g["deadline"]), "monthly_eur": float(g.get("monthly_eur") or 0), "pace_eur": pace,
                    "eta": str(eta) if eta else None, "on_course": bool(eta and eta <= g["deadline"])})
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


def offline(history: list[dict], summary: dict, draft: list[dict] | None = None) -> tuple[str, list[dict]]:
    # the draft (manual edits) comes first; only the last message can change it, earlier turns are already in it
    goals: dict[str, dict] = {}
    added = []   # suggestions taken into the plan this turn, named in the reply
    for g in draft or []:   # keyed like TOPICS so "my house" later edits "Own home" instead of adding a twin
        key = next((t[0] for t in TOPICS if t[2].lower() == g["title"].lower()), g["title"].lower())
        goals[key] = {**g, "monthly_eur": float(g.get("monthly_eur") or 0)}
    last = next(reversed(goals), None)   # a bare "make it 2500" edits the newest draft goal
    msgs = [m["content"] for m in history if m["role"] == "user"]
    for msg in msgs[-1:] if goals else msgs:
        low = msg.lower()
        if re.search(r"\b(yes|ok|sure|add)\b", low):   # "yes, add the ring" takes a suggestion into the plan
            for sg in summary.get("suggestions", []):
                if any(w in low for w in sg["title"].lower().split()) and sg["title"].lower() not in goals:
                    goals[sg["title"].lower()] = {"title": sg["title"], "type": sg["type"], "target_eur": sg["target_eur"],
                                                  "deadline": date.fromisoformat(sg["deadline"]), "monthly_eur": 0.0}
                    last = sg["title"].lower()
                    added.append(sg["title"])
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
                                   "deadline": add_months(TODAY, months), "monthly_eur": 0.0}
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

    out = []
    for p, g in enumerate(list(goals.values())[:5], start=1):
        deadline = max(date.fromisoformat(str(g["deadline"])), add_months(TODAY, 1))
        out.append({"title": g["title"], "type": g["type"], "target_eur": g["target_eur"], "deadline": deadline,
                    "priority": p, "horizon": "now" if (deadline - TODAY).days <= 183 else "long", "monthly_eur": g["monthly_eur"]})
    reply = reply_for(out, summary)
    return (f"Added {', '.join(added)}. " + reply if added else reply), out


def reply_for(draft: list[dict], summary: dict) -> str:
    if not draft:
        if summary.get("suggestions"):
            sg = summary["suggestions"][0]
            return (f"Where do you want to fly to? One goal I noticed: {sg['title']}, about {eur(sg['target_eur'], 0)} "
                    f"by {fmt_month(date.fromisoformat(sg['deadline']), 'en')}. Want to add it, or start with something else?")
        return ("Where do you want to fly to? Tell me what you're working towards, soon and later. "
                "For example a trip this winter, a safety buffer, or your own home one day.")
    room = summary["monthly_room"]
    for g, pace in zip(draft, pace_for(draft, room)):
        eta = add_months(TODAY, math.ceil(g["target_eur"] / pace)) if pace > 0 else None
        if eta is None:
            return (f"Right now there's little room left at the end of the month, so {g['title']} has no expected date yet. "
                    "Want to start small, or first build a safety buffer?")
        if eta > g["deadline"]:
            return (f"At your usual spare {eur(room, 0)} a month, {g["title"]} is reached around {fmt_month(eta, "en")}, "
                    f"later than {fmt_month(g['deadline'], 'en')}. Aim for {fmt_month(eta, 'en')}, or pick a smaller target?")
    has_now = any(g["horizon"] == "now" for g in draft)
    has_long = any(g["horizon"] == "long" for g in draft)
    if not has_now:
        return "Good long-term goal. Anything coming up in the next few months?"
    if not has_long:
        return "Good. And further ahead, where would you like to be in a few years?"
    return "Your goals are set. Check the amounts and dates, adjust anything, and save when it looks right."
