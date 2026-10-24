"""Paper-trading bot, Chapter 5. Reads live public Polymarket prices, trades on paper only.

This is the file at the end of Chapter 5: the BUILD STEP 2 code in order, plus
the fixes from "Testing Your Bot" that the chapter tells you to keep:
Test 1 (null check), Test 2 (rate_limited_get), Test 3 (get_all_markets),
Test 4 (traded_markets.json across restarts) and Test 5 (price filter).

Run it:  python3 polybot.py      Stop it: Ctrl+C
No key, no account. Paper mode writes trades.csv and traded_markets.json here.
Educational code, not financial advice.
"""
import csv
import json
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()  # Chapter 6 keeps its API keys in .env

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"


def rate_limited_get(url, params=None, timeout=30,
                     max_retries=3):
    """GET request with automatic retry on HTTP 429."""
    for attempt in range(max_retries):
        response = requests.get(url, params=params,
                                timeout=timeout)
        if response.status_code == 429:
            wait = 2 ** attempt  # 1s, 2s, 4s
            print(f"Rate limited. Waiting {wait}s...")
            time.sleep(wait)
            continue
        return response
    return response  # return last response even if 429


def get_markets(limit=50):
    """Fetch open markets, busiest first."""
    params = {"closed": "false", "limit": limit,
              "order": "volume24hr",
              "ascending": "false"}
    r = rate_limited_get(f"{GAMMA}/markets",
                         params=params, timeout=30)
    if r.status_code != 200:
        print(f"API error: {r.status_code}")
        return []
    return r.json()  # a plain list of market dicts


def get_market_prices(token_id):
    """Best bid and ask for one outcome token."""
    r = rate_limited_get(f"{CLOB}/book",
                         params={"token_id": token_id},
                         timeout=30)
    if r.status_code != 200:
        return None
    book = r.json()
    bids = [float(b["price"])
            for b in book.get("bids", [])]
    asks = [float(a["price"])
            for a in book.get("asks", [])]
    if not bids or not asks:
        return None
    # Best bid = HIGHEST bid. Best ask = LOWEST ask.
    # Never read bids[0] or asks[0]: list order is
    # not the price order.
    bid, ask = max(bids), min(asks)
    return {"bid": bid, "ask": ask,
            "mid": (bid + ask) / 2,
            "spread": ask - bid}


def fee_rate(market):
    """Taker fee rate from the market's feeSchedule."""
    sched = market.get("feeSchedule") or {}
    return float(sched.get("rate") or 0)


def scan_all_markets():
    """Scan markets and return prices for each."""
    results = []
    for market in get_markets(100):
        try:
            outcomes = json.loads(market["outcomes"])
            tokens = json.loads(market["clobTokenIds"])
        except (KeyError, TypeError, ValueError):
            continue
        if outcomes[:1] != ["Yes"] or not tokens:
            continue
        yes_token = tokens[0]  # same order as outcomes

        prices = get_market_prices(yes_token)
        if prices is None:
            continue

        results.append({
            "question": market["question"],
            "market_id": market["conditionId"],
            "yes_token_id": yes_token,
            "yes_price": prices["mid"],
            "spread": prices["spread"],
            "volume": float(market.get("volume24hr") or 0),
            "week_volume": float(
                market.get("volume1wk") or 0),
            "fee_rate": fee_rate(market),
        })

    return results


def get_all_markets(max_pages=10):
    """Fetch every open market, 100 per page."""
    all_markets = []
    cursor = None

    for _ in range(max_pages):
        params = {"closed": "false", "limit": 100}
        if cursor:
            params["after_cursor"] = cursor

        response = rate_limited_get(
            f"{GAMMA}/markets/keyset", params=params
        )
        if response.status_code != 200:
            break

        data = response.json()
        all_markets.extend(data.get("markets", []))
        cursor = data.get("next_cursor")
        if not cursor:
            break

    return all_markets


EDGE_THRESHOLD = 0.07  # minimum 7-point edge, after fees
MIN_VOLUME = 10000     # skip markets under $10K/24h
MAX_SPREAD = 0.08      # skip illiquid markets


def taker_fee(rate, price):
    """Polymarket taker fee per share."""
    return rate * price * (1 - price)


def analyze_market(market):
    """
    Simple edge detection. Compares market price to a
    baseline estimate. Returns trade signal or None.
    """
    if market.get("yes_price") is None:
        return None
    if market["volume"] < MIN_VOLUME:
        return None
    if market["spread"] > MAX_SPREAD:
        return None

    yes_price = market["yes_price"]
    if yes_price < 0.05 or yes_price > 0.95:
        return None  # skip extreme-priced markets

    # Simple baseline: assume 50% unless we have
    # a reason to think otherwise. This is deliberately
    # naive. Chapter 6 adds better estimates.
    baseline = 0.50

    edge = baseline - yes_price
    # p * (1 - p) is the same for Yes and No, so one
    # fee figure covers either side.
    fee = taker_fee(market["fee_rate"], yes_price)
    net_edge = abs(edge) - fee

    if net_edge < EDGE_THRESHOLD:
        return None  # not enough edge after fees

    return {
        "side": "YES" if edge > 0 else "NO",
        "edge": net_edge,
        "fee": fee,
        "market_price": yes_price,
        "our_estimate": baseline,
    }


MAX_POSITION_SIZE = 5.00  # max $5 per trade
PAPER_TRADE = True        # paper mode needs no key

# Track what we've already traded
traded_markets = set()


def calculate_position_size(edge, balance):
    """Simple position sizing. Chapter 8 upgrades to Kelly."""
    # For now: fixed $5 or 2% of balance, whichever is smaller
    size = min(MAX_POSITION_SIZE, balance * 0.02)
    return round(size, 2)


def execute_trade(signal, market, balance):
    """Place a trade based on the Analyst's signal."""
    if market["market_id"] in traded_markets:
        return None  # already traded this market

    size = calculate_position_size(signal["edge"], balance)

    trade_record = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "market": market["question"],
        "side": signal["side"],
        "price": market["yes_price"],
        "size_usd": size,
        "edge": signal["edge"],
        "paper": PAPER_TRADE,
    }

    if PAPER_TRADE:
        print(f"[PAPER] {signal['side']} ${size:.2f} "
              f"{market['question'][:28]}.. "
              f"edge {signal['edge']:.1%}")
    else:
        # Live orders need a wallet signature plus
        # API credentials. Use the official SDK for
        # where you live: polymarket-client or
        # polymarket-us. See live/live_order.py.
        raise NotImplementedError("paper mode only")

    traded_markets.add(market["market_id"])
    return trade_record


LOG_FILE = "trades.csv"


def init_log():
    """Create the trade log CSV if it doesn't exist."""
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "market", "side", "price",
                "size_usd", "edge", "paper", "balance"
            ])


def log_trade(trade, balance):
    """Append a trade to the CSV log."""
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            trade["timestamp"],
            trade["market"],
            trade["side"],
            trade["price"],
            trade["size_usd"],
            f"{trade['edge']:.4f}",
            trade["paper"],
            f"{balance:.2f}"
        ])


TRADED_FILE = "traded_markets.json"


def load_traded():
    if os.path.exists(TRADED_FILE):
        with open(TRADED_FILE) as f:
            return set(json.load(f))
    return set()


def save_traded(traded):
    with open(TRADED_FILE, "w") as f:
        json.dump(list(traded), f)


SCAN_INTERVAL = 30  # seconds between scans


def run_bot():
    """Main bot loop. Scans, analyzes, trades, logs."""
    init_log()
    traded_markets.update(load_traded())
    balance = 100.00  # starting balance for paper trading

    print("=" * 50)
    print("Polymarket Trading Bot v1.0")
    print(f"Mode: {'PAPER' if PAPER_TRADE else 'LIVE'}")
    print(f"Balance: ${balance:.2f}")
    print(f"Edge threshold: {EDGE_THRESHOLD:.0%}")
    print(f"Max position: ${MAX_POSITION_SIZE:.2f}")
    print(f"Scanning every {SCAN_INTERVAL}s")
    print("=" * 50)

    cycle = 0
    while True:
        cycle += 1
        print(f"\n--- Scan #{cycle} "
              f"({time.strftime('%H:%M:%S')}) ---")

        try:
            markets = scan_all_markets()
            print(f"Scanned {len(markets)} markets")

            signals = 0
            for market in markets:
                signal = analyze_market(market)
                if signal:
                    signals += 1
                    trade = execute_trade(
                        signal, market, balance
                    )
                    if trade:
                        log_trade(trade, balance)
                        save_traded(traded_markets)
                        if not PAPER_TRADE:
                            balance -= trade["size_usd"]

            print(f"Signals found: {signals}")
            print(f"Already traded: "
                  f"{len(traded_markets)} markets")

        except Exception as e:
            print(f"Error in scan cycle: {e}")
            # Don't crash on errors. Log and continue.

        time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    run_bot()
