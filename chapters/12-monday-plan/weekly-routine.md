# Weekly routine and 90-day checkpoint

From Chapter 12. Put the routine on your calendar as recurring events today; the times are the chapter's.

## The week

**Monday morning, 1 hour**
- [ ] Kelly sheet: is the bankroll number current? (`chapters/08-kelly/kelly-sheet.csv`)
- [ ] Portfolio tracker: update prices, check cluster exposure (`chapters/10-arbitrage/portfolio-tracker.csv`)
- [ ] New markets on the platforms open to you, onto a watchlist
- [ ] `python3 alerts.py`: any new trades from your whales?
- [ ] One scan of the bot; review what it flagged

**Monday afternoon, 30 minutes**
- [ ] Events in the next 7 days, onto the calendar
- [ ] For anything the bot flagged: base rate, disaggregation, contra-evidence. Trade only if the edge holds.

**Tuesday to Friday, 20 minutes a day**
- [ ] Tracker, bot scan, whale alerts
- [ ] Breaking news? Check it against your open positions

**Weekend, 1 hour**
- [ ] Trades this week: ___  Win rate: ___  P&L: $___
- [ ] Trades where the thesis was wrong: ___
- [ ] Calibration: overconfident or underconfident in any category?
- [ ] Next week's scheduled events, researched

## Six-month event calendar

Fed meetings, jobs/CPI/GDP releases, the sports seasons you trade, earnings. Set a reminder two days before each.

| Date | Event | Markets to check |
|---|---|---|
| | | |
| | | |
| | | |

## Where people stall, and the move back

| If | Then |
|---|---|
| The bot stopped running | Restart it in paper mode the same day, `tail -50 bot_output.log`, fix the first error you see |
| You skipped the journal | Rebuild the missed trades from your platform history (or the Data API) before the next trade |
| A losing week | Did the losses have positive EV at entry? Yes: change nothing. No: back to Chapter 3 |
| Drawdown past your stop rule | One week off, as your risk budget says, and review every trade |

## The 90-day checkpoint

Date (90 days from today): ____________. Paste these six into that calendar event.

1. How many trades did I make? (Under 50: too few to calibrate. Over 500: check fees and slippage.)
2. Win rate by category: politics ___ sports ___ crypto ___ economics ___
3. Total P&L: $______
4. Calibration: when I said 70%, how often was I right? ___%
5. Is the bot still running? If not, why?
6. Do I still enjoy this?

Scale up, fix the weak spots, or stop. The one wrong answer is carrying on without measuring.
