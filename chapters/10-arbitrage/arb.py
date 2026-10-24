"""Cross-platform arbitrage scanner, Chapter 10. Polymarket vs Kalshi, public data, no keys.

python3 arb.py prints how many candidate pairs it found; zero is the usual
answer. Every candidate still needs your own check of both platforms'
resolution rules before you trade it. To test your own pair, build two dicts
and call find_arbitrage (the README shows the book's recession pair).
"""
import json
import requests

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
KALSHI = "https://external-api.kalshi.com/trade-api/v2"


def best_ask(token_id):
    """Lowest ask on one Polymarket outcome token."""
    r = requests.get(f"{CLOB}/book",
                     params={"token_id": token_id},
                     timeout=30)
    if r.status_code != 200:
        return None
    asks = [float(a["price"])
            for a in r.json().get("asks", [])]
    return min(asks) if asks else None


def poly_markets(limit=50):
    """Yes ask, No ask and fee rate per market."""
    params = {"closed": "false", "limit": limit,
              "order": "volume24hr",
              "ascending": "false"}
    r = requests.get(f"{GAMMA}/markets",
                     params=params, timeout=30)
    out = []
    for m in r.json():
        try:
            yes_id, no_id = json.loads(m["clobTokenIds"])
        except (KeyError, TypeError, ValueError):
            continue
        yes, no = best_ask(yes_id), best_ask(no_id)
        if yes is None or no is None:
            continue
        sched = m.get("feeSchedule") or {}
        out.append({"question": m["question"],
                    "yes_ask": yes, "no_ask": no,
                    "fee_rate": float(
                        sched.get("rate") or 0)})
    return out


def kalshi_markets(limit=200):
    """Kalshi prices are dollar strings."""
    params = {"status": "open", "limit": limit,
              "mve_filter": "exclude"}
    r = requests.get(f"{KALSHI}/markets",
                     params=params, timeout=30)
    out = []
    for m in r.json().get("markets", []):
        yes = float(m["yes_ask_dollars"])
        no = float(m["no_ask_dollars"])
        if 0 < yes < 1 and 0 < no < 1:
            out.append({"question": m["title"],
                        "yes_ask": yes, "no_ask": no,
                        "fee_rate": 0.07})
    return out


def leg_cost(market, side):
    """Ask price plus taker fee, per share."""
    p = market[f"{side}_ask"]
    return p + market["fee_rate"] * p * (1 - p)


def find_arbitrage(poly, kalshi, min_profit=0.02):
    """
    Buy Yes on one platform and No on the other.
    Profit per pair = $1.00 minus both legs' cost.
    """
    opportunities = []
    for pm in poly:
        for km in kalshi:
            if not markets_match(pm, km):
                continue
            for yes_m, no_m, route in (
                (pm, km, "Yes Poly / No Kalshi"),
                (km, pm, "Yes Kalshi / No Poly"),
            ):
                cost = (leg_cost(yes_m, "yes")
                        + leg_cost(no_m, "no"))
                if 1 - cost >= min_profit:
                    opportunities.append({
                        "market": pm["question"],
                        "kalshi": km["question"],
                        "route": route,
                        "profit": round(1 - cost, 4),
                    })
    return opportunities


def markets_match(poly_market, kalshi_market):
    """
    Check if two markets from different platforms
    refer to the same event. Uses keyword matching.
    Every match still needs a human check of both
    platforms' resolution rules.
    """
    p_words = set(
        poly_market["question"].lower().split()
    )
    k_words = set(
        kalshi_market["question"].lower().split()
    )
    # If 60%+ of words overlap, likely the same event
    overlap = len(p_words & k_words)
    total = min(len(p_words), len(k_words))
    if total == 0:
        return False
    return overlap / total > 0.6


if __name__ == "__main__":
    poly = poly_markets()
    kalshi = kalshi_markets()
    opps = find_arbitrage(poly, kalshi)
    print(f"Polymarket {len(poly)} | Kalshi "
          f"{len(kalshi)} | candidates {len(opps)}")
    for o in opps[:5]:
        print(f"{o['profit']:+.3f} {o['route']} | "
              f"{o['market'][:30]}")
