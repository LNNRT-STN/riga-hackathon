-- KBC Autopilot prototype schema. Recreated from the seed on every start (demo data is synthetic).
PRAGMA journal_mode = WAL;

-- Pseudonymised customer record: the only thing the engine and AI ever see.
CREATE TABLE customer (
  id            INTEGER PRIMARY KEY,
  pkey          TEXT NOT NULL UNIQUE,          -- pseudonymous key, used in AI state and logs
  balance       REAL NOT NULL,                 -- current account
  savings       REAL NOT NULL,
  products      TEXT NOT NULL DEFAULT '{}',    -- JSON: insurer, deposits, ...
  mode          TEXT NOT NULL DEFAULT 'normal' CHECK (mode IN ('quiet', 'normal', 'proactive')),
  consent_help  INTEGER NOT NULL DEFAULT 1,    -- KBC "Extra gebruiksgemak"
  consent_product INTEGER NOT NULL DEFAULT 1,  -- KBC "Op jouw maat"
  holdout       INTEGER NOT NULL DEFAULT 0,    -- measurement group: no non-critical cards
  onboarded     INTEGER NOT NULL DEFAULT 1,
  value_created REAL NOT NULL DEFAULT 0,       -- EUR/year the customer accepted
  product_pause_until TEXT,
  last_product_response TEXT
);

-- Directly identifying data lives apart and never leaves the app layer.
CREATE TABLE identity (
  customer_id INTEGER PRIMARY KEY REFERENCES customer(id),
  display_name TEXT NOT NULL,
  persona TEXT NOT NULL DEFAULT ''             -- demo picker subtitle
);

CREATE TABLE txn (
  id INTEGER PRIMARY KEY,
  customer_id INTEGER NOT NULL REFERENCES customer(id),
  day TEXT NOT NULL,
  amount REAL NOT NULL,                        -- negative = money out
  counterparty TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  peer_id INTEGER                              -- the other customer in a Payconiq payment, else NULL
);
CREATE INDEX txn_customer ON txn(customer_id, day);

CREATE TABLE event (
  id INTEGER PRIMARY KEY,
  customer_id INTEGER NOT NULL REFERENCES customer(id),
  type TEXT NOT NULL,
  day TEXT NOT NULL,
  data TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE goal (
  id INTEGER PRIMARY KEY,
  customer_id INTEGER NOT NULL REFERENCES customer(id),
  horizon TEXT NOT NULL CHECK (horizon IN ('now', 'long')),
  type TEXT NOT NULL,
  title TEXT NOT NULL,
  target_eur REAL NOT NULL CHECK (target_eur > 0),
  saved_eur REAL NOT NULL DEFAULT 0,
  deadline TEXT NOT NULL,
  priority INTEGER NOT NULL,
  monthly_eur REAL NOT NULL DEFAULT 0
);

-- "Always do this": standing rules the customer approved once. Own accounts only, capped, revocable.
CREATE TABLE rule (
  id INTEGER PRIMARY KEY,
  customer_id INTEGER NOT NULL REFERENCES customer(id),
  goal_id INTEGER NOT NULL REFERENCES goal(id),
  keep REAL NOT NULL,
  cap REAL NOT NULL CHECK (cap > 0),
  active INTEGER NOT NULL DEFAULT 1,
  created TEXT NOT NULL
);

-- What the customer taught Autopilot, per situation. Visible and resettable in "Memory".
CREATE TABLE pref (
  customer_id INTEGER NOT NULL REFERENCES customer(id),
  situation_id TEXT NOT NULL,
  ignores INTEGER NOT NULL DEFAULT 0,
  accepted INTEGER NOT NULL DEFAULT 0,
  suppressed INTEGER NOT NULL DEFAULT 0,
  snoozed_until TEXT,
  PRIMARY KEY (customer_id, situation_id)
);

CREATE TABLE resolved (
  customer_id INTEGER NOT NULL REFERENCES customer(id),
  instance_key TEXT NOT NULL,
  PRIMARY KEY (customer_id, instance_key)
);

-- Append-only decision log: every response and every autopilot action (the audit trail).
CREATE TABLE decision (
  id INTEGER PRIMARY KEY,
  customer_id INTEGER NOT NULL REFERENCES customer(id),
  day TEXT NOT NULL,
  situation_id TEXT NOT NULL,
  instance_key TEXT NOT NULL,
  response TEXT NOT NULL,                      -- approve | later | not_relevant | autopilot
  option_id TEXT,
  customer_eur REAL NOT NULL DEFAULT 0,
  kbc_eur REAL NOT NULL DEFAULT 0,
  note TEXT NOT NULL DEFAULT ''
);

-- Situations added in plain language from "Behind the scenes" (screening only).
CREATE TABLE situation_custom (
  id INTEGER PRIMARY KEY,
  text TEXT NOT NULL,
  sample INTEGER NOT NULL,
  matches INTEGER NOT NULL,
  source TEXT NOT NULL
);
