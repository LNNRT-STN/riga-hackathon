"""The situation catalogue. A new situation is one row here; the engine has no situation-specific code."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from core import RATES, SAVING_GOALS, Instance, eur, fmt_date


@dataclass(frozen=True)
class Situation:
    id: str
    name: str                     # short name for lists
    audience: str                 # who it typically helps (display only)
    kind: str                     # help | product
    risk: str                     # critical | normal | regulated
    action: str                   # transfer | form | options | handoff | info
    detect: Callable              # code prefilter: Features -> list[Instance]
    question: str | None          # AI yes/no question about inst.ai_text; None = code is certain
    fallback: Callable | None     # offline stand-in for the AI answer: Instance -> probability
    customer_eur: Callable        # (Features, Instance) -> yearly EUR value for the customer. Drives the score.
    kbc_eur: Callable             # (Features, Instance) -> EUR for KBC. Logged only, never ranks.
    serves: tuple                 # goal types this can move forward
    title: str
    body: str
    benefit: str
    options: Callable | None = None   # (Features, Instance) -> list of option dicts
    monthly_saving: Callable | None = None  # (Features, Instance) -> EUR/month freed, routed to the linked goal


def kw(words: tuple, hit: float = 0.9, miss: float = 0.1) -> Callable:
    """Offline fallback: keyword match on the text the AI would judge."""
    return lambda inst: hit if any(w in inst.ai_text.lower() for w in words) else miss


def best_rate() -> float:
    return max(RATES["savings"], RATES["term_gross"] * (1 - RATES["withholding"]), RATES["staatsbon_net"])


def money_options(amount: float, source: str, with_bolero: bool) -> list[dict]:
    """Honest after-tax comparison. The KBC option is pre-filled, not the only one."""
    term_net = RATES["term_gross"] * (1 - RATES["withholding"])
    opts = [
        {"id": "savings", "type": "transfer", "kbc": True, "from": source, "to": "savings", "amount": amount,
         "label": "Move it to your KBC savings account",
         "detail": f"{RATES['savings']:.2%} a year, interest tax-free up to € 1.020. About {eur(amount * RATES['savings'])} a year."},
        {"id": "term", "type": "transfer", "kbc": True, "from": source, "to": "term", "amount": amount,
         "label": "12-month KBC term account",
         "detail": f"{RATES['term_gross']:.2%} gross, {term_net:.2%} after 30% withholding tax. About {eur(amount * term_net)} a year."},
        {"id": "staatsbon", "type": "info", "kbc": False,
         "label": "Next Belgian state note (staatsbon)",
         "detail": f"The last 1-year issue paid {RATES['staatsbon_net']:.2%} net, about {eur(amount * RATES['staatsbon_net'])} a year. Not a KBC product; subscribe when the next issue opens."},
    ]
    if with_bolero:
        opts.append({"id": "advisor", "type": "handoff", "kbc": True, "advisor": "KBC investment advisor",
                     "label": "Talk to an advisor about investing (Bolero)",
                     "detail": "Investing needs a suitability check, so a person helps you with this."})
    return opts


# ---------- detectors ----------

def d_cash_shortage(f) -> list[Instance]:
    if f.forecast_min >= 0 or f.savings <= 0:
        return []
    amount = min(f.savings, math.ceil((-f.forecast_min + 50) / 10) * 10)
    return [Instance(
        key=f"cash_shortage:{f.forecast_min_day}", confidence=0.9,
        params={"low_day": f.forecast_min_day, "short_eur": -f.forecast_min, "amount_eur": amount},
        evidence=[f"Current balance: {eur(f.balance)}"] + f.forecast_evidence,
    )]


def d_price_rise(f) -> list[Instance]:
    return [Instance(
        key=f"price_rise:{r['cp']}", ai_text=f"{r['cp']} ({r['description']})",
        params={"merchant": r["cp"], "old_eur": r["old"], "new_eur": r["new"],
                "delta_eur": r["new"] - r["old"], "year_eur": (r["new"] - r["old"]) * 12},
        evidence=[f"{r['cp']}: " + ", ".join(eur(a) for a in r["history"]) + " (last 3 months)"],
    ) for r in f.price_rises]


INSURER_REFUND = {"Helan": 50.0, "CM": 15.0}


def d_new_payee(f) -> list[Instance]:
    insurer = f.products.get("mutualiteit", "your health insurer")
    refund = INSURER_REFUND.get(insurer, 20.0)
    return [Instance(
        key=f"sports_club:{p['cp']}", ai_text=f"{p['cp']} – {p['description']}",
        params={"club": p["cp"], "fee_eur": p["amount"], "insurer": insurer, "refund_eur": min(refund, p["amount"])},
        evidence=[f"New payment on {fmt_date(p['day'], 'en')}: {p['cp']} – {p['description']} ({eur(-p['amount'])})",
                  f"Health insurer on file: {insurer}"],
    ) for p in f.new_payees]


def d_pin(f) -> list[Instance]:
    if f.pin_resets_30d < 3:
        return []
    log = "; ".join(f"PIN reset {fmt_date(e['day'], 'en')} via {e['channel']}" for e in f.pin_events)
    return [Instance(
        key=f"pin:{f.today:%Y-%m}", ai_text=f"{log}; same device each time: {f.same_device}",
        params={"count": f.pin_resets_30d},
        evidence=[f"{f.pin_resets_30d} PIN resets in the last 30 days", f"Same device each time: {'yes' if f.same_device else 'no'}"],
    )]


def d_budget_room(f) -> list[Instance]:
    goals = sorted((g for g in f.goals if not g.reached and g.type in SAVING_GOALS), key=lambda g: g.priority)
    if f.surplus < 100 or not goals:
        return []
    g = goals[0]
    amount = math.floor(min(f.surplus, g.remaining) / 10) * 10
    if amount < 50:
        return []
    keep = max(500, math.floor((f.balance - amount) / 50) * 50)
    return [Instance(
        key=f"budget_room:{g.id}:{f.today:%Y-%m}", confidence=0.85, goal_id=g.id,
        params={"goal": g.title, "amount_eur": amount, "keep_eur": keep, "cap_eur": math.ceil(amount / 100) * 100},
        evidence=[f"Current balance: {eur(f.balance)}",
                  f"Lowest expected balance in the next 14 days: {eur(f.forecast_min)}",
                  f"You usually spend {eur(f.monthly_spend)} a month"],
    )]


def d_maturity(f) -> list[Instance]:
    m = f.maturity
    if not m or not (0 < m["days"] <= 30):
        return []
    return [Instance(
        key=f"maturity:{m['day']}", confidence=1.0,
        params={"amount_eur": m["amount"], "day": m["day"], "what": m["what"], "best_eur": m["amount"] * best_rate()},
        evidence=[f"{m['what'].capitalize()} of {eur(m['amount'])} matures on {fmt_date(m['day'], 'en')}"],
    )]


# ---------- the catalogue ----------

SITUATIONS: list[Situation] = [
    Situation(
        id="cash_shortage", name="Cash shortage ahead", audience="Everyone",
        kind="help", risk="critical", action="transfer",
        detect=d_cash_shortage, question=None, fallback=None,
        customer_eur=lambda f, i: 15 + 0.1 * i.params["short_eur"],
        kbc_eur=lambda f, i: 0.0,
        serves=("avoid_overdraft", "buffer"),
        title="Your balance may dip below zero on {low_day}",
        body="Several scheduled payments are due before new money comes in. Moving {amount_eur} from your savings keeps you above zero.",
        benefit="Avoids going {short_eur} into the red",
        options=lambda f, i: [{"id": "move", "type": "transfer", "kbc": False, "from": "savings", "to": "current",
                               "amount": i.params["amount_eur"], "label": "Move money from savings", "detail": ""}],
    ),
    Situation(
        id="price_rise", name="Bill went up", audience="Everyone",
        kind="help", risk="normal", action="options",
        detect=d_price_rise,
        question="Is '{text}' a subscription, utility or insurance contract (for example telecom, streaming, energy or insurance) that a customer could renegotiate or switch?",
        fallback=kw(("telenet", "proximus", "orange", "netflix", "spotify", "engie", "luminus", "disney", "base", "scarlet")),
        customer_eur=lambda f, i: i.params["year_eur"],
        kbc_eur=lambda f, i: 0.0,
        serves=SAVING_GOALS,
        title="{merchant} went up by {delta_eur} a month",
        body="Your {merchant} payment went from {old_eur} to {new_eur}. Comparing offers or asking for a better rate often brings it back down.",
        benefit="Could save about {year_eur} a year",
        options=lambda f, i: [
            {"id": "compare", "type": "info", "kbc": False, "label": "Compare offers",
             "detail": "Use an independent comparison site. Autopilot doesn't earn anything from your choice."},
            {"id": "ask", "type": "info", "kbc": False, "label": f"Ask {i.params['merchant']} for a better rate",
             "detail": f"Mention you used to pay {eur(i.params['old_eur'])}. Providers often have retention offers."},
        ],
        monthly_saving=lambda f, i: i.params["delta_eur"],
    ),
    Situation(
        id="sports_club", name="Sports club fee refund", audience="Families",
        kind="help", risk="normal", action="form",
        detect=d_new_payee,
        question="Is the payment '{text}' a membership fee for a sports club, such as football, hockey, swimming, judo or tennis?",
        fallback=kw(("club", "kfc", "fc ", "vv ", "lidgeld", "sport", "hockey", "judo", "zwem", "voetbal", "tennis", "basket")),
        customer_eur=lambda f, i: i.params["refund_eur"],
        kbc_eur=lambda f, i: -24.0,   # the sports insurance we deliberately don't sell: a trust investment
        serves=SAVING_GOALS,
        title="A sports club fee: part of it comes back",
        body="You paid {fee_eur} to {club}. Club members are usually insured through their sports federation, so you don't need extra insurance. {insurer} refunds up to {refund_eur} of the fee.",
        benefit="{refund_eur} back from {insurer}",
        options=lambda f, i: [{"id": "form", "type": "form", "kbc": False, "label": f"Refund request for {i.params['insurer']}",
                               "fields": {"Health insurer": i.params["insurer"], "Club": i.params["club"],
                                          "Fee paid": eur(i.params["fee_eur"]), "Refund asked": eur(i.params["refund_eur"])},
                               "detail": "We fill in the form. You check it and send it."}],
    ),
    Situation(
        id="pin_friction", name="Trouble logging in", audience="Seniors",
        kind="help", risk="normal", action="handoff",
        detect=d_pin,
        question="Does this pattern ('{text}') look like a customer struggling to remember their code, rather than someone else trying to break in?",
        fallback=lambda i: 0.85 if "same device each time: True" in i.ai_text else 0.2,
        customer_eur=lambda f, i: 40.0,
        kbc_eur=lambda f, i: 15.0,    # fewer support calls
        serves=(),
        title="Logging in has been difficult lately",
        body="Your PIN was reset {count} times this month. It can be easier: someone you trust can help with your banking, or an advisor can set up a simpler way to log in with you.",
        benefit="Less hassle, and you stay in control",
        options=lambda f, i: [
            {"id": "family", "type": "form", "kbc": False, "label": "Let a family member help (volmacht)",
             "fields": {"Access": "View only, or view and prepare payments", "Who decides": "You. You can stop it any time.",
                        "Family member": "Chosen by you on the next screen"},
             "detail": "They get their own login. You choose what they can see or do."},
            {"id": "advisor", "type": "handoff", "kbc": True, "advisor": "KBC care advisor",
             "label": "Talk to a KBC advisor", "detail": "They'll call you to find an easier way to log in. No need to repeat your story."},
        ],
    ),
    Situation(
        id="budget_room", name="Room to top up a goal", audience="Goal setters",
        kind="help", risk="normal", action="transfer",
        detect=d_budget_room, question=None, fallback=None,
        customer_eur=lambda f, i: i.params["amount_eur"] * 0.05 + 10,   # progress on a goal the customer set
        kbc_eur=lambda f, i: i.params["amount_eur"] * 0.013,
        serves=SAVING_GOALS,
        title="{amount_eur} spare this month",
        body="After your scheduled payments you'll still have {amount_eur} more than you usually need. Put it towards {goal}?",
        benefit="{amount_eur} closer to {goal}",
        options=lambda f, i: [{"id": "move", "type": "transfer", "kbc": False, "from": "current", "to": f"goal:{i.goal_id}",
                               "amount": i.params["amount_eur"], "label": f"Move it to {i.params['goal']}", "detail": "",
                               "always": {"keep": i.params["keep_eur"], "cap": i.params["cap_eur"]}}],
    ),
    Situation(
        id="maturity", name="Deposit matures", audience="Savers",
        kind="product", risk="normal", action="options",
        detect=d_maturity, question=None, fallback=None,
        customer_eur=lambda f, i: i.params["best_eur"],
        kbc_eur=lambda f, i: i.params["amount_eur"] * 0.015,   # deposit kept at KBC
        serves=SAVING_GOALS,
        title="Your {amount_eur} {what} is freed up on {day}",
        body="When it matures, the money lands on your current account, where it earns nothing. Here are your options after tax, including the state note.",
        benefit="Up to about {best_eur} a year",
        options=lambda f, i: money_options(i.params["amount_eur"], "current", with_bolero=True),
    ),
]

BY_ID = {s.id: s for s in SITUATIONS}
