"""AI-upgraded paper-trading bot, Chapter 6. Same loop as Chapter 5, smarter Analyst.

The Chapter 5 file plus every Chapter 6 function placed above run_bot()
(BUILD STEP 1), with run_bot() calling analyze_market_v2 (BUILD STEP 2).

    python3 polybot.py                     run the bot (paper mode)
    python3 record.py crypto no            record one resolved market
    python3 -c 'from polybot import analyze_calibration; analyze_calibration()'

NEWS_API_KEY in .env is optional; without it the bot runs on volume and
calibration alone. call_llm_api is the book's stub: it returns "0.00" until
you wire in your own LLM provider. Educational code, not financial advice.
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


def get_sentiment_score(market):
    """
    Attention spike: last-24h volume against this
    market's average day over the past week.
    """
    week = market.get("week_volume", 0)
    if week <= 0:
        return None
    ratio = market["volume"] / (week / 7)
    return {
        "attention": ratio,  # 1.0 = a normal day
        "signal_strength": min(
            max(ratio - 1.0, 0.0) / 2.0, 1.0
        ),
    }


def call_llm_api(prompt):
    """STUB. Replace the body with one call to your
    LLM provider and return its reply as text."""
    return "0.00"  # "no shift" until you wire it up


def analyze_headline(headline, market_question,
                     current_price):
    """
    Use an LLM to estimate how a headline affects
    a market's probability.

    Returns a float between -0.3 and +0.3 representing
    the estimated probability shift.
    """
    prompt = f"""You are a prediction market analyst.

Market question: {market_question}
Current market price (implied probability): {current_price}

New headline: {headline}

Based on this headline, estimate how the true
probability of this market should change.

Respond with ONLY a number between -0.30 and +0.30:
- Positive means the event is MORE likely
- Negative means the event is LESS likely
- 0.00 means the headline has no effect

Be conservative. Most headlines shift probability
by less than 0.05. Only major breaking news
shifts by 0.10 or more.

Number:"""

    # Replace with your preferred LLM API call
    response = call_llm_api(prompt)

    try:
        shift = float(response.strip())
        # Clamp to valid range
        return max(-0.30, min(0.30, shift))
    except ValueError:
        return 0.0


HEADLINE_CACHE = {}       # keyword -> (time, titles)
CACHE_SECONDS = 12 * 3600 # free plan: 100 requests/day


def get_recent_headlines(keyword, count=5):
    """Fetch recent headlines from a news API."""
    key = os.getenv("NEWS_API_KEY")
    if not key:
        return []  # no key: run without headlines
    hit = HEADLINE_CACHE.get(keyword)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    # NewsAPI.org free tier: 100 requests/day, and
    # articles arrive with a 24-hour delay
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": keyword,
        "sortBy": "publishedAt",
        "pageSize": count,
        "apiKey": key,
    }
    try:
        response = requests.get(url, params=params,
                                timeout=30)
    except requests.RequestException:
        return []  # news is optional; keep scanning
    if response.status_code != 200:
        return []

    articles = response.json().get("articles", [])
    titles = [a["title"] for a in articles]
    HEADLINE_CACHE[keyword] = (time.time(), titles)
    return titles


CALIBRATION_FILE = "calibration.json"


def load_calibration():
    """Load calibration data from file."""
    if os.path.exists(CALIBRATION_FILE):
        with open(CALIBRATION_FILE) as f:
            return json.load(f)
    return {}


def update_calibration(category, resolved_yes):
    """
    Update calibration data when a market resolves.
    category: string like 'politics', 'crypto', 'sports'
    resolved_yes: boolean, did the market resolve Yes?
    """
    cal = load_calibration()

    if category not in cal:
        cal[category] = {"yes": 0, "total": 0}

    cal[category]["total"] += 1
    if resolved_yes:
        cal[category]["yes"] += 1

    with open(CALIBRATION_FILE, "w") as f:
        json.dump(cal, f, indent=2)


def get_baseline(category):
    """
    Get calibrated baseline probability for a category.
    Falls back to 0.50 if insufficient data.
    """
    cal = load_calibration()
    if category not in cal:
        return 0.50
    if cal[category]["total"] < 10:
        return 0.50  # not enough data yet

    return cal[category]["yes"] / cal[category]["total"]


def analyze_calibration():
    """Compare accuracy with and without
    calibrated baselines."""
    with open("calibration.json") as f:
        cal = json.load(f)
    with open("trades.csv") as f:
        trades = list(csv.DictReader(f))

    naive_correct = 0
    calibrated_correct = 0
    total = 0

    for trade in trades:
        if trade.get("outcome") not in ("win", "loss"):
            continue

        category = trade.get("category") or "general"
        market_price = float(trade["price"])
        won = trade["outcome"] == "win"
        # Did the market resolve Yes?
        yes = won if trade["side"] == "YES" else not won

        naive = "YES" if 0.50 > market_price else "NO"
        if (naive == "YES") == yes:
            naive_correct += 1

        c = cal.get(category, {})
        if c.get("total", 0) >= 10:
            base = c["yes"] / c["total"]
        else:
            base = 0.50
        calib = "YES" if base > market_price else "NO"
        if (calib == "YES") == yes:
            calibrated_correct += 1

        total += 1

    if total == 0:
        print("No resolved trades yet.")
        return
    diff = (calibrated_correct - naive_correct) / total
    print(f"Trades analyzed: {total}")
    print(f"Naive accuracy:      {naive_correct/total:.1%}")
    print(f"Calibrated accuracy: "
          f"{calibrated_correct/total:.1%}")
    print(f"Improvement:         {diff:+.1%}")


def analyze_market_v2(market):
    """
    Enhanced analysis using sentiment, news, and
    calibration. Replaces the naive 50% baseline.
    """
    if market["volume"] < MIN_VOLUME:
        return None
    if market["spread"] > MAX_SPREAD:
        return None

    yes_price = market["yes_price"]
    if yes_price < 0.05 or yes_price > 0.95:
        return None  # Chapter 5's Test 5 filter
    question = market["question"]

    # Step 1: Get calibrated baseline
    category = categorize_market(question)
    baseline = get_baseline(category)

    # Step 2: Check sentiment for spikes
    sentiment = get_sentiment_score(market)
    sentiment_active = (
        sentiment is not None
        and sentiment["signal_strength"] > 0.3
    )

    # Step 3: If sentiment is spiking, check headlines
    news_shift = 0.0
    if sentiment_active:
        keywords = extract_keywords(question)
        headlines = get_recent_headlines(
            " ".join(keywords[:3]), count=3
        )
        for headline in headlines:
            shift = analyze_headline(
                headline, question, yes_price
            )
            news_shift += shift
        # Average the shifts, don't sum them
        if headlines:
            news_shift = news_shift / len(headlines)

    # Step 4: Combine into final estimate
    adjusted_baseline = baseline + news_shift
    # Clamp to valid probability range
    adjusted_baseline = max(0.05, min(0.95,
                                      adjusted_baseline))

    edge = adjusted_baseline - yes_price
    fee = taker_fee(market["fee_rate"], yes_price)
    net_edge = abs(edge) - fee

    if net_edge < EDGE_THRESHOLD:
        return None

    return {
        "side": "YES" if edge > 0 else "NO",
        "edge": net_edge,
        "market_price": yes_price,
        "our_estimate": adjusted_baseline,
        "baseline": baseline,
        "news_shift": news_shift,
        "sentiment_active": sentiment_active,
    }


def categorize_market(question):
    """Simple keyword-based categorization."""
    q = question.lower()
    if any(w in q for w in ["bitcoin", "ethereum",
                             "crypto", "btc", "eth"]):
        return "crypto"
    if any(w in q for w in ["president", "election",
                             "senate", "congress",
                             "governor"]):
        return "politics"
    if any(w in q for w in ["nba", "nfl", "mlb",
                             "game", "win", "match"]):
        return "sports"
    if any(w in q for w in ["rate", "fed", "gdp",
                             "inflation", "jobs"]):
        return "economics"
    return "general"


def extract_keywords(question):
    """Pull searchable keywords from a market question."""
    stop_words = {"will", "the", "a", "an", "be", "by",
                  "in", "on", "at", "to", "of", "is",
                  "this", "that", "before", "after"}
    words = question.lower().replace("?", "").split()
    return [w for w in words if w not in stop_words][:5]


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
                signal = analyze_market_v2(market)
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
