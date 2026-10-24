"""The Chapter 5, 6 and 8 bots, run offline against a made-up market list."""
import csv
import json
import os
import subprocess
import sys
import unittest
from unittest import mock

import support
from support import CH, captured, in_tempdir, load


class StopAfterOneScan(BaseException):
    """Raised from the patched time.sleep so run_bot stops after one scan."""


def setUpModule():
    support.block_network()


def tearDownModule():
    support.unblock_network()


def one_scan(bot):
    """run_bot() for exactly one cycle, on the made-up market list."""
    def run():
        try:
            bot.run_bot()
        except StopAfterOneScan:
            pass
    with mock.patch.object(bot.requests, "get", side_effect=support.fake_polymarket_get), \
         mock.patch.object(bot.time, "sleep", side_effect=StopAfterOneScan), \
         mock.patch.dict(os.environ, {"NEWS_API_KEY": ""}):
        _, text = captured(run)
    return text


class NetworkGuard(unittest.TestCase):
    def test_a_real_request_cannot_get_out(self):
        import requests
        with self.assertRaises(Exception):
            requests.get("https://gamma-api.polymarket.com/markets", timeout=2)


class Chapter5Bot(unittest.TestCase):
    def setUp(self):
        self.bot = load("05-first-bot/polybot.py", "polybot_ch05")

    def test_fee_worked_example(self):
        # ch02 and ch08: 0.07 x 0.50 x 0.50 = $0.0175 a share
        self.assertAlmostEqual(self.bot.taker_fee(0.07, 0.50), 0.0175)

    def test_best_bid_and_ask_come_from_max_and_min(self):
        with mock.patch.object(self.bot.requests, "get", side_effect=support.fake_polymarket_get):
            p = self.bot.get_market_prices("yes-1")
        self.assertEqual((p["bid"], p["ask"]), (0.30, 0.32))
        self.assertAlmostEqual(p["spread"], 0.02)

    def test_scan_skips_non_yes_no_and_empty_books(self):
        with mock.patch.object(self.bot.requests, "get", side_effect=support.fake_polymarket_get):
            rows = self.bot.scan_all_markets()
        self.assertEqual([r["market_id"] for r in rows], ["0xmadeup1", "0xmadeup2", "0xmadeup4"])

    def test_test1_null_price_is_skipped(self):
        self.assertIsNone(self.bot.analyze_market({"yes_price": None, "volume": 100000, "spread": 0.0}))

    def test_one_scan_paper_trades_and_logs(self):
        with in_tempdir() as d:
            text = one_scan(self.bot)
            self.assertIn("Polymarket Trading Bot v1.0", text)
            self.assertIn("Mode: PAPER", text)
            self.assertIn("[PAPER] YES $2.00 Will the made-up council app.. edge", text)
            self.assertIn("Signals found: 1", text)   # Test 5 dropped the $0.02 market
            with open(d / "trades.csv") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["paper"], "True")
            self.assertEqual(rows[0]["balance"], "100.00")
            self.assertEqual(json.loads((d / "traded_markets.json").read_text()), ["0xmadeup1"])

    def test_test4_restart_does_not_trade_the_same_market(self):
        with in_tempdir():
            one_scan(self.bot)
            again = load("05-first-bot/polybot.py", "polybot_ch05_restart")
            text = one_scan(again)
            self.assertNotIn("[PAPER]", text)
            self.assertIn("Already traded: 1 markets", text)

    def test_live_branch_still_refuses(self):
        signal = {"side": "YES", "edge": 0.2}
        market = {"market_id": "0xlive", "question": "q", "yes_price": 0.3}
        with mock.patch.object(self.bot, "PAPER_TRADE", False):
            with self.assertRaises(NotImplementedError):
                self.bot.execute_trade(signal, market, 100.0)


class Chapter6Bot(unittest.TestCase):
    def setUp(self):
        self.bot = load("06-ai-edge/polybot.py", "polybot_ch06")

    def test_one_scan_runs_v2_with_no_key_and_no_calibration(self):
        with in_tempdir():
            text = one_scan(self.bot)
        self.assertIn("[PAPER] YES $2.00 Will the made-up council app..", text)
        self.assertNotIn("Error in scan cycle", text)

    def test_baseline_stays_50_until_ten_resolutions(self):
        with in_tempdir():
            for i in range(9):
                self.bot.update_calibration("crypto", i < 2)
            self.assertEqual(self.bot.get_baseline("crypto"), 0.50)
            self.bot.update_calibration("crypto", False)
            self.assertAlmostEqual(self.bot.get_baseline("crypto"), 0.2)

    def test_headline_shift_is_clamped(self):
        for reply, shift in (("0.5", 0.3), ("-0.9", -0.3), ("0.04", 0.04), ("abc", 0.0)):
            with mock.patch.object(self.bot, "call_llm_api", return_value=reply):
                self.assertAlmostEqual(self.bot.analyze_headline("h", "q", 0.5), shift)

    def test_no_news_key_means_no_request(self):
        with mock.patch.dict(os.environ, {"NEWS_API_KEY": ""}), \
             mock.patch.object(self.bot.requests, "get") as get:
            self.assertEqual(self.bot.get_recent_headlines("fed rates"), [])
        get.assert_not_called()

    def test_record_py_prints_and_writes(self):
        with in_tempdir() as d:
            run = subprocess.run([sys.executable, str(CH / "06-ai-edge/record.py"), "crypto", "no"],
                                 capture_output=True, text=True, env={**os.environ, "NEWS_API_KEY": ""})
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(run.stdout.strip(), "recorded crypto: no")
            self.assertEqual(json.loads((d / "calibration.json").read_text()),
                             {"crypto": {"yes": 0, "total": 1}})

    def test_analyze_calibration_on_made_up_resolved_trades(self):
        with in_tempdir() as d:
            (d / "calibration.json").write_text(json.dumps({"crypto": {"yes": 2, "total": 10}}))
            with open(d / "trades.csv", "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["timestamp", "market", "side", "price", "size_usd", "edge",
                            "paper", "balance", "category", "outcome"])
                w.writerow(["t", "made-up 1", "YES", "0.40", "2", "0.1", "True", "100", "crypto", "loss"])
                w.writerow(["t", "made-up 2", "YES", "0.30", "2", "0.2", "True", "100", "crypto", "win"])
                w.writerow(["t", "made-up 3", "NO", "0.60", "2", "0.1", "True", "100", "crypto", ""])
            _, text = captured(self.bot.analyze_calibration)
        self.assertIn("Trades analyzed: 2", text)
        self.assertIn("Naive accuracy:      50.0%", text)
        self.assertIn("Calibrated accuracy: 50.0%", text)

    def test_categorize_market_ships_verbatim(self):
        # The printed substring match, kept as printed. BOOK-FIXES.md, ch06.
        self.assertEqual(self.bot.categorize_market("Will Bitcoin hit $150K?"), "crypto")
        self.assertEqual(self.bot.categorize_market("Will the Netherlands win the World Cup?"), "crypto")

    def test_example_calibration_file_cannot_load_by_accident(self):
        tracked = [p.name for p in CH.rglob("*.json")]
        self.assertIn("calibration.example.json", tracked)
        self.assertNotIn("calibration.json", tracked)


class Chapter8Bot(unittest.TestCase):
    def setUp(self):
        self.bot = load("08-kelly/polybot.py", "polybot_ch08")

    def test_kelly_table_from_chapter_8(self):
        # full Kelly, no caps: edge (points) and price -> % of bankroll
        rows = [(0.05, 0.50, 100.00), (0.10, 0.40, 166.67), (0.15, 0.35, 230.77),
                (0.05, 0.80, 250.00), (0.10, 0.25, 133.33)]
        with mock.patch.multiple(self.bot, KELLY_FRACTION=1.0, MAX_BET=1.0, MAX_POSITION_SIZE=10**6):
            for edge, price, dollars in rows:
                sig = {"side": "YES", "edge": edge, "market_price": price}
                self.assertEqual(self.bot.calculate_position_size(sig, 1000.0), dollars)

    def test_paper_size_hits_the_five_dollar_cap(self):
        sig = {"side": "NO", "edge": 0.30, "market_price": 0.80}
        self.assertEqual(self.bot.calculate_position_size(sig, 100.0), 5.00)

    def test_liquidity_check_on_the_chapter_8_book(self):
        book = {"asks": [{"price": "0.55", "size": "500"}, {"price": "0.54", "size": "1200"},
                         {"price": "0.53", "size": "3000"}]}
        self.assertEqual(self.bot.max_position_for_price(book), 4700.0)
        self.assertEqual(self.bot.max_position_for_price({"asks": []}), 0.0)

    def test_scan_never_calls_the_liquidity_check(self):
        # BOOK-FIXES.md, ch08: printed, but nothing in the bot calls it.
        with in_tempdir(), mock.patch.object(self.bot, "max_position_for_price",
                                             wraps=self.bot.max_position_for_price) as liq:
            text = one_scan(self.bot)
        self.assertIn("[PAPER] YES $5.00", text)
        liq.assert_not_called()


if __name__ == "__main__":
    unittest.main()
