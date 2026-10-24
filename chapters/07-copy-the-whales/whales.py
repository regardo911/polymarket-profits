"""Wallet vetting and whale alerts, Chapter 7. Polymarket's free Data API, no key.

python3 whales.py   vets the top 5 wallets on this month's leaderboard.
To vet more, change leaderboard("month")[:5] at the bottom: "all" for all
time, [:20] for the top 20 (BUILD STEP 1). A row ending in * is partial.

check_for_new_trades() is the alert monitor; alerts.py runs it. It prints
nothing until you paste real wallets into WHALES below.
"""
import json
import os

import requests

DATA = "https://data-api.polymarket.com/v2"

def get(path, **params):
    """GET one Data API endpoint. No key needed."""
    r = requests.get(f"{DATA}/{path}", params=params,
                     timeout=30)
    r.raise_for_status()
    return r.json()


def leaderboard(period="month"):
    """Top 100 wallets by profit. period: day,
    week, month or all. Fields: rank, user_id
    (the wallet), pnl, volume (in shares)."""
    return get("leaderboard", time_period=period)["data"]


def positions(wallet, status=None, max_pages=10):
    """Positions, 500 per page. status="closed":
    sold or cashed out. No status: OPEN plus
    REDEEMABLE (resolved, not cashed out)."""
    rows, cursor = [], None
    for _ in range(max_pages):
        params = {"user": wallet, "limit": 500}
        if status:
            params["status"] = status
        if cursor:
            params["cursor"] = cursor
        page = get("positions", **params)
        rows += page["data"]
        cursor = page["pagination"].get("next_cursor")
        if not page["pagination"].get("has_more"):
            return rows, True   # complete history
    return rows, False          # capped: biased sample


def vet_wallet(wallet):
    """Trade count, win rate, P&L without best win."""
    stats = get("user-stats", user=wallet)["data"]
    closed, ok1 = positions(wallet, "closed")
    rest, ok2 = positions(wallet)
    # A bet that resolved at $0 is never sold or
    # cashed out, so it sits in REDEEMABLE, not
    # CLOSED. Count both, or every loser vanishes.
    done = closed + [p for p in rest
                     if p["status"] == "REDEEMABLE"]
    pnls = sorted((p["total_pnl"] for p in done),
                  reverse=True)
    wins = sum(1 for x in pnls if x > 0)
    return {
        "trades": stats["trades"],
        "resolved": len(pnls),
        "complete": ok1 and ok2,
        "win_rate": wins / len(pnls) if pnls else 0.0,
        "pnl": sum(pnls),
        "pnl_ex_best": sum(pnls[1:]),
    }


ALERT_FILE = "whale_alerts.json"

# Paste the user_id values of the wallets you vetted
WHALES = [
    "0x...",
]

def load_last_seen():
    """Load the timestamp of the last seen trade."""
    if os.path.exists(ALERT_FILE):
        with open(ALERT_FILE) as f:
            return json.load(f)
    return {}


def save_last_seen(data):
    with open(ALERT_FILE, "w") as f:
        json.dump(data, f)


def check_for_new_trades():
    """
    Poll whale wallets and alert on new trades.
    """
    last_seen = load_last_seen()

    for n, wallet in enumerate(WHALES, start=1):
        trades = get("trades", user=wallet,
                     limit=20)["data"]
        prev = last_seen.get(wallet, 0)
        new = [t for t in trades
               if t["timestamp"] > prev]
        for t in reversed(new):  # oldest first
            print(f"whale {n}: {t['side']} "
                  f"{t['outcome'][:12]} "
                  f"@ {t['price']:.3g} "
                  f"x{t['size']:,.0f} | "
                  f"{t['title'][:24]}")
            # Add notification here:
            # send_email, send_telegram, etc.
        if trades:
            last_seen[wallet] = max(
                t["timestamp"] for t in trades)

    save_last_seen(last_seen)


if __name__ == "__main__":
    for row in leaderboard("month")[:5]:
        v = vet_wallet(row["user_id"])
        flag = "" if v["complete"] else " *"
        print(f"#{row['rank']} trades={v['trades']:,} "
              f"resolved={v['resolved']:,} "
              f"win={v['win_rate']:.0%} "
              f"ex-best=${v['pnl_ex_best']:,.0f}{flag}")
