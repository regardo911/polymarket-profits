# Chapter 10: arbitrage scanner and portfolio tracker

```bash
cd chapters/10-arbitrage
python3 arb.py
```

```text
Polymarket 43 | Kalshi 90 | candidates 0
```

Zero is the normal answer, from a real run: it means the two platforms mostly agree. When it does find one, it prints the profit per pair after both fees and the route, and you still check both platforms' resolution rules by hand before you trade it. `arb.py` only reads polymarket.com, which is close-only from the US. There, compare Kalshi against Polymarket US yourself.

To test a pair you found yourself, build the two dicts and call `find_arbitrage`. Here's the chapter's made-up recession pair. The chapter prints Polymarket's Yes ask and Kalshi's No ask; the other two asks come from the 28 and 35 cent prices it quotes:

```bash
python3 -c '
from arb import find_arbitrage
q = "Will the US enter a recession this year?"
poly = [{"question": q, "yes_ask": 0.28, "no_ask": 0.72, "fee_rate": 0.04}]
kalshi = [{"question": q, "yes_ask": 0.35, "no_ask": 0.65, "fee_rate": 0.07}]
print(find_arbitrage(poly, kalshi))'
```

It returns one candidate, `Yes Poly / No Kalshi` with `profit` 0.046: the 4.6 cents per pair the chapter works out. Swap in your own questions, asks and fee rates. The two `question` strings must share more than 60% of their words to match.

## The tracker

Import `portfolio-tracker.csv` into your spreadsheet app. Fill A to F and J to M for each open position; G, H and I (cost basis, current value, unrealized P&L) calculate themselves. Type your cash into the Cash Reserve row.

The cluster rows divide each cluster's cost basis by Total Portfolio Value (positions at current value plus cash), because the chapter caps each cluster at 25% of your total portfolio. The cluster names in column J must match the names in the cluster rows exactly. Add a row for any cluster you use that isn't listed.

**Done when** every open position is in the tracker and no cluster row is above 25%.
