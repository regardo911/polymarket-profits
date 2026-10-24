"""One limit order through Polymarket's official SDK, Chapter 5 ("It doesn't do real order execution").

Paper mode is the default and the only thing this file does until you edit it:

    python3 live_order.py --venue international --slug <market-slug> --side yes --price 0.42 --size 10
    python3 live_order.py --venue us --slug <market-slug> --side yes --price 0.42 --size 10

Both print the order they WOULD send and exit. To send it for real, you uncomment the
set_live_mode line at the bottom of this file:
    set_live_mode(True, confirm="I_HAVE_REVIEWED_THIS")
No command-line flag or environment variable can switch it on.

Live mode needs your own account, your own credentials in a .env file next to
this script, and the SDK for where you live (requirements-live.txt):
    international (polymarket.com, outside the close-only countries):
        polymarket-client, Python 3.11+
        POLYMARKET_PRIVATE_KEY, POLYMARKET_WALLET_ADDRESS
    us (Polymarket US, CFTC-regulated, US dollars):
        polymarket-us, Python 3.10+
        POLYMARKET_KEY_ID, POLYMARKET_SECRET_KEY

Every call below is copied from the official docs (docs.polymarket.com/trading/
quickstart, docs.polymarket.us/api-reference/sdks/python/orders) and matches
polymarket-client 0.14.0 and polymarket-us 2.4.1. Real money, your risk:
educational code, not financial advice.
"""
import argparse
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

GEOBLOCK = "https://polymarket.com/api/geoblock"
CONFIRM = "I_HAVE_REVIEWED_THIS"

_live = False


def set_live_mode(on, confirm=""):
    """Turn live orders on. Only works with the exact confirm string."""
    global _live
    if on and confirm != CONFIRM:
        raise ValueError(f'set_live_mode(True) needs confirm="{CONFIRM}"')
    _live = bool(on)


def is_live():
    return _live


def geoblocked():
    """The Chapter 2 check: True when polymarket.com is close-only for you."""
    r = requests.get(GEOBLOCK, timeout=30)
    r.raise_for_status()
    return bool(r.json().get("blocked"))


def parse_args(argv):
    ap = argparse.ArgumentParser(description="Place one limit order "
                                 "(prints it unless live mode is on in code).")
    ap.add_argument("--venue", choices=["international", "us"], required=True)
    ap.add_argument("--slug", required=True,
                    help="market slug, the last part of the market's URL")
    ap.add_argument("--side", choices=["yes", "no"], required=True,
                    help="the outcome you are buying")
    ap.add_argument("--price", type=float, required=True,
                    help="limit price for that outcome, 0.01 to 0.99")
    ap.add_argument("--size", type=float, required=True,
                    help="number of shares (contracts on Polymarket US)")
    a = ap.parse_args(argv)
    if not 0 < a.price < 1:
        ap.error("--price must be between 0 and 1")
    if a.size <= 0:
        ap.error("--size must be above 0")
    return a


def place_international(a):
    from polymarket import SecureClient  # pip install polymarket-client

    with SecureClient.create(
        private_key=os.environ["POLYMARKET_PRIVATE_KEY"],
        wallet=os.environ["POLYMARKET_WALLET_ADDRESS"],
    ) as client:
        market = client.get_market(slug=a.slug)
        outcome = market.outcomes.yes if a.side == "yes" else market.outcomes.no
        # V2 markets trade by position id, older ones by token id (per the docs)
        asset_id = outcome.position_id if market.version == "v2" else outcome.token_id
        response = client.place_limit_order(
            asset_id=asset_id, price=str(a.price), size=str(a.size), side="BUY",
        )
        if not response.ok:
            raise SystemExit(f"rejected: {response.message}")
        print(f"order {response.order_id}: {response.status}")


def place_us(a):
    from polymarket_us import PolymarketUS  # pip install polymarket-us

    client = PolymarketUS(
        key_id=os.environ["POLYMARKET_KEY_ID"],
        secret_key=os.environ["POLYMARKET_SECRET_KEY"],
    )
    try:
        order = client.orders.create(us_order_params(a))
        print(f"order {order.get('id')}")
    finally:
        client.close()


def us_order_params(a):
    """The request body docs.polymarket.us shows for a limit order."""
    return {
        "marketSlug": a.slug,
        "intent": "ORDER_INTENT_BUY_LONG",
        "type": "ORDER_TYPE_LIMIT",
        "price": {"value": f"{a.price}", "currency": "USD"},
        "quantity": a.size,
        "tif": "TIME_IN_FORCE_GOOD_TILL_CANCEL",
    }


def main(argv=None):
    a = parse_args(sys.argv[1:] if argv is None else argv)

    if a.venue == "us" and a.side == "no":
        # The Polymarket US docs describe a No position as a short on Yes
        # (Collateral and Margin). How a No limit price is entered there has
        # not been checked for this example, so it buys Yes only on US.
        print("On Polymarket US this example buys Yes only. Use --side yes, "
              "or place the No order in the app.")
        return 1

    if a.venue == "international" and geoblocked():
        print("polymarket.com is close-only where you are (the geoblock check "
              "says blocked). Use --venue us, or Kalshi. Never a VPN.")
        return 1

    order = (f"{a.venue}: BUY {a.side.upper()} {a.size:g} @ ${a.price:.2f} "
             f"limit, market {a.slug}")
    if not is_live():
        print("DRY RUN, nothing sent. This is the order live mode would place:")
        print("  " + order)
        print(f'To send it, uncomment set_live_mode(True, confirm="{CONFIRM}") '
              "at the bottom of live_order.py")
        return 0

    print("LIVE ORDER. Real money, your risk. Not financial advice.")
    print("  " + order)
    load_dotenv(Path(__file__).with_name(".env"))
    if a.venue == "international":
        place_international(a)
    else:
        place_us(a)
    return 0


if __name__ == "__main__":
    # set_live_mode(True, confirm="I_HAVE_REVIEWED_THIS")
    raise SystemExit(main())
