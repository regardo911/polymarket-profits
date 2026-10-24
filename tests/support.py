"""Shared test plumbing: load a chapter script by path, fake HTTP, block the network.

Every market, book, wallet and trade in these tests is made up. Nothing here
talks to Polymarket, Kalshi or NewsAPI: block_network() makes any real socket
connection raise, so a test that forgot a fake fails instead of going online.
"""
import contextlib
import importlib.util
import io
import os
import socket
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CH = ROOT / "chapters"

_real_connect = socket.socket.connect


def _refuse(*args, **kwargs):
    raise OSError("network blocked in tests")


def block_network():
    socket.socket.connect = _refuse


def unblock_network():
    socket.socket.connect = _real_connect


def load(relpath, name):
    """Import chapters/<relpath> as a fresh module called `name`.

    Several chapters ship a file called polybot.py, so each gets its own name.
    The file's folder goes on sys.path so record.py and alerts.py can import
    their neighbour the way they do when you run them.
    """
    path = CH / relpath
    folder = str(path.parent)
    if folder not in sys.path:
        sys.path.insert(0, folder)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@contextlib.contextmanager
def in_tempdir():
    """Run inside an empty folder: the bots write trades.csv and friends to the cwd."""
    old = os.getcwd()
    with tempfile.TemporaryDirectory() as d:
        os.chdir(d)
        try:
            yield Path(d)
        finally:
            os.chdir(old)


def captured(fn, *args, **kwargs):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        result = fn(*args, **kwargs)
    return result, out.getvalue()


# ---- a made-up Polymarket: four Gamma markets and their Yes order books ----

MADE_UP_MARKETS = [
    {   # busy, mispriced against a 50% baseline: the bot should paper-trade it
        "question": "Will the made-up council approve the stadium deal?",
        "conditionId": "0xmadeup1",
        "outcomes": '["Yes", "No"]',
        "clobTokenIds": '["yes-1", "no-1"]',
        "volume24hr": 50000, "volume1wk": 140000,
        "feeSchedule": {"rate": 0.05},
    },
    {   # extreme price: Test 5 drops it
        "question": "Will the made-up sun explode tomorrow?",
        "conditionId": "0xmadeup2",
        "outcomes": '["Yes", "No"]',
        "clobTokenIds": '["yes-2", "no-2"]',
        "volume24hr": 90000, "volume1wk": 300000,
        "feeSchedule": None,
    },
    {   # not a Yes/No question: scan_all_markets skips it
        "question": "Made-up Lakers vs. Celtics",
        "conditionId": "0xmadeup3",
        "outcomes": '["Lakers", "Celtics"]',
        "clobTokenIds": '["lak-3", "cel-3"]',
        "volume24hr": 80000, "volume1wk": 200000,
    },
    {   # too quiet: under MIN_VOLUME
        "question": "Will the made-up quiet market resolve Yes?",
        "conditionId": "0xmadeup4",
        "outcomes": '["Yes", "No"]',
        "clobTokenIds": '["yes-4", "no-4"]',
        "volume24hr": 500, "volume1wk": 3000,
    },
]

# bids/asks deliberately out of price order, the way the live API returns them
MADE_UP_BOOKS = {
    "yes-1": {"bids": [{"price": "0.01", "size": "900"}, {"price": "0.30", "size": "400"}],
              "asks": [{"price": "0.99", "size": "900"}, {"price": "0.32", "size": "300"}]},
    "yes-2": {"bids": [{"price": "0.01", "size": "100"}],
              "asks": [{"price": "0.03", "size": "100"}]},
    "yes-4": {"bids": [{"price": "0.40", "size": "10"}],
              "asks": [{"price": "0.44", "size": "10"}]},
}


def fake_polymarket_get(url, params=None, timeout=None, **kwargs):
    if url.endswith("/markets"):
        return FakeResponse(MADE_UP_MARKETS)
    if url.endswith("/book"):
        book = MADE_UP_BOOKS.get(params["token_id"])
        return FakeResponse(book or {}, 200 if book else 404)
    return FakeResponse({}, 404)
