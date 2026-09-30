"""Shared constants, value types and formatting. No I/O."""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date

# Demo clock: every date in the prototype is relative to this day, so the demo is reproducible.
TODAY = date(2026, 9, 30)
LANGS = ("en", "nl", "fr")

# Indicative rates on 30 Sep 2026, shown to customers as "indicative".
# ponytail: hard-coded rates, read them from KBC's pricing service in a real pilot.
RATES = {
    "current": 0.0,
    "savings": 0.007,          # KBC savings: 0.40% base + 0.30% loyalty, regulated, tax-free up to EUR 1,020 interest
    "term_gross": 0.020,       # 12-month term account, gross
    "withholding": 0.30,       # roerende voorheffing on term accounts
    "staatsbon_net": 0.0193,   # last 1-year state note (Sep 2026), net
}

KINDS = ("help", "product")
RISKS = ("critical", "normal", "regulated")
ACTIONS = ("transfer", "form", "options", "handoff", "info")
MODES = {"quiet": 50.0, "normal": 15.0, "proactive": 3.0}  # the bar "do nothing" sets per mode, in EUR
GOAL_TYPES = ("save_for", "buffer", "avoid_overdraft", "pay_off", "budget_cap",
              "raise_capital", "care_for_family", "other")
SAVING_GOALS = ("save_for", "buffer", "pay_off", "raise_capital", "care_for_family", "other")


@dataclass(frozen=True)
class Txn:
    day: date
    amount: float          # negative = money out
    counterparty: str
    description: str = ""


@dataclass
class Goal:
    id: int
    horizon: str           # "now" (stopover) | "long" (destination)
    type: str
    title: str
    target_eur: float
    saved_eur: float
    deadline: date
    priority: int
    monthly_eur: float     # current pace towards this goal
    # computed
    eta: date | None = None
    on_course: bool = True
    reached: bool = False

    @property
    def remaining(self) -> float:
        return max(0.0, self.target_eur - self.saved_eur)


@dataclass
class Instance:
    """One concrete occurrence of a situation for one customer."""
    key: str                          # stable id, e.g. "price_rise:TELENET"
    confidence: float = 0.9           # code confidence when no AI question is asked
    params: dict = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)   # "data used", already in plain words
    goal_id: int | None = None        # set when the instance is about one specific goal
    ai_text: str = ""                 # the text the AI question is about (payee, pattern, ...)


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    y, m = d.year + y, m + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def eur(x: float, decimals: int = 2) -> str:
    """Belgian money format for every language: EUR 2.450,00 -> '€ 2.450,00'."""
    sign = "−" if x < 0 else ""
    s = f"{abs(x):,.{decimals}f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    return f"{sign}€ {s}"


MONTHS = {
    "en": "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(),
    "nl": "jan feb mrt apr mei jun jul aug sep okt nov dec".split(),
    "fr": "janv. févr. mars avr. mai juin juil. août sept. oct. nov. déc.".split(),
}


def fmt_date(d: date, lang: str) -> str:
    return f"{d.day} {MONTHS[lang][d.month - 1]} {d.year}"


def fmt_month(d: date, lang: str) -> str:
    return f"{MONTHS[lang][d.month - 1]} {d.year}"
