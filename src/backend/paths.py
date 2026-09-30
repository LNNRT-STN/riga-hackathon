"""Suggested goals: what Autopilot proposes from life signals and the customer's Payconiq circle.
One row per life event; suggest() has no event-specific code."""
from __future__ import annotations

from dataclasses import dataclass

from core import TODAY, add_months


@dataclass(frozen=True)
class Path:
    key: str
    title: str
    type: str
    target_eur: float
    months: int
    own: tuple            # keywords in the customer's own payments (lower-case)
    reason: str
    peer: tuple = ()      # keywords in a circle goal title (lower-case)


PATHS: list[Path] = [
    Path("baby", "Studies for your child", "save_for", 25000, 18 * 12,
         ("prenatal", "dreambaby", "kruidvat baby", "luiers", "pampers"),
         "Baby shops in your payments. Studies start in about 18 years; small monthly amounts add up by then."),
    Path("wedding", "Wedding ring", "save_for", 3000, 12, ("bloemen", "fleurs", "flower", "juwelier", "jewel"),
         "Flowers or jewellery in your payments. A ring is a big one-off; saving a year ahead keeps it calm.", ("ring", "wedding")),
    Path("travel", "Next trip", "save_for", 1500, 6, ("ryanair", "brussels airlines", "booking.com"),
         "You travel. A trip you save for in advance never lands on your current account.", ("trip", "holiday", "travel")),
    Path("car", "Next car", "save_for", 12000, 36, ("d'ieteren", "vab", "carglass"),
         "Car costs in your payments. Saving for the next one avoids a loan later.", ("car",)),
    Path("pet", "Vet buffer", "buffer", 800, 12, ("zooplus", "dierenarts", "tom&co"),
         "Pet shops and vets in your payments. Vet bills come unannounced."),
    Path("home", "Own home", "save_for", 40000, 72, ("immoweb", "notaris"),
         "House hunting in your payments. A deposit takes years; starting now makes it real.", ("home", "house", "flat")),
]


def suggest(txns, peer_goals: list[dict], goals, today=TODAY) -> list[dict]:
    """Top 3 paths the customer does not have yet. Score: own signal 1, circle signal 1."""
    # ponytail: circle counts of 1 are shown; a real pilot needs k-anonymity (k >= 5 peers) before a circle signal is used.
    have = {g.title.lower() for g in goals}
    have_buffer = any(g.type == "buffer" for g in goals)
    out = []
    for p in PATHS:
        if p.title.lower() in have or (p.type == "buffer" and have_buffer):
            continue
        shops = sorted({t.counterparty for t in txns if any(w in f"{t.counterparty} {t.description}".lower() for w in p.own)})
        circle = sum(any(w in g["title"].lower() for w in p.peer) for g in peer_goals) if p.peer else 0
        if not shops and not circle:
            continue
        evidence = []
        if shops:
            evidence.append("Payments to " + ", ".join(shops[:3]))
        if circle:
            evidence.append(f"{circle} {'person' if circle == 1 else 'people'} in your Payconiq circle set a similar goal")
        deadline = add_months(today, p.months)
        out.append({"key": p.key, "title": p.title, "type": p.type, "horizon": "now" if p.months <= 6 else "long",
                    "target_eur": float(p.target_eur), "deadline": str(deadline), "reason": p.reason, "evidence": evidence,
                    "source": "both" if shops and circle else "life" if shops else "circle"})
    out.sort(key=lambda s: {"both": 0, "life": 1, "circle": 2}[s["source"]])
    return out[:3]
