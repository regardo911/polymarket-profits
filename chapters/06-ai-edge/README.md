# Chapter 6: a smarter Analyst

Same bot, same loop. `analyze_market_v2` replaces the flat 50% with three signals: a volume spike (`get_sentiment_score`), headline shifts (`get_recent_headlines` + `analyze_headline`) and a calibrated baseline per category (`get_baseline`). Everything else in `polybot.py` is the Chapter 5 file.

Moving over from your Chapter 5 folder: replace `polybot.py`, add `record.py`, keep your `trades.csv` and `traded_markets.json`.

```bash
cd chapters/06-ai-edge
python3 polybot.py
```

On day one it makes the same calls as Chapter 5 on most markets. That's expected and it isn't broken: with no `calibration.json`, `get_baseline` returns 0.50 for every category, and with no key and the stub LLM the headline shift is 0.0. A category switches to its own baseline once it has 10 recorded resolutions.

## Feeding it resolutions

You record outcomes yourself. Each time a market you paper-traded resolves, run:

```bash
python3 record.py crypto no
```

It prints `recorded crypto: no` and adds one line of evidence to `calibration.json`. Use the category `categorize_market` gives the question, so your records land where the bot looks:

```bash
python3 -c 'from polybot import categorize_market; print(categorize_market("Will Bitcoin hit $150K?"))'
```

Check that answer before you record; the keyword match makes mistakes (see [BOOK-FIXES.md](../../BOOK-FIXES.md)). Both arguments are required: `python3 record.py` on its own stops with `IndexError`.

`calibration.example.json` is the chapter's made-up file, kept under a name the bot never opens. A real `calibration.json` comes only from your own `record.py` runs. Copy the example over it and every category gets a fake baseline the moment the bot starts.

## Is calibration helping yet?

After a month, add two columns to `trades.csv` in your spreadsheet app, `category` and `outcome` (`win` or `loss`), fill them for the trades that resolved, save as CSV, and run:

```bash
python3 -c 'from polybot import analyze_calibration; analyze_calibration()'
```

It prints four lines: `Trades analyzed`, `Naive accuracy`, `Calibrated accuracy` and `Improvement`, all computed from your own resolved rows. Rows without an `outcome` are skipped. Before your first `record.py` it stops with `FileNotFoundError: calibration.json`. Keep the calibrated baseline only in the categories where this says it helps, and give each category dozens of resolutions before you believe it.

## Optional upgrades

- **Headlines.** Free key at newsapi.org, then `cp .env.example .env` and put it after `NEWS_API_KEY=`. Free articles arrive 24 hours late, so treat them as context, not speed. `.env` is already in `.gitignore`.
- **An LLM.** `call_llm_api` is the book's stub and returns `"0.00"`. Replace its body with one call to your provider that returns the reply as text. Until you do, the headline shift is zero.

Good run: three scans, no `NameError`, new rows in `trades.csv`, and `record.py` writes a resolution into `calibration.json`.
