# One real order, through Polymarket's own SDK

The Chapter 5 bot stops at paper. This folder is the step after it: `live_order.py` places one limit order you chose, with the official SDK for where you live. You need your own account and your own API credentials. Paper-trade first; Chapter 9 says a month.

| Where you live | Platform | SDK | Python | In `.env` next to the script |
|---|---|---|---|---|
| Outside the close-only countries | polymarket.com | `polymarket-client` | 3.11+ | `POLYMARKET_PRIVATE_KEY`, `POLYMARKET_WALLET_ADDRESS` |
| United States | Polymarket US | `polymarket-us` | 3.10+ | `POLYMARKET_KEY_ID`, `POLYMARKET_SECRET_KEY` |

Account and key setup is in the official docs, not here: [docs.polymarket.com/trading/quickstart](https://docs.polymarket.com/trading/quickstart) (the wallet address is your account's Deposit Wallet, shown in your profile menu, not your MetaMask address) and [docs.polymarket.us/getting-started/quickstart](https://docs.polymarket.us/getting-started/quickstart).

## Dry run first

```bash
pip install polymarket-us            # or: pip install polymarket-client
python3 live_order.py --venue us --slug <market-slug> --side yes --price 0.42 --size 10
```

```text
DRY RUN, nothing sent. This is the order live mode would place:
  us: BUY YES 10 @ $0.42 limit, market <market-slug>
To send it, uncomment set_live_mode(True, confirm="I_HAVE_REVIEWED_THIS") at the bottom of live_order.py
```

The slug is the last part of the market's URL. With `--venue international` the script runs the Chapter 2 geoblock check first and refuses if polymarket.com is close-only where you are. On Polymarket US it buys Yes only. The US docs treat a No position as a short on Yes, and this example hasn't been checked against that.

## Sending it

Open `live_order.py` and uncomment the one line at the bottom:

```python
set_live_mode(True, confirm="I_HAVE_REVIEWED_THIS")
```

Run the same command. It prints `LIVE ORDER. Real money, your risk.`, then the order id the SDK returns. A flag can't do this and neither can an environment variable; it has to be an edit you made and can see. Put the line back in a comment when you're done.

You get back one resting limit order, the size and price you typed, placed through Polymarket's code rather than signing code copied from a book. Every SDK call was read off the official docs and checked against the real signatures in `polymarket-client` 0.14.0 and `polymarket-us` 2.4.1. Both install and load. It has never been run against a real account here.

Don't commit `.env`. If a private key ever leaks, move your funds to a new wallet first and ask questions after.
