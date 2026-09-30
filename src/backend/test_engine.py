"""Checks for the parts that must not break. Run: python -m unittest (from src/backend)."""
import json
import unittest
from datetime import date, timedelta

import ai
import onboarding
from core import TODAY, Goal, Txn, eur
from engine import (candidates, decide, features, questions, respond_update, rule_allowed, rule_amount,
                    validate_goals)
from paths import suggest
from situations import BY_ID


def monthly(cp, amounts, dom):
    return [Txn(date(2026, m, dom), a, cp, "DOMICILIERING") for m, a in zip((7, 8, 9), amounts)]


def customer(**kw):
    return {"mode": "normal", "consent_help": 1, "consent_product": 1, "holdout": 0,
            "product_pause_until": None, "last_product_response": None, **kw}


def run(txns, balance=2000.0, savings=5000.0, products=None, events=None, goals=None, cust=None, prefs=None,
        resolved=None):
    f = features(txns, balance, savings, products or {}, events or [], goals or [])
    cands = candidates(f)
    _, fallbacks = questions(f, cands)
    card, opts, bar = decide(cust or customer(), f, cands, fallbacks, prefs or {}, resolved or set())
    return f, card, {o.situation.id: o for o in opts}


SALARY = monthly("WERKGEVER NV", [2500] * 3, 5)
RENT = monthly("HUUR", [-950] * 3, 1)


class Engine(unittest.TestCase):
    def test_forecast_finds_shortfall_before_payday(self):
        f, card, _ = run(SALARY + RENT + monthly("LENING", [-400] * 3, 2), balance=1000)
        self.assertLess(f.forecast_min, 0)
        self.assertEqual(card.situation.id, "cash_shortage")

    def test_price_rise_detected(self):
        f, _, _ = run(SALARY + monthly("TELENET BV", [-62, -62, -76], 12))
        self.assertEqual([(r["cp"], r["old"], r["new"]) for r in f.price_rises], [("TELENET BV", 62, 76)])

    def test_do_nothing_wins_below_the_bar(self):
        # a EUR 1/month rise is real but not worth a message in quiet mode
        _, card, opts = run(SALARY + monthly("SPOTIFY", [-10.99, -10.99, -12.0], 8), cust=customer(mode="quiet"))
        self.assertIsNone(card)
        self.assertEqual(opts["price_rise"].status, "below_bar")

    def test_not_relevant_suppresses_but_critical_only_snoozes(self):
        tele = SALARY + monthly("TELENET BV", [-62, -62, -76], 12)
        _, card, _ = run(tele, prefs={"price_rise": {"suppressed": 1}})
        self.assertIsNone(card)
        pref, _ = respond_update({}, customer(), BY_ID["cash_shortage"], "not_relevant")
        self.assertEqual(pref["suppressed"], 0)
        self.assertEqual(pref["snoozed_until"], TODAY + timedelta(days=7))
        short = SALARY + RENT + monthly("LENING", [-400] * 3, 2)
        _, card, _ = run(short, balance=1000, prefs={"cash_shortage": {"suppressed": 1}})
        self.assertEqual(card.situation.id, "cash_shortage")

    def test_product_cards_need_consent_and_pause_after_rejection(self):
        deposit = {"term deposit": {"amount": 10000, "matures": str(TODAY + timedelta(days=15))}}
        _, card, _ = run(SALARY, products=deposit)
        self.assertEqual(card.situation.id, "maturity")
        _, card, opts = run(SALARY, products=deposit, cust=customer(consent_product=0))
        self.assertIsNone(card)
        self.assertEqual(opts["maturity"].status, "no_consent")
        _, cust = respond_update({}, customer(), BY_ID["maturity"], "not_relevant")
        self.assertEqual(cust["product_pause_until"], TODAY + timedelta(days=60))
        _, card, _ = run(SALARY, products=deposit, cust=customer(**cust))
        self.assertIsNone(card)

    def test_holdout_sees_no_normal_cards_but_still_critical(self):
        _, card, _ = run(SALARY + monthly("TELENET BV", [-62, -62, -76], 12), cust=customer(holdout=1))
        self.assertIsNone(card)
        _, card, _ = run(SALARY + RENT + monthly("LENING", [-400] * 3, 2), balance=1000, cust=customer(holdout=1))
        self.assertEqual(card.situation.id, "cash_shortage")

    def test_goal_weight_lifts_a_card_that_serves_a_goal(self):
        tele = SALARY + monthly("TELENET BV", [-62, -62, -76], 12)
        _, _, plain = run(tele)
        goal = Goal(1, "long", "save_for", "House", 40000, 5000, date(2031, 1, 1), 1, 400)
        _, card, linked = run(tele, goals=[goal])
        self.assertGreater(linked["price_rise"].score, plain["price_rise"].score)
        self.assertEqual(card.goal.title, "House")

    def test_off_course_goal(self):
        f, _, _ = run(SALARY, goals=[Goal(1, "long", "save_for", "House", 40000, 0, date(2027, 6, 1), 1, 100)])
        self.assertFalse(f.goals[0].on_course)

    def test_standing_rule_respects_cap_and_scope(self):
        self.assertEqual(rule_amount({"keep": 1500, "cap": 300}, 2400, 0), 300)
        self.assertEqual(rule_amount({"keep": 1500, "cap": 300}, 2400, 250), 50)
        self.assertEqual(rule_amount({"keep": 1500, "cap": 300}, 1200, 0), 0)
        move = {"type": "transfer", "to": "goal:1", "always": {"keep": 1500, "cap": 300}}
        self.assertTrue(rule_allowed(BY_ID["budget_room"], move))
        self.assertFalse(rule_allowed(BY_ID["maturity"], move))        # product
        self.assertFalse(rule_allowed(BY_ID["cash_shortage"], move))   # critical
        self.assertFalse(rule_allowed(BY_ID["budget_room"], {**move, "to": "iban:BE00"}))


class Safety(unittest.TestCase):
    def test_ai_state_has_no_personal_data(self):
        import server
        f = server.evaluate(1, live=False)[2]
        state = json.dumps(server.ai_state(f))
        for leak in ("Tom", "BE", "@", "straat"):
            self.assertNotIn(leak, state)

    def test_pushy_or_wrong_amount_phrasing_is_rejected(self):
        need = [eur(14)]
        self.assertTrue(ai.tone_ok("Telenet went up by € 14,00 a month.", need))
        self.assertFalse(ai.tone_ok("Telenet went up by € 15,00 a month.", need))
        self.assertFalse(ai.tone_ok("Exclusive offer: save € 14,00 now!", need))

    def test_phrase_accepts_unspaced_euro(self):
        real = ai.llm_json
        ai.llm_json = lambda *a: {"title": "Bill went up by €14,00", "body": "It is now €76,00 a month."}
        try:
            self.assertEqual(ai.phrase("t", "b", [eur(14), eur(76)], True), ("Bill went up by € 14,00", "It is now € 76,00 a month."))
        finally:
            ai.llm_json = real

    def test_goal_validation(self):
        ok = {"title": "Ski trip", "type": "save_for", "horizon": "now", "target_eur": 600,
              "deadline": "2027-02-01", "priority": 1}
        self.assertEqual(len(validate_goals([ok])), 1)
        for bad in ({**ok, "type": "lottery"}, {**ok, "deadline": "2020-01-01"}, {**ok, "target_eur": -5},
                    {**ok, "horizon": "soon"}):
            with self.assertRaises(ValueError):
                validate_goals([bad])
        with self.assertRaises(ValueError):
            validate_goals([ok] * 6)

    def test_offline_onboarding_builds_a_goal_list(self):
        hist = [{"role": "user", "content": "Skiing in February for 600 euro, and one day my own flat, around 40k"}]
        out = onboarding.turn(hist, {"monthly_income": 2500, "monthly_spend": 2000, "monthly_room": 500,
                                     "savings": 1500}, live=False)
        goals = {g["title"]: g for g in out["goals"]}
        self.assertEqual(goals["Trip"]["target_eur"], 600)
        self.assertEqual(goals["Trip"]["horizon"], "now")
        self.assertEqual(goals["Own home"]["target_eur"], 40000)
        self.assertIn("is reached around", out["reply"])   # 40k at 200/month is later than the default date

    def test_offline_onboarding_reads_amounts_when_a_topic_matches_twice(self):
        hist = [{"role": "user", "content": "A citytrip in March for 800, and a safety buffer of 5000 by 2028"}]
        out = onboarding.turn(hist, {"monthly_income": 2500, "monthly_spend": 2000, "monthly_room": 500,
                                     "savings": 1500}, live=False)
        goals = {g["title"]: g for g in out["goals"]}
        self.assertEqual(goals["Trip"]["target_eur"], 800)
        self.assertEqual(goals["Safety buffer"]["target_eur"], 5000)
        self.assertEqual(goals["Safety buffer"]["deadline"], "2028-06-30")


class FlightPaths(unittest.TestCase):
    GOAL = {"title": "Trip", "type": "save_for", "horizon": "long", "target_eur": 3000, "deadline": "2027-12-01", "priority": 1}

    def test_diapers_suggest_studies_in_18_years(self):
        tx = SALARY + [Txn(date(2026, 9, 6), -38.5, "DREAMBABY", "LUIERS MAAT 2")]
        out = suggest(tx, [], [])
        self.assertEqual([s["title"] for s in out], ["Studies for your child"])
        self.assertEqual(out[0]["deadline"], "2044-09-30")
        self.assertEqual(out[0]["source"], "life")

    def test_flowers_plus_circle_rank_first(self):
        tx = SALARY + [Txn(date(2026, 9, 5), -35, "BLOEMEN VAN GOGH", ""), Txn(date(2026, 9, 1), -189, "RYANAIR", "")]
        out = suggest(tx, [{"title": "Wedding ring", "type": "save_for"}], [])
        self.assertEqual(out[0]["title"], "Wedding ring")
        self.assertEqual(out[0]["source"], "both")
        self.assertIn("1 person in your Payconiq circle set a similar goal", out[0]["evidence"])
        self.assertEqual(out[1]["source"], "life")
        # a title already in the plan is not suggested again
        have = [Goal(1, "long", "save_for", "wedding ring", 3000, 0, date(2027, 9, 1), 1, 100)]
        self.assertNotIn("Wedding ring", [s["title"] for s in suggest(tx, [], have)])

    def test_circle_needs_the_peers_consent(self):
        import server
        self.assertEqual(server.peer_goals(7), [{"title": "Wedding ring", "type": "save_for"}])
        server.db.execute("UPDATE customer SET consent_help = 0 WHERE id = 6")
        try:
            self.assertEqual(server.peer_goals(7), [])
            self.assertEqual(server.view(7)["suggestions"][0]["source"], "life")
        finally:
            server.db.execute("UPDATE customer SET consent_help = 1 WHERE id = 6")
        self.assertEqual(server.view(5)["suggestions"][0]["title"], "Studies for your child")

    def test_monthly_amount_is_validated_and_kept(self):
        self.assertEqual(validate_goals([{**self.GOAL, "monthly_eur": 150}])[0]["monthly_eur"], 150)
        self.assertEqual(validate_goals([self.GOAL])[0]["monthly_eur"], 0)
        with self.assertRaises(ValueError):
            validate_goals([{**self.GOAL, "monthly_eur": -1}])
        out = onboarding.turn([{"role": "user", "content": "make it 2500"}],
                              {"monthly_income": 2500, "monthly_spend": 2000, "monthly_room": 500, "savings": 0},
                              live=False, draft=validate_goals([{**self.GOAL, "monthly_eur": 150}]))
        self.assertEqual([(g["title"], g["target_eur"], g["monthly_eur"]) for g in out["goals"]], [("Trip", 2500, 150)])

    def test_offline_yes_adds_the_suggestion(self):
        out = onboarding.turn([{"role": "user", "content": "yes, add the ring"}], {**{"monthly_income": 2500,
                              "monthly_spend": 2000, "monthly_room": 500, "savings": 0}, "suggestions": [
                                  {"title": "Wedding ring", "type": "save_for", "target_eur": 3000, "deadline": "2027-09-30", "reason": ""}]},
                              live=False)
        self.assertEqual(out["goals"][0]["title"], "Wedding ring")

    def test_add_goal_and_progress_survive_plan_edits(self):
        import server
        cid = server.new_try()["id"]
        v = server.save_goals(cid, [self.GOAL])
        server.db.execute("UPDATE goal SET saved_eur = 400 WHERE customer_id = ?", (cid,))
        v = server.add_goal(cid, {**self.GOAL, "title": "Car", "target_eur": 8000, "monthly_eur": 120})
        self.assertEqual([(g["title"], g["priority"], g["saved"]) for g in v["goals"]], [("Trip", 1, 400), ("Car", 2, 0)])
        self.assertEqual(v["goals"][1]["monthly"], 120)
        with self.assertRaises(ValueError):
            server.add_goal(cid, {**self.GOAL, "title": "trip"})
        for t in ("A", "B", "C"):
            server.add_goal(cid, {**self.GOAL, "title": t})
        with self.assertRaises(ValueError):
            server.add_goal(cid, {**self.GOAL, "title": "D"})
        v = server.save_goals(cid, [{**self.GOAL, "target_eur": 5000}])   # edited plan keeps the € 400 already saved
        self.assertEqual([(g["title"], g["saved"], g["target"]) for g in v["goals"]], [("Trip", 400, 5000)])


class TryIt(unittest.TestCase):
    GOAL = [{"title": "Trip", "type": "save_for", "horizon": "long", "target_eur": 3000, "deadline": "2027-12-01",
             "priority": 1}]

    def test_baseline_is_quiet(self):
        import server
        v = server.new_try()
        self.assertTrue(v["is_try"])
        self.assertFalse(v["onboarded"])
        self.assertIsNone(v["card"])
        self.assertIsNone(server.save_goals(v["id"], self.GOAL)["card"])   # quiet with a goal too

    def test_every_scenario_shows_its_own_card(self):
        import seed
        import server
        for sid in seed.SCENARIOS:
            with self.subTest(sid):
                cid = server.new_try()["id"]
                server.save_goals(cid, self.GOAL)
                out = server.scenario(cid, {"id": sid})
                self.assertEqual(out["view"]["card"]["situation_id"], sid)
                self.assertEqual(out["notification"]["title"], out["view"]["card"]["title"])

    def test_scenario_rejects_demo_customers_and_unknown_ids(self):
        import server
        with self.assertRaises(ValueError):
            server.scenario(1, {"id": "price_rise"})
        cid = server.new_try()["id"]
        for bad in ({"id": "lottery"}, {"id": 3}, {}):
            with self.assertRaises(ValueError):
                server.scenario(cid, bad)

    def test_pipeline_has_seven_steps_in_order(self):
        import server
        keys = [s["key"] for s in server.view(1, live=False)["pipeline"]]
        self.assertEqual(keys, ["signals", "understood", "candidates", "ai_check", "score", "controls", "decision"])


if __name__ == "__main__":
    unittest.main()
