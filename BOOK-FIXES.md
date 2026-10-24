# Book fixes

Two places where the printed code doesn't do what the chapter says. Both ship exactly as printed, so your file and ours still match; this page is the warning that goes with them.

## Chapter 6: `categorize_market` matches parts of words

The chapter calls its output "the market's category", and `record.py` files your resolutions under it. It checks whether a keyword appears anywhere in the question, so "eth" inside "Netherlands" or "Ethan" means crypto, and "win" puts election questions in sports:

```text
$ cd chapters/06-ai-edge
$ python3 -c 'from polybot import categorize_market as c
for q in ["Will the Netherlands win the World Cup?", "Will Ethan Hawke host SNL?", "Will Trump win Pennsylvania?"]:
    print(c(q), "<-", q)'
crypto <- Will the Netherlands win the World Cup?
crypto <- Will Ethan Hawke host SNL?
sports <- Will Trump win Pennsylvania?
```

What this repo does: ships it verbatim, because the bot and `record.py` use the same function, so a mislabelled market is at least mislabelled the same way on both sides. Check the category before you record a resolution (the command is in `chapters/06-ai-edge/README.md`). If you fix it, match whole words, and fix it before you start recording.

## Chapter 8: the liquidity check is never called

The chapter says `max_position_for_price` "prevents your bot from ever placing an order that would move the market more than 2 cents against you". Nothing in the bot calls it, and it returns shares while `calculate_position_size` returns dollars:

```text
$ cd chapters/08-kelly
$ grep -n "max_position_for_price(" polybot.py
77:def max_position_for_price(book, max_slippage=0.02):
$ python3 -c 'from polybot import max_position_for_price, calculate_position_size
book = {"asks": [{"price": "0.55", "size": "500"}, {"price": "0.54", "size": "1200"}, {"price": "0.53", "size": "3000"}]}
print(max_position_for_price(book)); print(calculate_position_size({"side": "YES", "edge": 0.10, "market_price": 0.53}, 100.0))'
4700.0
5.0
```

The only match is the definition. The test `test_scan_never_calls_the_liquidity_check` runs one full scan and confirms the call count is zero.

What this repo does: ships it as printed and uncalled, so the Chapter 8 bot sizes exactly as the chapter's function does. If you wire it in for live trading, compare like with like: shares × ask price is the dollar amount the book can absorb.
