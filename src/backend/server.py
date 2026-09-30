"""KBC Autopilot prototype server. Python standard library only.

    python server.py      # http://localhost:8000 (PORT env var on Cloud Run)
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from collections import defaultdict, deque
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import ai
import onboarding
import paths
import seed
from core import MODES, TODAY, Goal, Txn, add_months, eur, fmt_date
from engine import (candidates, compute_goals, decide, features, fmt_params, pace_for, questions,
                    respond_update, rule_allowed, rule_amount, validate_goals)
from situations import BY_ID, SITUATIONS

HERE = Path(__file__).parent
DB_PATH = Path(os.environ.get("DB_PATH", "/tmp/kbc-autopilot.db"))
STATIC = Path(os.environ.get("STATIC_DIR", HERE.parent / "frontend" / "dist")).resolve()
MAX_BODY = 16_384

db = seed.build(DB_PATH)
lock = threading.Lock()   # ponytail: one global DB lock, fine for one Cloud Run instance and a jury


def q(sql: str, *args) -> list[dict]:
    cur = db.execute(sql, args)
    cols = [c[0] for c in cur.description or []]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def d(s):
    return date.fromisoformat(s) if s else None


# ---------- loading and evaluating one customer ----------

def load(cid: int):
    rows = q("SELECT c.*, i.display_name, i.persona FROM customer c JOIN identity i ON i.customer_id = c.id WHERE c.id = ?", cid)
    if not rows:
        return None
    c = rows[0]
    c["products"] = json.loads(c["products"])
    c["product_pause_until"] = d(c["product_pause_until"])
    c["last_product_response"] = d(c["last_product_response"])
    txns = [Txn(d(t["day"]), t["amount"], t["counterparty"], t["description"])
            for t in q("SELECT day, amount, counterparty, description FROM txn WHERE customer_id = ? ORDER BY day", cid)]
    events = [{"type": e["type"], "day": d(e["day"]), **json.loads(e["data"])}
              for e in q("SELECT type, day, data FROM event WHERE customer_id = ?", cid)]
    goals = [Goal(g["id"], g["horizon"], g["type"], g["title"], g["target_eur"], g["saved_eur"], d(g["deadline"]),
                  g["priority"], g["monthly_eur"]) for g in q("SELECT * FROM goal WHERE customer_id = ? ORDER BY priority", cid)]
    c["suggestions"] = paths.suggest(txns, peer_goals(cid), goals)
    prefs = {p["situation_id"]: {**p, "snoozed_until": d(p["snoozed_until"])}
             for p in q("SELECT * FROM pref WHERE customer_id = ?", cid)}
    resolved = {r["instance_key"] for r in q("SELECT instance_key FROM resolved WHERE customer_id = ?", cid)}
    return c, txns, events, goals, prefs, resolved


def peer_goals(cid: int) -> list[dict]:
    """Goals of people this customer paid with Payconiq in the last 90 days. Titles and types only, no names,
    and only from peers who allow Autopilot to use their data."""
    since = str(TODAY - timedelta(days=90))
    return q("SELECT DISTINCT g.title, g.type FROM txn t JOIN customer p ON p.id = t.peer_id JOIN goal g ON g.customer_id = p.id "
             "WHERE t.customer_id = ? AND t.day >= ? AND p.consent_help = 1", cid, since)


def ai_state(f) -> dict:
    """Pseudonymised, minimal state for the AI: no name, no account numbers, no address."""
    return {"monthly_income": round(f.monthly_income), "monthly_spend": round(f.monthly_spend),
            "goals": [{"title": g.title, "type": g.type} for g in f.goals if not g.reached]}


def evaluate(cid: int, live: bool = True):
    c, txns, events, goals, prefs, resolved = load(cid)
    f = features(txns, c["balance"], c["savings"], c["products"], events, goals)
    cands = candidates(f)
    qs, fallbacks = questions(f, cands)
    probs, source = ai.screen(ai_state(f), qs, fallbacks, live)
    card, opts, bar = decide(c, f, cands, probs, prefs, resolved)
    return c, txns, f, cands, card, opts, bar, source, prefs, qs, probs


# ---------- view model ----------

STATUS_TEXT = {"shown": "Shown to you", "below_bar": "Not worth disturbing you", "no_consent": "Needs your permission",
               "paused": "Paused: no product suggestions right now", "snoozed": "Snoozed", "not_relevant": "You said not relevant",
               "done": "Done", "not_confirmed": "Checked, doesn't apply", "holdout": "Test group: kept quiet",
               "no_benefit": "No benefit for you"}
PRIMARY = {"transfer": "Review transfer", "form": "Review form", "options": "See options", "handoff": "See options",
           "info": "Got it"}


def card_json(card, f, source: str, live: bool) -> dict | None:
    if card is None:
        return None
    s, inst = card.situation, card.inst
    p = fmt_params(inst.params)
    title, body = s.title.format(**p), s.body.format(**p)
    required = [v for k, v in p.items() if k.endswith("_eur") and v in title + " " + body]
    title, body = ai.phrase(title, body, required, live)
    options = s.options(f, inst) if s.options else []
    return {
        "situation_id": s.id, "instance_key": inst.key, "kind": s.kind, "risk": s.risk, "action": s.action,
        "title": title, "body": body, "benefit": s.benefit.format(**p), "primary": PRIMARY[s.action],
        "includes_kbc_product": s.kind == "product" or any(o.get("kbc") for o in options),
        "goal": card.goal and {"id": card.goal.id, "title": card.goal.title, "saved": card.goal.saved_eur,
                               "target": card.goal.target_eur},
        "options": options,
        "why": {"evidence": inst.evidence,
                "confidence": "High" if card.confidence >= 0.85 else "Medium" if card.confidence >= 0.6 else "Low",
                "checked_by": "AI check (Jev)" if source == "jev" and s.question else "Rules on your own data",
                "customer_eur": round(card.customer_eur, 2), "score": round(card.score, 1)},
    }


def view(cid: int, live: bool = True) -> dict:
    c, txns, f, cands, card, opts, bar, source, prefs, qs, probs = evaluate(cid, live)
    goals = compute_goals(f.goals)
    rules = q("SELECT r.*, g.title FROM rule r JOIN goal g ON g.id = r.goal_id WHERE r.customer_id = ? AND r.active = 1", cid)
    considered = [{"name": o.situation.name, "status": o.status, "status_text": STATUS_TEXT[o.status],
                   "score": round(o.score, 1), "customer_eur": round(o.customer_eur, 2), "kind": o.situation.kind}
                  for o in sorted(opts, key=lambda o: -o.score)]
    detected = {o.situation.id for o in opts}
    considered += [{"name": s.name, "status": "not_detected", "status_text": "Not your situation", "score": None,
                    "customer_eur": 0, "kind": s.kind} for s in SITUATIONS if s.id not in detected]
    memory = []
    for sid, p in prefs.items():
        name = BY_ID[sid].name if sid in BY_ID else sid
        if p["suppressed"]:
            memory.append(f"You said “{name}” is not relevant. Autopilot won't suggest it again.")
        if p["snoozed_until"] and p["snoozed_until"] > TODAY:
            memory.append(f"“{name}” snoozed until {fmt_date(p['snoozed_until'], 'en')}.")
        if p["accepted"]:
            memory.append(f"You accepted “{name}” {p['accepted']}×. Similar help ranks a bit higher.")
    if c["product_pause_until"] and c["product_pause_until"] > TODAY:
        memory.append(f"No product suggestions until {fmt_date(c['product_pause_until'], 'en')}.")
    shown = card_json(card, f, source, live)
    return {
        "id": cid, "name": c["display_name"], "persona": c["persona"], "onboarded": bool(c["onboarded"]),
        "is_try": cid in seed.TRY_IDS,
        "balance": round(c["balance"], 2), "savings": round(c["savings"], 2),
        "mode": c["mode"], "consent_help": bool(c["consent_help"]), "consent_product": bool(c["consent_product"]),
        "value_created": round(c["value_created"], 2),
        "transactions": [{"day": str(t.day), "amount": t.amount, "counterparty": t.counterparty}
                         for t in sorted(txns, key=lambda t: t.day, reverse=True)[:6]],
        "card": shown,
        "pipeline": pipeline(c, txns, f, cands, card, opts, bar, source, qs, probs, shown),
        "considered": considered, "bar": bar,
        "goals": [{"id": g.id, "title": g.title, "horizon": g.horizon, "type": g.type, "target": g.target_eur,
                   "saved": g.saved_eur, "deadline": str(g.deadline), "eta": str(g.eta) if g.eta else None,
                   "on_course": g.on_course, "reached": g.reached, "monthly": g.monthly_eur, "priority": g.priority}
                  for g in goals],
        "suggestions": c["suggestions"],
        "rules": [{"id": r["id"], "goal": r["title"], "keep": r["keep"], "cap": r["cap"],
                   "next_run": str(add_months(TODAY.replace(day=1), 1)),
                   "preview": round(rule_amount(r, c["balance"], 0), 2)} for r in rules],
        "memory": memory,
        "log": [{"day": x["day"], "text": x["note"]} for x in
                q("SELECT day, note FROM decision WHERE customer_id = ? AND note != '' ORDER BY id DESC LIMIT 5", cid)],
    }


def pipeline(c, txns, f, cands, card, opts, bar, source, qs, probs, shown) -> list[dict]:
    """The 7 steps behind one decision, in plain words. Only reads what evaluate() already produced."""
    def item(label, value, tone="info"):
        return {"label": label, "value": value, "tone": tone}

    def step(key, title, summary, items):
        return {"key": key, "title": title, "summary": summary, "items": items[:8]}

    products = [k for k in f.products if k != "mutualiteit"]
    signals = [item("Payments", f"{len(txns)} in the last 3 months"), item("PIN resets", f"{f.pin_resets_30d} in 30 days"),
               item("Goals", str(len(f.goals))), item("Current account", eur(f.balance)), item("Savings", eur(f.savings)),
               item("Products", ", ".join(products) or "none"),
               item("Health insurer", f.products.get("mutualiteit", "unknown"))]
    low_day = fmt_date(f.forecast_min_day, "en") if f.forecast_min_day else "n/a"
    understood = [item("Money in a month", eur(f.monthly_income)), item("Money out a month", eur(f.monthly_spend)),
                  item("Lowest point, next 14 days", f"{eur(f.forecast_min)} on {low_day}", "no" if f.forecast_min < 0 else "ok"),
                  item("Room after scheduled payments", eur(f.surplus), "ok" if f.surplus >= 100 else "info")]
    understood += [item("Bill went up", f"{r['cp']}: {eur(r['old'])} → {eur(r['new'])}", "no") for r in f.price_rises]
    understood += [item("New payee", f"{p['cp']} {eur(p['amount'])}") for p in f.new_payees]
    if f.pin_resets_30d:
        understood.append(item("PIN resets", f"{f.pin_resets_30d}, {'same device' if f.same_device else 'different devices'}"))
    if f.maturity:
        understood.append(item("Matures", f"{f.maturity['what']} of {eur(f.maturity['amount'])} on {fmt_date(f.maturity['day'], 'en')}"))

    n = len({s.id for s, _ in cands})
    cand_items = [item(s.name, "; ".join(inst.evidence)) for s, inst in cands]

    who = "Jev" if source == "jev" else "offline check"
    ai_items = []
    for qid, qv in qs.items():
        p = probs.get(qid, 0.0)
        ai_items.append(item(qv["instructions"], f"{p:.0%} yes ({who})", "ok" if p >= 0.5 else "no"))
    ai_summary = (f"{len(qs)} yes/no question{'s' if len(qs) != 1 else ''}, answered by "
                  f"{'Jev' if source == 'jev' else 'offline keyword rules'}") if qs else "No questions needed: rules on your own data are enough"

    ranked = sorted(opts, key=lambda o: -o.score)
    score_items = [item(o.situation.name, f"{eur(o.customer_eur, 0)} × {o.goal_weight:g} goal × {o.confidence:.2f} sure − "
                        f"{o.annoyance:g} = {o.score:.1f} vs bar {bar:g}", "ok" if o.score > bar else "no") for o in ranked]
    beat = sum(o.score > bar for o in opts)

    control_items = [item(o.situation.name, STATUS_TEXT[o.status], "ok" if o.status == "shown" else "no") for o in ranked]
    controls = (f"{c['mode'].capitalize()} mode · help suggestions {'on' if c['consent_help'] else 'off'} · "
                f"product suggestions {'on' if c['consent_product'] else 'off'}")

    if shown:
        s, p = card.situation, fmt_params(card.inst.params)
        templ = shown["title"] == s.title.format(**p) and shown["body"] == s.body.format(**p)
        decision = step("decision", "Decision", f"Showing one card: {shown['title']}", [
            item("Situation", s.name, "ok"), item("Benefit for you", shown["benefit"]),
            item("Wording", "Fixed template" if templ else "Reworded by the AI, amounts checked"),
            item("Money moves", "Only after you review and approve")])
    else:
        decision = step("decision", "Decision", "Staying quiet: nothing beat doing nothing",
                        [item(o.situation.name, STATUS_TEXT[o.status], "no") for o in ranked])
    return [
        step("signals", "Signals", f"{len(txns)} payments, {f.pin_resets_30d} log-in events, {len(f.goals)} goal{'' if len(f.goals) == 1 else 's'}", signals),
        step("understood", "What Autopilot understood",
             f"{eur(f.monthly_income, 0)} in, {eur(f.monthly_spend, 0)} out a month", understood),
        step("candidates", "Possible situations",
             f"{n} of {len(SITUATIONS)} situations could apply" if n else f"None of the {len(SITUATIONS)} situations fit right now",
             cand_items),
        step("ai_check", "AI check", ai_summary, ai_items),
        step("score", "Score vs doing nothing",
             f"{beat} of {len(opts)} beat doing nothing (bar {bar:g})" if opts else "Nothing to score", score_items),
        step("controls", "Your controls", controls, control_items),
        decision,
    ]


# ---------- actions ----------

def respond(cid: int, body: dict) -> dict:
    key, response = body.get("instance_key"), body.get("response")
    if response not in ("approve", "later", "not_relevant") or not isinstance(key, str):
        raise ValueError("bad response")
    c, txns, f, cands, card, opts, bar, source, prefs, qs, probs = evaluate(cid, live=False)
    match = next(((s, i) for s, i in cands if i.key == key), None)
    if not match:
        raise ValueError("this suggestion no longer applies")
    s, inst = match
    o = next(o for o in opts if o.inst.key == key)
    new_pref, cust = respond_update(prefs.get(s.id, {}), c, s, response)
    db.execute("INSERT OR REPLACE INTO pref (customer_id, situation_id, ignores, accepted, suppressed, snoozed_until) "
               "VALUES (?,?,?,?,?,?)", (cid, s.id, new_pref["ignores"], new_pref["accepted"], new_pref["suppressed"],
                                        str(new_pref["snoozed_until"]) if new_pref["snoozed_until"] else None))
    for col, v in cust.items():
        db.execute(f"UPDATE customer SET {col} = ? WHERE id = ?", (str(v), cid))   # col from a fixed set, not user input

    result, note, option_id = {"lines": []}, "", None
    if response == "approve":
        options = s.options(f, inst) if s.options else []
        option = next((x for x in options if x["id"] == body.get("option_id")), options[0] if options else {})
        option_id = option.get("id")
        result, note = apply(cid, c, s, inst, o, option, bool(body.get("always")))
        db.execute("UPDATE customer SET value_created = value_created + ? WHERE id = ?", (o.customer_eur, cid))
        db.execute("INSERT OR IGNORE INTO resolved VALUES (?, ?)", (cid, key))
    db.execute("INSERT INTO decision (customer_id, day, situation_id, instance_key, response, option_id, customer_eur, "
               "kbc_eur, note) VALUES (?,?,?,?,?,?,?,?,?)",
               (cid, str(TODAY), s.id, key, response, option_id, o.customer_eur if response == "approve" else 0,
                o.kbc_eur if response == "approve" else 0, note))
    db.commit()
    return {"result": result, "view": view(cid)}


def apply(cid: int, c: dict, s, inst, o, option: dict, always: bool) -> tuple[dict, str]:
    """Simulated effect of an approved option. Returns (confirmation for the UI, audit note)."""
    kind, lines = option.get("type", "info"), []
    if kind == "transfer" and s.id != "maturity":
        amount, src, dst = option["amount"], option["from"], option["to"]
        if src in ("current", "savings"):
            db.execute(f"UPDATE customer SET {'balance' if src == 'current' else 'savings'} = "
                       f"{'balance' if src == 'current' else 'savings'} - ? WHERE id = ?", (amount, cid))
        if dst == "current":
            db.execute("UPDATE customer SET balance = balance + ? WHERE id = ?", (amount, cid))
        elif dst == "savings":
            db.execute("UPDATE customer SET savings = savings + ? WHERE id = ?", (amount, cid))
        elif dst.startswith("goal:"):
            db.execute("UPDATE goal SET saved_eur = saved_eur + ? WHERE id = ? AND customer_id = ?",
                       (amount, int(dst[5:]), cid))
            db.execute("UPDATE customer SET savings = savings + ? WHERE id = ?", (amount, cid))
        lines.append(f"{eur(amount)} moved. Simulated, no real money moved.")
        note = f"You moved {eur(amount)} ({s.name})."
        if always and rule_allowed(s, option):
            db.execute("INSERT INTO rule (customer_id, goal_id, keep, cap, created) VALUES (?,?,?,?,?)",
                       (cid, int(dst[5:]), option["always"]["keep"], option["always"]["cap"], str(TODAY)))
            lines.append(f"Autopilot rule on: every month, keep {eur(option['always']['keep'])} on your current account "
                         f"and move the rest to your goal, max {eur(option['always']['cap'])}. You can switch it off any time.")
            note += " Standing rule created."
    elif kind == "transfer":   # a maturing deposit: an instruction for the maturity day
        lines.append(f"On {fmt_date(inst.params['day'], 'en')}, {eur(option['amount'])} goes to: {option['label']}. Simulated.")
        note = f"Instruction for your maturing deposit: {option['label']}."
    elif kind == "form":
        lines.append("Form sent. Simulated. You'll get a copy in your documents.")
        note = f"Form sent: {option['label']}."
    elif kind == "handoff":
        lines += [f"A {option['advisor']} will call you within one working day (simulated).",
                  "They already see what Autopilot noticed, so you don't need to repeat anything."]
        note = f"Handed over to a {option['advisor']} with context."
    else:
        lines.append(option.get("detail") or "Noted.")
        note = f"You chose: {option.get('label', s.name)}."
    saving = s.monthly_saving(None, inst) if s.monthly_saving else 0
    if saving > 0 and o.goal:
        db.execute("UPDATE goal SET monthly_eur = monthly_eur + ? WHERE id = ?", (saving, o.goal.id))
        lines.append(f"The {eur(saving)} a month you save goes to {o.goal.title}. You get there sooner.")
    return {"type": kind, "lines": lines, "advisor": option.get("advisor")}, note


def summary(cid: int) -> dict:
    """What the onboarding guide may know: pseudonymised monthly figures only."""
    c, txns, events, goals, prefs, resolved = load(cid)
    f = features(txns, c["balance"], c["savings"], c["products"], events, goals)
    room = max(0.0, round(f.monthly_income - f.monthly_spend, -1))
    return {"monthly_income": round(f.monthly_income, -1), "monthly_spend": round(f.monthly_spend, -1),
            "monthly_room": room, "savings": round(c["savings"], -2),
            "suggestions": [{k: s[k] for k in ("title", "type", "target_eur", "deadline", "reason")} for s in c["suggestions"]]}


def save_goals(cid: int, raw) -> dict:
    """Replace the plan. Progress (saved_eur) carries over by title; standing rules are reset with the plan."""
    goals = validate_goals(raw)
    paces = pace_for(goals, summary(cid)["monthly_room"])
    saved = {r["title"].lower(): r["saved_eur"] for r in q("SELECT title, saved_eur FROM goal WHERE customer_id = ?", cid)}
    db.execute("DELETE FROM rule WHERE customer_id = ?", (cid,))
    db.execute("DELETE FROM goal WHERE customer_id = ?", (cid,))
    db.executemany("INSERT INTO goal (customer_id, horizon, type, title, target_eur, saved_eur, deadline, priority, "
                   "monthly_eur) VALUES (?,?,?,?,?,?,?,?,?)",
                   [(cid, g["horizon"], g["type"], g["title"], g["target_eur"], saved.get(g["title"].lower(), 0),
                     str(g["deadline"]), g["priority"], p) for g, p in zip(goals, paces)])
    db.execute("UPDATE customer SET onboarded = 1 WHERE id = ?", (cid,))
    db.commit()
    return view(cid)


def add_goal(cid: int, raw) -> dict:
    """Append one goal (for example a suggestion) without touching the others or their rules."""
    have = q("SELECT title FROM goal WHERE customer_id = ?", cid)
    if len(have) >= 5:
        raise ValueError("five goals is the maximum")
    g = validate_goals([{**(raw if isinstance(raw, dict) else {}), "priority": len(have) + 1}])[0]
    if g["title"].lower() in {r["title"].lower() for r in have}:
        raise ValueError("you already have this goal")
    pace = g["monthly_eur"] or pace_for([{"priority": 1}], summary(cid)["monthly_room"])[0] * 0.4
    db.execute("INSERT INTO goal (customer_id, horizon, type, title, target_eur, saved_eur, deadline, priority, monthly_eur) "
               "VALUES (?,?,?,?,?,0,?,?,?)", (cid, g["horizon"], g["type"], g["title"], g["target_eur"], str(g["deadline"]),
                                             g["priority"], round(pace, 2)))
    db.execute("UPDATE customer SET onboarded = 1 WHERE id = ?", (cid,))
    db.commit()
    return view(cid)


def settings(cid: int, body: dict) -> dict:
    if "mode" in body:
        if body["mode"] not in MODES:
            raise ValueError("bad mode")
        db.execute("UPDATE customer SET mode = ? WHERE id = ?", (body["mode"], cid))
    for k in ("consent_help", "consent_product"):
        if k in body:
            if not isinstance(body[k], bool):
                raise ValueError(f"bad {k}")
            db.execute(f"UPDATE customer SET {k} = ? WHERE id = ?", (int(body[k]), cid))   # k from a fixed tuple
    db.commit()
    return view(cid)


def reset_memory(cid: int) -> dict:
    db.execute("DELETE FROM pref WHERE customer_id = ?", (cid,))
    db.execute("DELETE FROM resolved WHERE customer_id = ?", (cid,))
    db.execute("UPDATE customer SET product_pause_until = NULL, last_product_response = NULL WHERE id = ?", (cid,))
    db.commit()
    return view(cid)


def revoke_rule(cid: int, rid: int) -> dict:
    db.execute("UPDATE rule SET active = 0 WHERE id = ? AND customer_id = ?", (rid, cid))
    db.execute("INSERT INTO decision (customer_id, day, situation_id, instance_key, response, note) VALUES (?,?,?,?,?,?)",
               (cid, str(TODAY), "rule", f"rule:{rid}", "revoke", "You switched off an Autopilot rule."))
    db.commit()
    return view(cid)


_try_next = 0


def new_try() -> dict:
    """A fresh "You" customer on the next id of the recycled try pool."""
    global _try_next
    cid = seed.TRY_IDS[_try_next % len(seed.TRY_IDS)]
    _try_next += 1
    for table, col in (("txn", "customer_id"), ("event", "customer_id"), ("goal", "customer_id"), ("rule", "customer_id"),
                       ("pref", "customer_id"), ("resolved", "customer_id"), ("decision", "customer_id"),
                       ("identity", "customer_id"), ("customer", "id")):
        db.execute(f"DELETE FROM {table} WHERE {col} = ?", (cid,))   # names from a fixed tuple
    seed.insert(db, cid, seed.baseline())
    db.commit()
    return view(cid)


def scenario(cid: int, body: dict) -> dict:
    """Replay one situation on a try customer: baseline + scenario. Goals and prefs are kept, so learning carries over."""
    sid = body.get("id")
    if cid not in seed.TRY_IDS:
        raise ValueError("scenarios only work on your own try-it customer")
    if not isinstance(sid, str) or sid not in seed.SCENARIOS:
        raise ValueError("unknown scenario")
    c = seed.baseline()
    seed.SCENARIOS[sid]["apply"](c)
    for table in ("txn", "event", "resolved"):
        db.execute(f"DELETE FROM {table} WHERE customer_id = ?", (cid,))   # table from a fixed tuple
    seed.insert_activity(db, cid, c)
    db.execute("UPDATE customer SET balance = ?, savings = ?, products = ? WHERE id = ?",
               (c["balance"], c["savings"], json.dumps(c["products"]), cid))
    db.commit()
    v = view(cid)
    return {"view": v, "notification": v["card"] and {"title": v["card"]["title"], "body": v["card"]["benefit"]}}


def reset_demo() -> dict:
    global db, _funnel
    _funnel = None
    db.close()
    db = seed.build(DB_PATH)
    return {"ok": True}


def warm() -> None:
    """Pre-compute AI answers for every customer so the public demo needs no live calls to browse."""
    from concurrent.futures import ThreadPoolExecutor
    ids = [r["id"] for r in q("SELECT id FROM customer")]
    with ThreadPoolExecutor(max_workers=20) as pool:
        list(pool.map(lambda cid: evaluate(cid, live=True), ids))
    for cid in seed.DEMO_IDS:
        view(cid, live=True)
    ai.save_cache()
    print(f"warmed {len(ids)} customers into {ai.CACHE_FILE}")


# ---------- behind the scenes: the whole population ----------

SCALE = 2_300_000
_funnel: dict | None = None


def funnel() -> dict:
    """Run the same engine over every synthetic customer. Never calls AI live (cache or offline fallback)."""
    global _funnel
    if _funnel:
        return _funnel
    ids = [r["id"] for r in q("SELECT id FROM customer WHERE id >= 100 AND id < 10000")]
    n = len(ids)
    stats = {"customers": n, "with_candidate": 0, "confirmed": 0, "shown": 0, "help": 0, "product": 0,
             "customer_eur": 0.0, "kbc_eur": 0.0, "trust": 0, "holdout": 0, "holdout_shown": 0, "questions": 0,
             "tokens": 0}
    per = {s.id: {"id": s.id, "name": s.name, "audience": s.audience, "kind": s.kind, "detected": 0, "shown": 0}
           for s in SITUATIONS}
    for cid in ids:
        c, txns, f, cands, card, opts, bar, source, prefs, qs, probs = evaluate(cid, live=False)
        stats["questions"] += len(qs)
        stats["tokens"] += len(json.dumps([ai_state(f), qs])) // 4 if qs else 0
        stats["holdout"] += c["holdout"]
        stats["with_candidate"] += bool(cands)
        stats["confirmed"] += any(o.status != "not_confirmed" for o in opts)
        for sid in {o.situation.id for o in opts if o.status != "not_confirmed"}:
            per[sid]["detected"] += 1
        if card:
            stats["shown"] += 1
            stats["holdout_shown"] += c["holdout"]
            stats[card.situation.kind] += 1
            stats["customer_eur"] += card.customer_eur
            stats["kbc_eur"] += card.kbc_eur
            stats["trust"] += card.kbc_eur < 0
            per[card.situation.id]["shown"] += 1
    k = SCALE / n
    daily_jev = stats["tokens"] * k * 0.05 / 1e6 * 0.042          # 5% of customers get new signals per day
    daily_llm = stats["shown"] * k / 7 * 600 / 1e6 * 2.0           # one worded card a week, ~600 tokens
    _funnel = {**stats, "situations": list(per.values()), "scale": SCALE,
               "cost_per_day_usd": round(daily_jev + daily_llm, 2), "jev_per_day_usd": round(daily_jev, 2),
               "ai_mode": "live" if ai.has_key() else "offline fallback"}
    return _funnel


SYNONYMS = {  # offline stand-in for the AI check on plain-language situations
    "pet": ("zooplus", "dierenarts", "tom&co"), "dog": ("zooplus", "dierenarts", "tom&co"),
    "cat": ("zooplus", "dierenarts", "tom&co"), "travel": ("ryanair", "brussels airlines", "booking.com"),
    "trip": ("ryanair", "brussels airlines", "booking.com"), "holiday": ("ryanair", "brussels airlines", "booking.com"),
    "fly": ("ryanair", "brussels airlines"), "gym": ("basic-fit", "jims"), "fitness": ("basic-fit", "jims"),
    "baby": ("prenatal", "kruidvat baby", "dreambaby"), "pregnan": ("prenatal", "dreambaby"),
    "car": ("d'ieteren", "vab", "carglass"), "streaming": ("netflix", "spotify", "disney"),
    "sport": ("basic-fit", "jims", "decathlon", "club", "lidgeld"),
}


def add_situation(text: str) -> dict:
    """Screen a plain-language situation over a sample of customers: no code, one AI yes/no question each."""
    text = " ".join(text.split())[:200]
    if len(text) < 4:
        raise ValueError("describe the situation in a few words")
    ids = [r["id"] for r in q("SELECT id FROM customer WHERE id >= 100 AND id < 10000 AND id % 10 = 0")]
    low = text.lower()
    words = {w for w in re.findall(r"[a-z&'.-]{4,}", low)} | {m for k, v in SYNONYMS.items() if k in low for m in v}
    question = {"type": "noul", "instructions": f"Based on these recent payments, does this describe the customer: {text}?"}

    payments = {cid: [f"{t['counterparty']} {t['description']} {eur(t['amount'])}".strip() for t in
                      q("SELECT counterparty, description, amount FROM txn WHERE customer_id = ? ORDER BY day DESC LIMIT 30", cid)]
                for cid in ids}   # read the DB here; only the AI calls run in parallel

    def one(cid):
        lines = payments[cid]
        hits = [x for x in lines if any(w in x.lower() for w in words)]
        got = ai.jev({"payments": lines}, {"match": question}, live=True)
        p = got["match"] if got else (0.9 if hits else 0.05)
        return cid, p, hits, "jev" if got else "offline"

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(one, ids))
    matched = [r for r in results if r[1] >= 0.5]
    source = "jev" if any(r[3] == "jev" for r in results) else "offline"
    db.execute("INSERT INTO situation_custom (text, sample, matches, source) VALUES (?,?,?,?)",
               (text, len(ids), len(matched), source))
    db.commit()
    keys = {r["id"]: r["pkey"] for r in q("SELECT id, pkey FROM customer WHERE id >= 100 AND id < 10000 AND id % 10 = 0")}
    return {"text": text, "sample": len(ids), "matches": len(matched), "source": source,
            "estimate": round(len(matched) / max(1, len(ids)) * SCALE, -3),
            "examples": [{"customer": keys[cid], "confidence": round(p, 2), "evidence": hits[:3]}
                         for cid, p, hits, _ in matched[:5]]}


def engine_view() -> dict:
    return {"funnel": funnel(),
            "catalogue": [{"id": s.id, "name": s.name, "audience": s.audience, "kind": s.kind, "risk": s.risk,
                           "action": s.action, "check": "Rules + AI yes/no check" if s.question else "Rules on the customer's own data",
                           "question": (s.question or "").replace("'{text}'", "…").replace("{text}", "…")} for s in SITUATIONS],
            "custom": q("SELECT text, sample, matches, source FROM situation_custom ORDER BY id DESC LIMIT 5")}


# ---------- HTTP ----------

hits: dict[str, deque] = defaultdict(deque)


def allow(bucket: str, limit: int, window: float) -> bool:
    now, h = time.time(), hits[bucket]
    while h and h[0] < now - window:
        h.popleft()
    if len(h) >= limit:
        return False
    h.append(now)
    return True


SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
                               "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
    "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}
CUSTOMER_PATH = re.compile(r"^/api/customers/(\d{1,5})(?:/([a-z-]+))?(?:/(\d{1,6}))?$")


class Handler(BaseHTTPRequestHandler):
    server_version = "autopilot"
    sys_version = ""

    def send(self, status: int, body: bytes, ctype: str, cache: str = "no-store"):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        for k, v in SECURITY_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def json(self, status: int, obj) -> None:
        self.send(status, json.dumps(obj, default=str).encode(), "application/json")

    def ip(self) -> str:
        fwd = self.headers.get("X-Forwarded-For", "")
        return fwd.split(",")[0].strip() or self.client_address[0]

    def body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_BODY:
            raise ValueError("request too large")
        data = json.loads(self.rfile.read(n) or b"{}")
        if not isinstance(data, dict):
            raise ValueError("expected a JSON object")
        return data

    def do_GET(self):
        path = self.path.split("?")[0]
        try:
            with lock:
                if path == "/api/customers":
                    return self.json(200, [{"id": r["customer_id"], "name": r["display_name"], "persona": r["persona"]}
                                           for r in q("SELECT * FROM identity WHERE customer_id < 100 ORDER BY customer_id")])
                if path == "/api/scenarios":
                    return self.json(200, [{"id": k, "label": v["label"], "blurb": v["blurb"], "needs_goal": v["needs_goal"]}
                                           for k, v in seed.SCENARIOS.items()])
                if path == "/api/engine":
                    return self.json(200, engine_view())
                if m := CUSTOMER_PATH.match(path):
                    if m.group(2) or not load(int(m.group(1))):
                        return self.json(404, {"error": "not found"})
                    return self.json(200, view(int(m.group(1))))
            if path.startswith("/api/"):
                return self.json(404, {"error": "not found"})
            self.static(path)
        except Exception as e:   # never leak internals
            self.log_error("GET %s failed: %r", path, e)
            self.json(500, {"error": "something went wrong"})

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            body = self.body()
            if path == "/api/reset-demo":
                if not (allow("reset:" + self.ip(), 10, 600) and allow("reset:all", 30, 3600)):
                    return self.json(429, {"error": "too many resets, try again in a few minutes"})
                with lock:
                    return self.json(200, reset_demo())
            if path == "/api/situations":
                if not (allow("sit:" + self.ip(), 3, 600) and allow("sit:all", 30, 3600)):
                    return self.json(429, {"error": "a few per 10 minutes per visitor, please wait a moment"})
                if not isinstance(body.get("text"), str):
                    raise ValueError("text is required")
                with lock:
                    return self.json(200, add_situation(body["text"]))
            if path == "/api/try":
                if not (allow("try:" + self.ip(), 20, 600) and allow("try:all", 500, 3600)):
                    return self.json(429, {"error": "too many tries, please wait a few minutes"})
                with lock:
                    return self.json(200, new_try())
            m = CUSTOMER_PATH.match(path)
            if not m:
                return self.json(404, {"error": "not found"})
            cid, action, rid = int(m.group(1)), m.group(2), m.group(3)
            with lock:
                if not load(cid):
                    return self.json(404, {"error": "not found"})
                if action == "onboarding":
                    if not (allow("onb:" + self.ip(), 30, 600) and allow("onb:all", 300, 3600)):
                        return self.json(429, {"error": "busy, use the suggestions instead"})
                    draft = validate_goals(body.get("goals") or [])
                    return self.json(200, onboarding.turn(chat(body), summary(cid), True, draft))
                handlers = {"respond": lambda: respond(cid, body), "goals": lambda: save_goals(cid, body.get("goals")),
                            "add-goal": lambda: add_goal(cid, body.get("goal")),
                            "settings": lambda: settings(cid, body), "reset-memory": lambda: reset_memory(cid),
                            "revoke-rule": lambda: revoke_rule(cid, int(rid or 0)), "scenario": lambda: scenario(cid, body)}
                if action not in handlers:
                    return self.json(404, {"error": "not found"})
                return self.json(200, handlers[action]())
        except (ValueError, json.JSONDecodeError) as e:
            self.json(400, {"error": str(e)[:200]})
        except Exception as e:
            self.log_error("POST %s failed: %r", path, e)
            self.json(500, {"error": "something went wrong"})

    def static(self, path: str) -> None:
        f = (STATIC / path.lstrip("/")).resolve()
        if not f.is_relative_to(STATIC) or not f.is_file():
            f = STATIC / "index.html"   # single-page app
        if not f.is_file():
            return self.send(200, b"Frontend not built. Run: cd src/frontend && npm ci && npm run build", "text/plain")
        types = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css",
                 ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon", ".woff2": "font/woff2"}
        cache = "public, max-age=31536000, immutable" if "/assets/" in str(f) else "no-cache"
        self.send(200, f.read_bytes(), types.get(f.suffix, "application/octet-stream"), cache)


def chat(body: dict) -> list[dict]:
    """Validate the onboarding history coming from the browser."""
    hist = body.get("history")
    if not isinstance(hist, list) or len(hist) > 2 * onboarding.MAX_TURNS:
        raise ValueError("bad history")
    out = []
    for m in hist:
        if not isinstance(m, dict) or m.get("role") not in ("user", "assistant") or not isinstance(m.get("content"), str):
            raise ValueError("bad message")
        if len(m["content"]) > 500:
            raise ValueError("message too long (max 500 characters)")
        out.append({"role": m["role"], "content": m["content"]})
    if sum(m["role"] == "user" for m in out) > onboarding.MAX_TURNS:
        raise ValueError("that's the maximum number of turns, please confirm or use the chips")
    return out


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"KBC Autopilot on http://localhost:{port}  (AI: {'live' if ai.has_key() else 'offline fallback'})")
    ThreadingHTTPServer(("", port), Handler).serve_forever()
