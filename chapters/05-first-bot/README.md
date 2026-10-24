# Chapter 5: the paper-trading bot

`polybot.py` reads the 100 busiest Polymarket markets, keeps the plain Yes/No ones, reads each one's order book, and paper-trades any market whose price sits more than 7 points from its estimate after the taker fee. Its estimate is a flat 50%. That's the dumb version on purpose; Chapter 6 gives it a brain.

```bash
cd chapters/05-first-bot
python3 polybot.py
```

You get the banner, then one block per scan:

```text
--- Scan #1 (21:11:06) ---
Scanned 59 markets
[PAPER] NO $2.00 Will there be no change in F.. edge 43.5%
[PAPER] YES $2.00 Will the Fed increase intere.. edge 43.5%
...
Signals found: 37
Already traded: 37 markets
```

That's a real run; yours will show different markets. Scan #2 usually prints no `[PAPER]` lines, because every flagged market is already traded.

**It works when** three scans in a row print `Scanned` with a number above zero, and `trades.csv` in this folder has one row per `[PAPER]` line, `paper` = `True`, `balance` = `100.00`.

## Running it as your own bot

This file is the BUILD STEP 2 code in order with the five fixes from "Testing Your Bot" already in, so you can diff it against the one you typed:

| Test | Where it lives |
|---|---|
| 1, empty market | `if market.get("yes_price") is None` at the top of `analyze_market` |
| 2, rate limits | `rate_limited_get`, used by `get_markets` and `get_market_prices` |
| 3, pagination | `get_all_markets` (defined; `run_bot` still scans the 100 busiest) |
| 4, restarts | `traded_markets.json`: loaded at the start of `run_bot`, saved after each trade |
| 5, extreme prices | `if yes_price < 0.05 or yes_price > 0.95` in `analyze_market` |

The things you edit are the constants under their book names: `EDGE_THRESHOLD`, `MIN_VOLUME`, `MAX_SPREAD`, `MAX_POSITION_SIZE`, `SCAN_INTERVAL`. Leave `PAPER_TRADE = True`. Set it to `False` and the bot stops with `NotImplementedError: paper mode only`, which is what the book prints. Live orders are [`live/`](live)'s job.

On a server that doesn't sleep, from this folder (the book's line has `.venv/bin/python`; in this repo the venv sits two folders up):

```bash
nohup ../../.venv/bin/python -u polybot.py > bot_output.log 2>&1 &
tail -50 bot_output.log
```

Keep the `-u`. Without it Python buffers the output and the log stays empty for many scans.

To start over, delete `traded_markets.json`. While it exists, the bot skips every market listed in it, across restarts.

## When it misbehaves

- `Signals found` is almost the whole scan: that's the 50% baseline, not a bug in the plumbing. Chapter 6 replaces the baseline.
- `Scanned 0 markets` or zero signals for a long time: print how many markets survive each filter. Volume comes from Gamma's `volume24hr`, and the spread from `max(bids)` and `min(asks)`.
- Try Test 1's fake market yourself and the loop's `try` catches it, printing `Error in scan cycle: ...`.
- `Rate limited. Waiting 1s...` comes from Polymarket US or Kalshi limits; Polymarket's own API slows down instead of refusing.

**Exercise.** After 30 minutes, open `trades.csv` and pick three rows. For each, write one line: is 50% a sensible estimate for that question? You're done when you can name the row where it's most obviously wrong and why. That row is the reason Chapter 6 exists.
