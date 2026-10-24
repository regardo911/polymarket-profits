# Contributing

Bug reports and fixes are welcome. The most useful ones: an endpoint or field that Polymarket, Kalshi or the Data API changed, and a script that breaks on a Python version from 3.11 up.

A few house rules, because readers copy these files next to the book:

- Keep the book's names. `polybot.py`, `scan_all_markets`, `EDGE_THRESHOLD = 0.07` and the rest match the printed chapters, so a reader can diff their own file against ours. A rename makes that impossible.
- The three `polybot.py` files are snapshots of the same bot at the end of Chapters 5, 6 and 8. A fix to shared code goes into all three.
- If the printed book is wrong and the code here works around it, add an entry to `BOOK-FIXES.md` with the command and output that show the problem.
- No result figures. No profit, win rate or return goes into a doc, a test or a fixture unless the code computes it from live data when you run it, or it's labelled made-up.
- Tests run offline: `python3 -m unittest discover tests`. Fake the HTTP call; the test helpers block real network connections, so a missing fake fails loudly.
