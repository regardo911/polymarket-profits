# Chapter 7: vet a wallet before you copy it

```bash
cd chapters/07-copy-the-whales
python3 whales.py
```

It pulls this month's leaderboard from Polymarket's free Data API and vets the top five: trade count, resolved positions, win rate, and profit with the single best win taken out. It takes under a minute and prints one row per wallet:

```text
#1 trades=<count> resolved=<count> win=<rate>% ex-best=$<profit without the best win>
#3 trades=<count> resolved=<count> win=100% ex-best=$<...> *
```

Every number is pulled live from the API when you run it, and they're other people's wallets, not your results. In a test run, every complete row (no `*`) had won fewer than half its resolved bets: win rate alone tells you little. The `*` means the history didn't fit in ten pages and the API sends winners first, so that row's win rate reads too high; skip it or raise `max_pages`.

To go wider, edit the last block of `whales.py` the way BUILD STEP 1 says: `leaderboard("month")` to `leaderboard("all")`, and `[:5]` to `[:20]`.

To vet one wallet you found yourself (a `user_id` from the leaderboard, or a `proxyWallet` from `https://gamma-api.polymarket.com/public-search?q=<handle>&search_profiles=true`):

```bash
python3 -c 'from whales import vet_wallet; print(vet_wallet("0xYOUR_WALLET"))'
```

Keep a wallet only if it has 100+ resolved positions, stays profitable without its best win, has been profitable for 90+ days, and trades more than one category.

## Alerts on the wallets you kept

Replace the `"0x..."` placeholder in `WHALES` (in `whales.py`) with real wallets, then run `python3 alerts.py`. The first run prints each wallet's last 20 trades, oldest first, and writes `whale_alerts.json`; later runs print only what's new. Until you replace the placeholder it prints nothing:

```text
whale 1: BUY Hornets @ 0.44 x153,874 | Hawks vs. Hornets
```

Every five minutes on a Mac or Linux box, with `crontab -e`:

```text
*/5 * * * * cd /path/to/chapters/07-copy-the-whales && /path/to/.venv/bin/python alerts.py >> alerts.log 2>&1
```

On Windows, Task Scheduler runs the same command. Delete `whale_alerts.json` to see the last 20 again.

**Done when** you've written down 3-5 wallets that pass the four checks above and `alerts.py` prints their trades. Then watch for a week before copying anything.
