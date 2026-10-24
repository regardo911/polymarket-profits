"""Kelly calculator, Chapter 8. Full, half and quarter Kelly for one trade, with the 5% cap.

The chapter prints the formula and the spreadsheet, not a script; this is the
same math as a command, so you can size a trade without opening the sheet.

    python3 kelly.py --prob 0.55 --price 0.50
    python3 kelly.py --prob 0.20 --price 0.30 --side no --fee-rate 0.04 --bankroll 2000

--prob is your probability that the event happens (Yes), and --price is the
Yes price, the same two numbers as columns B and C of kelly-sheet.csv. The fee
is folded into the price the way the chapter does it: you pay price + fee for
the side you buy. Full Kelly = (p - c) / (1 - c).

Educational code, not financial advice. Your probability is the input that
decides everything here, and only your journal can tell you if it is any good.
"""
import argparse
from decimal import ROUND_HALF_UP, Decimal

MAX_BET = 0.05  # Rule 1: never more than 5% of bankroll on one market


def taker_fee(rate, price):
    """Polymarket taker fee per share: rate x p x (1 - p)."""
    return rate * price * (1 - price)


def full_kelly(prob, price, side="yes", fee_rate=0.0):
    """Return (full Kelly fraction, your win probability, cost per share).

    prob and price are always the Yes probability and the Yes price, as in
    the spreadsheet. For a NO trade you win with 1 - prob and pay 1 - price.
    """
    if side == "yes":
        p, c = prob, price
    else:
        p, c = 1 - prob, 1 - price
    c = c + taker_fee(fee_rate, c)
    if c >= 1:
        return 0.0, p, c
    return (p - c) / (1 - c), p, c


def pct(x, places="0.1"):
    """Percent, rounded half up the way the chapter's table is.

    round(..., 9) first, because float math leaves 6.25 as 6.2499999...
    """
    return Decimal(str(round(x * 100, 9))).quantize(Decimal(places),
                                                     ROUND_HALF_UP)


def money(x):
    return Decimal(str(x)).quantize(Decimal("0.01"), ROUND_HALF_UP)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--prob", type=float, required=True,
                    help="your probability the event happens, 0 to 1")
    ap.add_argument("--price", type=float, required=True,
                    help="the market's Yes price, 0 to 1")
    ap.add_argument("--side", choices=["yes", "no"], default="yes")
    ap.add_argument("--fee-rate", type=float, default=0.0,
                    help="taker fee rate from the market's fee schedule "
                         "(0 for a resting limit order)")
    ap.add_argument("--bankroll", type=float,
                    help="your current bankroll in dollars")
    ap.add_argument("--fraction", type=float, default=0.25,
                    help="Kelly fraction you bet (default 0.25, quarter "
                         "Kelly for your first 50 trades)")
    a = ap.parse_args(argv)
    if not (0 < a.prob < 1 and 0 < a.price < 1):
        ap.error("--prob and --price must be between 0 and 1")

    full, p, c = full_kelly(a.prob, a.price, a.side, a.fee_rate)
    fee = c - (a.price if a.side == "yes" else 1 - a.price)
    print(f"Buying {a.side.upper()} at ${c - fee:.2f} + ${fee:.4f} fee "
          f"= ${c:.4f} a share")
    print(f"You win {pct(p)}% of the time, edge after fee "
          f"{pct(p - c, '0.01')} points")
    if full <= 0:
        print("Kelly says no bet: you have no edge after the fee.")
        return 0

    print()
    rows = [("Full Kelly", 1.0), ("Half Kelly", 0.5), ("Quarter Kelly", 0.25)]
    for name, f in rows:
        line = f"{name:<14}{pct(full * f):>6}%"
        if a.bankroll:
            line += f"   ${money(full * f * a.bankroll)}"
        print(line)

    stake = min(full * a.fraction, MAX_BET)
    print()
    print(f"At {a.fraction:g} Kelly with the 5% cap: bet {pct(stake)}% "
          "of your bankroll", end="")
    if a.bankroll:
        print(f", ${money(stake * a.bankroll)} of ${money(a.bankroll)}")
    else:
        print(" (add --bankroll for dollars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
