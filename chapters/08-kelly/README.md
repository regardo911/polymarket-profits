# Chapter 8: size every trade

Three ways to the same Kelly number: a command, a spreadsheet, and the bot.

## The calculator

```bash
python3 kelly.py --prob 0.55 --price 0.50 --fee-rate 0.07 --bankroll 1000
```

```text
Buying YES at $0.50 + $0.0175 fee = $0.5175 a share
You win 55.0% of the time, edge after fee 3.25 points

Full Kelly       6.7%   $67.36
Half Kelly       3.4%   $33.68
Quarter Kelly    1.7%   $16.84

At 0.25 Kelly with the 5% cap: bet 1.7% of your bankroll, $16.84 of $1000.00
```

That's the chapter's fee example: a 5-point edge at 50 cents on a crypto market shrinks to 3.25 points, and full Kelly drops from 10.0% to 6.7%. `--prob` is always your probability that the event happens and `--price` is always the Yes price, even for `--side no`, the same two numbers as columns B and C of the sheet. Leave `--fee-rate` at 0 for a resting limit order.

Check it against the chapter's table:

| `--prob` | `--price` | Full | Half | Quarter |
|---|---|---|---|---|
| 0.55 | 0.50 | 10.0% | 5.0% | 2.5% |
| 0.50 | 0.40 | 16.7% | 8.3% | 4.2% |
| 0.50 | 0.35 | 23.1% | 11.5% | 5.8% |
| 0.85 | 0.80 | 25.0% | 12.5% | 6.3% |
| 0.35 | 0.25 | 13.3% | 6.7% | 3.3% |

## The sheet

Import `kelly-sheet.csv` into Google Sheets (File > Import, with "Convert text to numbers, dates, and formulas" ticked) or open it in Excel. The cells in E to I are formulas that start with `=`; if they show as text, that option was off. Fill A to D and J for each trade; E to I calculate themselves, with the formulas the chapter prints. For a taker order, type the price into C with the fee built in: price + fee for YES, Yes price − fee for NO.

Column I is position size at **half** Kelly, as printed, but the chapter tells you to use quarter Kelly for your first 50 trades. Until then, bet half of what column I says.

## The bot

`polybot.py` here is the Chapter 6 bot with Kelly sizing (`KELLY_FRACTION = 0.25`, `MAX_BET = 0.05`). In your own folder, rename the old `traded_markets.json` before you restart, or the bot skips every market it already traded and logs only the few that are new:

```bash
mv traded_markets.json traded_markets.v6.json    # your folder only; this one starts clean
python3 polybot.py
```

Check `trades.csv`: the new rows should show `size_usd` set by Kelly. On the $100 paper balance most hit the $5.00 cap; only the smallest edges size below it.
