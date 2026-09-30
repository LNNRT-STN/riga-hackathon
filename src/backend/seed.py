"""Builds a fresh demo database: 5 demo customers + 2,000 synthetic ones. Fully deterministic.

    python seed.py            # build the DB
    python seed.py --warm     # also pre-compute AI answers into ai_cache.json (needs OPENROUTER_API_KEY)
"""
from __future__ import annotations

import hashlib
import json
import random
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

from core import TODAY, add_months

HERE = Path(__file__).parent
POPULATION = 2000
START = date(2026, 7, 1)   # three months of history

GROCERIES = ["COLRUYT", "DELHAIZE", "ALDI", "LIDL", "ALBERT HEIJN", "CARREFOUR MARKET"]
DAY_TO_DAY = ["BAKKERIJ", "APOTHEEK", "KRUIDVAT", "ACTION", "HEMA", "Q8", "TOTAL", "NMBS", "DE LIJN", "CAFE",
              "BRASSERIE", "ZARA", "DECATHLON", "IKEA", "BOL.COM", "COOLBLUE", "FNAC", "PANOS", "EXKI"]
SUBSCRIPTIONS = [("TELENET BV", 58), ("PROXIMUS", 49), ("ORANGE BELGIUM", 35), ("NETFLIX", 13.99),
                 ("SPOTIFY", 11.99), ("DISNEY PLUS", 9.99), ("DPG MEDIA", 24.5)]
ENERGY = [("ENGIE", 95), ("LUMINUS", 88), ("TOTALENERGIES POWER", 102)]
CLUBS = [("KFC HEIST", "LIDGELD U10 SEIZOEN 26-27"), ("HC LEUVEN", "LIDGELD HOCKEY JEUGD"),
         ("ZWEMCLUB MECHELEN", "LIDGELD ZWEMMEN"), ("JUDO KWAI GENT", "INSCHRIJVING SEIZOEN"),
         ("TC RAPID ANTWERPEN", "LIDMAATSCHAP TENNIS")]
# Signals for plain-language situations the jury can add live (pets, travel, gym, baby, car).
LIFESTYLE = {"pet": [("ZOOPLUS", 42), ("DIERENARTS PEETERS", 65), ("TOM&CO", 38)],
             "travel": [("RYANAIR", 189), ("BRUSSELS AIRLINES", 240), ("BOOKING.COM", 310)],
             "gym": [("BASIC-FIT", 29.99), ("JIMS FITNESS", 34.99)],
             "baby": [("PRENATAL", 120), ("KRUIDVAT BABY", 45), ("DREAMBABY", 160)],
             "car": [("D'IETEREN SERVICE", 340), ("VAB", 89), ("CARGLASS", 180)]}
NAMES = ["Emma", "Noah", "Olivia", "Arthur", "Louise", "Jules", "Mila", "Lucas", "Elena", "Victor", "Nora",
         "Finn", "Julie", "Vic", "Marie", "Wout", "Lotte", "Senne", "Fien", "Lars", "Amélie", "Hugo", "Inès", "Milan"]


def pkey(i: int) -> str:
    return "c_" + hashlib.sha256(f"kbc-autopilot-{i}".encode()).hexdigest()[:10]


def months():
    return [START, add_months(START, 1), add_months(START, 2)]


def monthly(cp: str, amount: float, dom: int, desc: str = "", amounts: list | None = None):
    """A payment on day `dom` of each of the last three months."""
    out = []
    for k, m in enumerate(months()):
        d = m.replace(day=min(dom, 28))
        if d <= TODAY:
            out.append((d, amounts[k] if amounts else amount, cp, desc))
    return out


def daily_life(rng: random.Random, per_day: float, groceries_per_week: float = 2.0):
    """Groceries and day-to-day spending spread over the history."""
    out, d = [], START
    shops = rng.sample(GROCERIES, 3)
    small = rng.sample(DAY_TO_DAY, 8)
    while d <= TODAY:
        if rng.random() < groceries_per_week / 7:
            out.append((d, -round(rng.uniform(25, 95) * per_day / 25, 2), rng.choice(shops), "BETALING BANCONTACT"))
        if rng.random() < 0.35:
            out.append((d, -round(rng.uniform(4, 28) * per_day / 25, 2), rng.choice(small), "BETALING BANCONTACT"))
        d += timedelta(days=1)
    return out


def life(rng: random.Random, salary: float, pay_day: int, housing: float, per_day: float,
         subs: int = 2, price_rise: bool = False):
    tx = monthly("WERKGEVER NV", salary, pay_day, "LOON")
    tx += monthly("HUUR / LENING", -housing, 1, "DOORLOPENDE OPDRACHT")
    cp, amt = rng.choice(ENERGY)
    tx += monthly(cp, -amt, rng.randint(10, 20), "DOMICILIERING ENERGIE")
    for i, (cp, amt) in enumerate(rng.sample(SUBSCRIPTIONS, subs)):
        amounts = None
        if price_rise and i == 0:
            new = round(amt * rng.uniform(1.12, 1.3), 2)
            amounts = [-amt, -amt, -new]
        tx += monthly(cp, -amt, rng.randint(5, 25), "DOMICILIERING", amounts)
    return tx + daily_life(rng, per_day)


def demo_customers():
    """Five people the jury can open. Their numbers are chosen so each shows a different situation."""
    r = random.Random(7)
    tom = monthly("WERKGEVER NV", 3200, 25, "LOON") + monthly("HUUR APPARTEMENT", -1050, 1, "DOORLOPENDE OPDRACHT") \
        + monthly("TELENET BV", -62, 12, "DOMICILIERING INTERNET + TV", [-62, -62, -76]) \
        + monthly("SPOTIFY", -11.99, 8, "DOMICILIERING") + monthly("ENGIE", -95, 15, "DOMICILIERING ENERGIE") \
        + daily_life(r, 30)
    sarah = monthly("WERKGEVER NV", 2480, 5, "LOON") + monthly("HUUR APPARTEMENT", -950, 1, "DOORLOPENDE OPDRACHT") \
        + monthly("KBC AUTOLENING", -289, 2, "AFLOSSING") + monthly("LUMINUS", -112, 3, "DOMICILIERING ENERGIE") \
        + monthly("PROXIMUS", -49, 20, "DOMICILIERING") + daily_life(r, 22)
    an = monthly("FEDERALE PENSIOENDIENST", 1890, 25, "PENSIOEN") + monthly("ENGIE", -84, 12, "DOMICILIERING ENERGIE") \
        + monthly("DPG MEDIA", -24.5, 3, "ABONNEMENT KRANT") + daily_life(r, 18)
    lisa = monthly("WERKGEVER NV", 4100, 26, "LOON") + monthly("KBC WOONKREDIET", -1180, 1, "AFLOSSING") \
        + monthly("LUMINUS", -130, 14, "DOMICILIERING ENERGIE") + monthly("ORANGE BELGIUM", -35, 9, "DOMICILIERING") \
        + monthly("NETFLIX", -13.99, 17, "DOMICILIERING") + daily_life(r, 45) \
        + [(date(2026, 9, 16), -260.0, "KFC HEIST", "LIDGELD U10 SEIZOEN 26-27")]
    sam = monthly("WERKGEVER NV", 2450, 28, "LOON") + monthly("HUUR STUDIO", -780, 1, "DOORLOPENDE OPDRACHT") \
        + monthly("TELENET BV", -45, 11, "DOMICILIERING") + monthly("BASIC-FIT", -29.99, 4, "DOMICILIERING") \
        + daily_life(r, 26)
    pin = [{"type": "pin_reset", "day": date(2026, 9, d), "data": {"channel": ch, "device": "phone-1"}}
           for d, ch in ((4, "app"), (11, "app"), (19, "branch"), (26, "app"))]
    return [
        dict(name="Tom", persona="28 · bill went up · saving for a home", balance=2900, savings=9400, txns=tom,
             products={"mutualiteit": "CM"},
             goals=[("long", "save_for", "House deposit", 40000, 12400, "2031-06-30", 1, 480),
                    ("now", "save_for", "Ski trip", 600, 200, "2027-02-01", 2, 100)]),
        dict(name="Sarah", persona="34 · bills before payday", balance=1352, savings=2400, txns=sarah,
             products={"mutualiteit": "Helan"},
             goals=[("long", "buffer", "Safety buffer", 5000, 2400, "2027-12-31", 1, 150)]),
        dict(name="An", persona="78 · trouble logging in", balance=700, savings=14800, txns=an, events=pin,
             products={"mutualiteit": "CM"},
             goals=[("long", "care_for_family", "Grandchildren's studies", 3000, 1200, "2028-09-01", 1, 100)]),
        dict(name="Lisa", persona="41 · two kids · deposit matures", balance=3900, savings=6100, txns=lisa,
             products={"mutualiteit": "Helan", "term deposit": {"amount": 10000, "matures": "2026-10-15"}},
             goals=[("long", "save_for", "Family holiday", 3000, 1200, "2027-07-01", 1, 200)]),
        dict(name="Sam", persona="26 · new customer · no goals yet", balance=2100, savings=1500, txns=sam,
             products={"mutualiteit": "Helan"}, goals=[], onboarded=0),
    ]


def synthetic(i: int, rng: random.Random) -> dict:
    """One synthetic customer. The engine never sees the archetype; situations are planted at realistic rates."""
    arch = rng.choices(["student", "young", "family", "senior", "saver", "single"], [10, 25, 25, 15, 10, 15])[0]
    salary = {"student": 900, "young": 2500, "family": 4200, "senior": 1900, "saver": 3400, "single": 2800}[arch]
    salary = round(salary * rng.uniform(0.8, 1.25), -1)
    housing = round(salary * rng.uniform(0.25, 0.38), -1)
    per_day = salary / 110 * rng.uniform(0.8, 1.2)
    tx = life(rng, salary, rng.choice([1, 5, 25, 26, 28]), housing, per_day, subs=rng.randint(1, 3),
              price_rise=rng.random() < 0.12)
    balance = round(rng.uniform(0.6, 1.6) * salary, 2)
    if rng.random() < 0.05:   # payments land before income
        balance = round(housing * rng.uniform(0.6, 0.95), 2)
    events, products = [], {"mutualiteit": rng.choice(["Helan", "CM", "Solidaris", "Partena"])}
    if arch == "family" and rng.random() < 0.3:
        cp, desc = rng.choice(CLUBS)
        tx.append((TODAY - timedelta(days=rng.randint(3, 50)), -float(rng.choice([180, 220, 260, 310])), cp, desc))
    if arch == "senior" and rng.random() < 0.25:
        dev = "phone-1" if rng.random() < 0.8 else None
        for k in range(rng.randint(3, 6)):
            events.append({"type": "pin_reset", "day": TODAY - timedelta(days=rng.randint(1, 29)),
                           "data": {"channel": rng.choice(["app", "app", "branch"]), "device": dev or f"device-{k}"}})
    if rng.random() < (0.15 if arch in ("saver", "senior") else 0.03):
        what = rng.choice(["term deposit", "state note"])
        products[what] = {"amount": float(rng.choice([5000, 10000, 15000, 25000])),
                          "matures": str(TODAY + timedelta(days=rng.randint(-20, 60)))}
    for kind, p in (("pet", 0.07), ("travel", 0.2), ("gym", 0.15), ("baby", 0.03), ("car", 0.1)):
        if rng.random() < p:
            cp, amt = rng.choice(LIFESTYLE[kind])
            for _ in range(rng.randint(1, 3)):
                tx.append((START + timedelta(days=rng.randint(0, 91)), -round(amt * rng.uniform(0.8, 1.2), 2), cp, ""))
    goals = []
    if rng.random() < 0.45:
        for p in range(1, rng.randint(1, 2) + 1):
            gtype, title, target = rng.choice([("save_for", "House deposit", 30000), ("save_for", "Car", 12000),
                                               ("buffer", "Safety buffer", 6000), ("save_for", "Trip", 2500),
                                               ("pay_off", "Pay off loan", 4000)])
            deadline = add_months(TODAY, rng.randint(4, 60))
            saved = round(target * rng.uniform(0, 0.9), -1)
            goals.append(("long" if (deadline - TODAY).days > 183 else "now", gtype, title, target, saved,
                          str(deadline), p, round(rng.uniform(0, 400), -1)))
    return dict(name=rng.choice(NAMES), persona=arch, balance=balance, savings=round(rng.uniform(0, 3) * salary, -1),
                txns=tx, events=events, products=products, goals=goals,
                mode=rng.choices(["quiet", "normal", "proactive"], [20, 70, 10])[0],
                consent_help=int(rng.random() < 0.85), consent_product=int(rng.random() < 0.55),
                holdout=int(rng.random() < 0.10))


def insert(conn: sqlite3.Connection, cid: int, c: dict) -> None:
    conn.execute("INSERT INTO customer (id, pkey, balance, savings, products, mode, consent_help, consent_product, "
                 "holdout, onboarded) VALUES (?,?,?,?,?,?,?,?,?,?)",
                 (cid, pkey(cid), c["balance"], c["savings"], json.dumps(c["products"]), c.get("mode", "normal"),
                  c.get("consent_help", 1), c.get("consent_product", 1), c.get("holdout", 0), c.get("onboarded", 1)))
    conn.execute("INSERT INTO identity VALUES (?,?,?)", (cid, c["name"], c["persona"]))
    conn.executemany("INSERT INTO txn (customer_id, day, amount, counterparty, description) VALUES (?,?,?,?,?)",
                     [(cid, str(d), round(a, 2), cp, desc) for d, a, cp, desc in c["txns"] if d <= TODAY])
    conn.executemany("INSERT INTO event (customer_id, type, day, data) VALUES (?,?,?,?)",
                     [(cid, e["type"], str(e["day"]), json.dumps(e["data"])) for e in c.get("events", [])])
    conn.executemany("INSERT INTO goal (customer_id, horizon, type, title, target_eur, saved_eur, deadline, priority, "
                     "monthly_eur) VALUES (?,?,?,?,?,?,?,?,?)", [(cid, *g) for g in c["goals"]])


DEMO_IDS = range(1, 6)


def build(path: Path) -> sqlite3.Connection:
    path.unlink(missing_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.executescript((HERE / "schema.sql").read_text())
    for cid, c in enumerate(demo_customers(), start=1):
        insert(conn, cid, c)
    rng = random.Random(42)
    for i in range(POPULATION):
        insert(conn, 100 + i, synthetic(i, rng))
    conn.commit()
    return conn


if __name__ == "__main__":
    db = HERE / "autopilot.db"
    build(db)
    print(f"built {db}")
    if "--warm" in sys.argv:
        import server   # noqa: E402 (needs the built DB)
        server.warm()
