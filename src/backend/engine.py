"""The Autopilot engine: features -> candidates -> decide. Pure functions, no I/O, no situation-specific code."""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from statistics import median

from core import GOAL_TYPES, MODES, TODAY, Goal, Instance, Txn, add_months, eur, fmt_date
from situations import SITUATIONS, Situation

BASE_ANNOYANCE = {"help": 3.0, "product": 12.0}   # product cards must clear a higher bar
IGNORE_PENALTY = 5.0                               # every "Later" makes that situation quieter
PRODUCT_GAP_DAYS = 30                              # at most one product card a month
PRODUCT_PAUSE_DAYS = 60                            # after "Not relevant" on a product card
SNOOZE_DAYS = 7


# ---------- features ----------

@dataclass
class Features:
    today: date
    balance: float
    savings: float
    products: dict
    goals: list[Goal]
    monthly_income: float = 0.0
    monthly_spend: float = 0.0
    forecast_min: float = 0.0
    forecast_min_day: date | None = None
    forecast_evidence: list[str] = field(default_factory=list)
    surplus: float = 0.0
    price_rises: list[dict] = field(default_factory=list)
    new_payees: list[dict] = field(default_factory=list)
    pin_events: list[dict] = field(default_factory=list)
    pin_resets_30d: int = 0
    same_device: bool = True
    maturity: dict | None = None


def recurring(txns: list[Txn]) -> dict[str, list[Txn]]:
    """Counterparties paid roughly monthly, at least 3 times."""
    by: dict[str, list[Txn]] = defaultdict(list)
    for t in txns:
        by[t.counterparty].append(t)
    out = {}
    for cp, ts in by.items():
        ts.sort(key=lambda t: t.day)
        gaps = [(b.day - a.day).days for a, b in zip(ts, ts[1:])]
        if len(ts) >= 3 and all(24 <= g <= 38 for g in gaps):
            out[cp] = ts
    return out


def forecast(balance: float, rec: dict[str, list[Txn]], daily_spend: float, today: date, days: int = 14):
    """Day-by-day balance for the next `days` days from recurring items plus average day-to-day spending."""
    expected: dict[date, list[Txn]] = defaultdict(list)
    for ts in rec.values():
        nxt = add_months(ts[-1].day, 1)
        while nxt <= today:
            nxt = add_months(nxt, 1)
        if nxt <= today + timedelta(days=days):
            expected[nxt].append(Txn(nxt, ts[-1].amount, ts[-1].counterparty))
    bal, path = balance, []
    for i in range(1, days + 1):
        d = today + timedelta(days=i)
        bal += sum(t.amount for t in expected[d]) - daily_spend
        path.append((d, bal))
    return path, expected


def compute_goals(goals: list[Goal], today: date = TODAY) -> list[Goal]:
    for g in goals:
        g.reached = g.saved_eur >= g.target_eur
        if g.reached:
            g.eta, g.on_course = today, True
        elif g.monthly_eur > 0:
            g.eta = add_months(today, math.ceil(g.remaining / g.monthly_eur))
            g.on_course = g.eta <= g.deadline
        else:
            g.eta, g.on_course = None, False
    return goals


def features(txns: list[Txn], balance: float, savings: float, products: dict, events: list[dict],
             goals: list[Goal], today: date = TODAY) -> Features:
    f = Features(today=today, balance=balance, savings=savings, products=products, goals=compute_goals(goals, today))
    window = [t for t in txns if (today - t.day).days < 90]
    f.monthly_income = sum(t.amount for t in window if t.amount > 0) / 3
    f.monthly_spend = -sum(t.amount for t in window if t.amount < 0) / 3

    rec = recurring(txns)
    rec_ids = {id(t) for ts in rec.values() for t in ts}
    day_to_day = -sum(t.amount for t in window if t.amount < 0 and id(t) not in rec_ids) / 90
    path, expected = forecast(balance, rec, day_to_day, today)
    f.forecast_min_day, f.forecast_min = min(path, key=lambda p: p[1])
    f.forecast_evidence = [f"{'Expected' if t.amount > 0 else 'Scheduled'}: {t.counterparty} {eur(t.amount)} on {fmt_date(d, 'en')}"
                           for d in sorted(expected) for t in expected[d]]
    f.forecast_evidence.append(f"Day-to-day spending: about {eur(day_to_day)} a day")
    f.surplus = f.forecast_min - 0.5 * f.monthly_spend

    for cp, ts in rec.items():
        amounts = [-t.amount for t in ts if t.amount < 0]
        if len(amounts) >= 3:
            old, new = median(amounts[:-1]), amounts[-1]
            if new > old * 1.05 and new - old >= 1:
                f.price_rises.append({"cp": cp, "old": old, "new": new, "history": [-a for a in amounts[-3:]],
                                      "description": ts[-1].description})

    first_seen: dict[str, Txn] = {}
    for t in sorted(txns, key=lambda t: t.day):
        first_seen.setdefault(t.counterparty, t)
    f.new_payees = [{"cp": t.counterparty, "amount": -t.amount, "day": t.day, "description": t.description}
                    for t in first_seen.values()
                    if (today - t.day).days <= 60 and 30 <= -t.amount <= 600 and t.counterparty not in rec]

    f.pin_events = [e for e in events if e["type"] == "pin_reset" and (today - e["day"]).days <= 30]
    f.pin_resets_30d = len(f.pin_events)
    f.same_device = len({e.get("device") for e in f.pin_events}) <= 1

    for what in ("term deposit", "state note"):
        p = products.get(what)
        if p:
            day = date.fromisoformat(p["matures"])
            f.maturity = {"what": what, "amount": p["amount"], "day": day, "days": (day - today).days}
    return f


# ---------- candidates and AI questions ----------

def candidates(f: Features) -> list[tuple[Situation, Instance]]:
    return [(s, inst) for s in SITUATIONS for inst in s.detect(f)]


def link_goals(s: Situation, inst: Instance, goals: list[Goal]) -> list[Goal]:
    """Goals this instance could move forward (before the AI confirms)."""
    if inst.goal_id is not None:
        return [g for g in goals if g.id == inst.goal_id]
    return [g for g in goals if not g.reached and g.type in s.serves]


def questions(f: Features, cands) -> tuple[dict, dict]:
    """One fan-out request per customer: a yes/no question per candidate, plus 'does this help goal X?'."""
    qs, fallbacks = {}, {}
    for s, inst in cands:
        if s.question:
            qid = f"{s.id}|{inst.key}"
            qs[qid] = {"type": "noul", "instructions": s.question.format(text=inst.ai_text)}
            fallbacks[qid] = s.fallback(inst)
        if inst.goal_id is None:
            for g in link_goals(s, inst, f.goals):
                qid = f"goal|{inst.key}|{g.id}"
                qs[qid] = {"type": "noul", "instructions":
                           f"Would acting on this situation ('{s.name}: {s.benefit.format(**fmt_params(inst.params))}') "
                           f"help the customer reach their goal '{g.title}' ({g.type.replace('_', ' ')})?"}
                fallbacks[qid] = 0.8
    return qs, fallbacks


def fmt_params(params: dict) -> dict:
    """*_eur -> '€ 1.234,00', *_day / day -> '3 Oct 2026'."""
    out = {}
    for k, v in params.items():
        if k.endswith("_eur"):
            out[k] = eur(v)
        elif isinstance(v, date):
            out[k] = fmt_date(v, "en")
        else:
            out[k] = v
    return out


# ---------- decide ----------

@dataclass
class Option:
    situation: Situation
    inst: Instance
    confidence: float
    customer_eur: float
    kbc_eur: float
    goal: Goal | None
    goal_weight: float
    annoyance: float
    score: float
    status: str   # shown | below_bar | no_consent | paused | snoozed | not_relevant | done | not_confirmed | holdout | no_benefit


def decide(customer: dict, f: Features, cands, probs: dict, prefs: dict, resolved: set, today: date = TODAY):
    """Score every candidate against 'do nothing'. Returns (card or None, all options, bar)."""
    bar = MODES[customer["mode"]]
    opts: list[Option] = []
    for s, inst in cands:
        p = probs.get(f"{s.id}|{inst.key}", inst.confidence) if s.question else inst.confidence
        goal, weight = None, 1.0
        for g in sorted(link_goals(s, inst, f.goals), key=lambda g: g.priority):
            if inst.goal_id is not None or probs.get(f"goal|{inst.key}|{g.id}", 0.0) >= 0.5:
                goal, weight = g, 1.5 if g.priority == 1 else 1.25
                break
        c_eur, k_eur = s.customer_eur(f, inst), s.kbc_eur(f, inst)
        pref = prefs.get(s.id, {})
        annoyance = BASE_ANNOYANCE[s.kind] + IGNORE_PENALTY * pref.get("ignores", 0)
        score = c_eur * weight * p - annoyance
        opts.append(Option(s, inst, p, c_eur, k_eur, goal, weight, annoyance, score,
                           gate(customer, s, inst, p, c_eur, pref, resolved, today)))

    live = [o for o in opts if o.status == "ok"]
    critical = [o for o in live if o.situation.risk == "critical"]
    best = max(critical or live, key=lambda o: o.score, default=None)
    for o in live:
        o.status = "below_bar"
    if best and (best.situation.risk == "critical" or best.score > bar):
        best.status = "shown"
        return best, opts, bar
    return None, opts, bar


def gate(customer: dict, s: Situation, inst: Instance, p: float, c_eur: float, pref: dict, resolved: set, today: date) -> str:
    if s.question and p < 0.5:
        return "not_confirmed"
    if inst.key in resolved:
        return "done"
    if c_eur <= 0:
        return "no_benefit"
    if not customer["consent_help"] or (s.kind == "product" and not customer["consent_product"]):
        return "no_consent"
    if customer["holdout"] and s.risk != "critical":
        return "holdout"   # measurement group; critical warnings still reach them
    if pref.get("suppressed") and s.risk != "critical":
        return "not_relevant"
    if pref.get("snoozed_until") and pref["snoozed_until"] > today:
        return "snoozed"
    if s.kind == "product":
        pause = customer.get("product_pause_until")
        last = customer.get("last_product_response")
        if (pause and pause > today) or (last and (today - last).days < PRODUCT_GAP_DAYS):
            return "paused"
    return "ok"


# ---------- responses and standing rules ----------

def respond_update(pref: dict, customer: dict, s: Situation, response: str, today: date = TODAY) -> tuple[dict, dict]:
    """New pref row and customer fields after Approve / Later / Not relevant."""
    pref = {"ignores": 0, "accepted": 0, "suppressed": 0, "snoozed_until": None, **pref}
    cust = {}
    if response == "approve":
        pref["accepted"] += 1
        pref["ignores"] = max(0, pref["ignores"] - 1)
    elif response == "later":
        pref["ignores"] += 1
        pref["snoozed_until"] = today + timedelta(days=SNOOZE_DAYS)
    elif response == "not_relevant":
        if s.risk == "critical":   # a critical warning can be snoozed, never switched off
            pref["snoozed_until"] = today + timedelta(days=SNOOZE_DAYS)
        else:
            pref["suppressed"] = 1
        if s.kind == "product":
            cust["product_pause_until"] = today + timedelta(days=PRODUCT_PAUSE_DAYS)
    if s.kind == "product":
        cust["last_product_response"] = today
    return pref, cust


def rule_amount(rule: dict, balance: float, moved_this_month: float) -> float:
    """Standing rule: keep `keep` on the current account, move the excess to the goal, max `cap` a month."""
    return max(0.0, min(balance - rule["keep"], rule["cap"] - moved_this_month))


def rule_allowed(s: Situation, option: dict) -> bool:
    """'Always do this' only for low-risk help transfers between the customer's own accounts."""
    return (s.kind == "help" and s.risk == "normal" and option.get("type") == "transfer"
            and "always" in option and option.get("to", "").startswith("goal:"))


# ---------- goals from onboarding ----------

def validate_goals(raw, today: date = TODAY) -> list[dict]:
    """Strict check of AI- or user-supplied goals. Raises ValueError."""
    if not isinstance(raw, list) or len(raw) > 5:
        raise ValueError("goals must be a list of at most 5")
    out = []
    for g in raw:
        if not isinstance(g, dict):
            raise ValueError("goal must be an object")
        title = str(g.get("title", "")).strip()[:40]
        gtype = g.get("type")
        horizon = g.get("horizon")
        try:
            target = float(g.get("target_eur"))
            deadline = date.fromisoformat(str(g.get("deadline")))
            priority = int(g.get("priority", len(out) + 1))
            monthly = float(g.get("monthly_eur") or 0)
        except (TypeError, ValueError):
            raise ValueError("bad amount, date or priority")
        if not title or gtype not in GOAL_TYPES or horizon not in ("now", "long"):
            raise ValueError("bad title, type or horizon")
        if not (0 < target <= 10_000_000) or deadline <= today or not 1 <= priority <= 5 or not 0 <= monthly <= 100_000:
            raise ValueError("amount, date, priority or monthly amount out of range")
        out.append({"title": title, "type": gtype, "horizon": horizon, "target_eur": round(target, 2),
                    "deadline": deadline, "priority": priority, "monthly_eur": round(monthly, 2)})
    return out


def pace_for(goals: list[dict], monthly_room: float) -> list[float]:
    """Split the customer's usual monthly room over goals: 60% to priority 1, the rest shared.
    A goal with its own monthly_eur (the customer's choice) keeps it and is left out of the split."""
    if not goals:
        return []
    own = [float(g.get("monthly_eur") or 0) for g in goals]
    if any(own):
        rest = [g for g, m in zip(goals, own) if not m]
        shared = iter(pace_for(rest, max(0.0, monthly_room - sum(own))))
        return [m if m else next(shared) for m in own]
    ranked = sorted(range(len(goals)), key=lambda i: goals[i]["priority"])
    share = [0.0] * len(goals)
    rest = ranked[1:]
    share[ranked[0]] = 0.6 if rest else 1.0
    for i in rest:
        share[i] = 0.4 / len(rest)
    return [round(max(0.0, monthly_room) * s, 2) for s in share]

