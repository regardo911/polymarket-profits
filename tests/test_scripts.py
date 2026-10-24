"""whales.py, alerts.py, arb.py, kelly.py and the guarded live-order example, offline."""
import json
import os
import unittest
from unittest import mock

import support
from support import FakeResponse, captured, in_tempdir, load


def setUpModule():
    support.block_network()


def tearDownModule():
    support.unblock_network()


# ---- Chapter 7 ------------------------------------------------------------

MADE_UP_WALLET = "0xmadeupwallet"


def fake_data_api(url, params=None, timeout=None, **kwargs):
    path = url.rsplit("/v2/", 1)[1]
    if path == "leaderboard":
        return FakeResponse({"data": [{"rank": 1, "user_id": MADE_UP_WALLET, "pnl": 1, "volume": 1}]})
    if path == "user-stats":
        return FakeResponse({"data": {"trades": 12}})
    if path == "positions":
        done = {"has_more": False, "next_cursor": None}
        if params.get("status") == "closed":
            return FakeResponse({"data": [{"total_pnl": 50.0, "status": "CLOSED"}], "pagination": done})
        return FakeResponse({"data": [{"total_pnl": -30.0, "status": "REDEEMABLE"},
                                      {"total_pnl": 5.0, "status": "OPEN"}], "pagination": done})
    if path == "trades":
        if params["user"] != MADE_UP_WALLET:
            return FakeResponse({"data": []})
        return FakeResponse({"data": [   # newest first, as the API sends them
            {"timestamp": 200, "side": "BUY", "outcome": "Yes", "price": 0.56, "size": 1200.0,
             "title": "Will the made-up bill pass?"},
            {"timestamp": 100, "side": "SELL", "outcome": "No", "price": 0.15, "size": 355.0,
             "title": "Will the made-up team win?"},
        ]})
    return FakeResponse({}, 404)


class Whales(unittest.TestCase):
    def setUp(self):
        self.w = load("07-copy-the-whales/whales.py", "whales")

    def test_vet_wallet_counts_redeemable_losers(self):
        with mock.patch.object(self.w.requests, "get", side_effect=fake_data_api):
            v = self.w.vet_wallet(MADE_UP_WALLET)
        self.assertEqual(v["trades"], 12)
        self.assertEqual(v["resolved"], 2)          # CLOSED win + REDEEMABLE loser; OPEN excluded
        self.assertEqual(v["win_rate"], 0.5)
        self.assertEqual(v["pnl_ex_best"], -30.0)
        self.assertTrue(v["complete"])

    def test_placeholder_wallet_prints_nothing(self):
        with in_tempdir() as d, mock.patch.object(self.w.requests, "get", side_effect=fake_data_api):
            _, text = captured(self.w.check_for_new_trades)
            self.assertEqual(text, "")
            self.assertEqual(json.loads((d / "whale_alerts.json").read_text()), {})

    def test_alerts_oldest_first_then_only_new(self):
        with in_tempdir(), mock.patch.object(self.w.requests, "get", side_effect=fake_data_api), \
             mock.patch.object(self.w, "WHALES", [MADE_UP_WALLET]):
            _, first = captured(self.w.check_for_new_trades)
            _, second = captured(self.w.check_for_new_trades)
        self.assertEqual(first.splitlines(), [
            "whale 1: SELL No @ 0.15 x355 | Will the made-up team wi",
            "whale 1: BUY Yes @ 0.56 x1,200 | Will the made-up bill pa",
        ])
        self.assertEqual(second, "")


# ---- Chapter 10 -----------------------------------------------------------

class Arbitrage(unittest.TestCase):
    def setUp(self):
        self.arb = load("10-arbitrage/arb.py", "arb")

    def test_recession_pair_from_chapter_10(self):
        q = "Will the US enter a recession this year?"   # made-up pair, as the chapter says
        poly = [{"question": q, "yes_ask": 0.28, "no_ask": 0.72, "fee_rate": 0.04}]
        kalshi = [{"question": q, "yes_ask": 0.35, "no_ask": 0.65, "fee_rate": 0.07}]
        opps = self.arb.find_arbitrage(poly, kalshi)
        self.assertEqual([(o["route"], o["profit"]) for o in opps], [("Yes Poly / No Kalshi", 0.046)])

    def test_different_questions_do_not_match(self):
        a = {"question": "Will the Fed cut rates in June?"}
        b = {"question": "Will Bitcoin close above $150K?"}
        self.assertFalse(self.arb.markets_match(a, b))

    def test_kalshi_dollar_strings(self):
        payload = {"markets": [
            {"title": "Made-up A", "yes_ask_dollars": "0.4100", "no_ask_dollars": "0.6200"},
            {"title": "Made-up B", "yes_ask_dollars": "1.0000", "no_ask_dollars": "0.0100"},
        ]}
        with mock.patch.object(self.arb.requests, "get", return_value=FakeResponse(payload)):
            rows = self.arb.kalshi_markets()
        self.assertEqual(rows, [{"question": "Made-up A", "yes_ask": 0.41, "no_ask": 0.62, "fee_rate": 0.07}])


# ---- Chapter 8: kelly.py --------------------------------------------------

class KellyCalculator(unittest.TestCase):
    def setUp(self):
        self.k = load("08-kelly/kelly.py", "kelly")

    def test_chapter_8_table(self):
        rows = [(0.55, 0.50, "10.0", "5.0", "2.5"), (0.50, 0.40, "16.7", "8.3", "4.2"),
                (0.50, 0.35, "23.1", "11.5", "5.8"), (0.85, 0.80, "25.0", "12.5", "6.3"),
                (0.35, 0.25, "13.3", "6.7", "3.3")]
        for prob, price, full, half, quarter in rows:
            f, _, _ = self.k.full_kelly(prob, price)
            self.assertEqual([str(self.k.pct(f * x)) for x in (1, 0.5, 0.25)], [full, half, quarter])

    def test_fee_folded_into_price(self):
        # ch08: 5 points at 50 cents on a 0.07 market -> 3.25 points, full Kelly 6.7%
        f, p, c = self.k.full_kelly(0.55, 0.50, fee_rate=0.07)
        self.assertAlmostEqual(c, 0.5175)
        self.assertEqual(str(self.k.pct(f)), "6.7")

    def test_no_side_situation_1(self):
        # ch08 Situation 1: market 30%, you say 20%, No at $0.70 -> half Kelly 16.7%
        f, _, _ = self.k.full_kelly(0.20, 0.30, side="no")
        self.assertEqual(str(self.k.pct(f * 0.5)), "16.7")

    def test_cli_caps_at_five_percent(self):
        code, text = captured(self.k.main, ["--prob", "0.20", "--price", "0.30", "--side", "no",
                                            "--bankroll", "3000"])
        self.assertEqual(code, 0)
        self.assertIn("bet 5.0% of your bankroll, $150.00 of $3000.00", text)

    def test_cli_says_no_bet_without_edge(self):
        _, text = captured(self.k.main, ["--prob", "0.40", "--price", "0.50"])
        self.assertIn("Kelly says no bet", text)


# ---- Chapter 5: the guarded live-order example ----------------------------

US_ORDER = ["--venue", "us", "--slug", "made-up-market", "--side", "yes", "--price", "0.42", "--size", "10"]
INTL_ORDER = ["--venue", "international", "--slug", "made-up-market", "--side", "no",
              "--price", "0.58", "--size", "10"]


class LiveOrderStaysOff(unittest.TestCase):
    def setUp(self):
        self.lo = load("05-first-bot/live/live_order.py", "live_order")

    def no_sdk(self):
        return mock.patch.multiple(self.lo, place_us=mock.DEFAULT, place_international=mock.DEFAULT)

    def test_off_by_default_and_prints_the_order(self):
        with self.no_sdk() as sdk, mock.patch.object(self.lo.requests, "get") as get:
            code, text = captured(self.lo.main, US_ORDER)
        self.assertEqual(code, 0)
        self.assertIn("DRY RUN, nothing sent", text)
        self.assertIn("us: BUY YES 10 @ $0.42 limit, market made-up-market", text)
        sdk["place_us"].assert_not_called()
        get.assert_not_called()

    def test_international_dry_run_makes_only_the_geoblock_call(self):
        with self.no_sdk() as sdk, mock.patch.object(
                self.lo.requests, "get", return_value=FakeResponse({"blocked": False})) as get:
            code, text = captured(self.lo.main, INTL_ORDER)
        self.assertEqual(code, 0)
        self.assertIn("international: BUY NO 10 @ $0.58", text)
        get.assert_called_once_with(self.lo.GEOBLOCK, timeout=30)
        sdk["place_international"].assert_not_called()

    def test_blocked_country_is_refused_for_international(self):
        with self.no_sdk(), mock.patch.object(
                self.lo.requests, "get", return_value=FakeResponse({"blocked": True})):
            code, text = captured(self.lo.main, INTL_ORDER)
        self.assertEqual(code, 1)
        self.assertIn("close-only", text)

    def test_a_flag_cannot_turn_it_on(self):
        for flag in ("--live", "--live=1", "--confirm=I_HAVE_REVIEWED_THIS"):
            with self.no_sdk(), self.assertRaises(SystemExit) as e, captured_stderr():
                self.lo.main(US_ORDER + [flag])
            self.assertEqual(e.exception.code, 2)
            self.assertFalse(self.lo.is_live())

    def test_an_environment_variable_cannot_turn_it_on(self):
        env = {"LIVE": "1", "POLYMARKET_LIVE": "1", "LIVE_MODE": "true"}
        with self.no_sdk() as sdk, mock.patch.dict(os.environ, env):
            _, text = captured(self.lo.main, US_ORDER)
        self.assertIn("DRY RUN", text)
        sdk["place_us"].assert_not_called()

    def test_wrong_confirm_string_is_rejected(self):
        for confirm in ("", "yes", "i_have_reviewed_this"):
            with self.assertRaises(ValueError):
                self.lo.set_live_mode(True, confirm=confirm)
        self.assertFalse(self.lo.is_live())

    def test_us_no_side_is_refused(self):
        with self.no_sdk() as sdk:
            code, _ = captured(self.lo.main, US_ORDER[:5] + ["no"] + US_ORDER[6:])
        self.assertEqual(code, 1)
        sdk["place_us"].assert_not_called()

    def test_code_level_opt_in_reaches_the_sdk_call(self):
        self.lo.set_live_mode(True, confirm="I_HAVE_REVIEWED_THIS")
        try:
            with self.no_sdk() as sdk, mock.patch.object(self.lo, "load_dotenv"):
                code, text = captured(self.lo.main, US_ORDER)
        finally:
            self.lo.set_live_mode(False)
        self.assertEqual(code, 0)
        self.assertIn("LIVE ORDER. Real money, your risk.", text)
        sdk["place_us"].assert_called_once()   # a mock: nothing was sent


def captured_stderr():
    import contextlib
    import io
    return contextlib.redirect_stderr(io.StringIO())


if __name__ == "__main__":
    unittest.main()
