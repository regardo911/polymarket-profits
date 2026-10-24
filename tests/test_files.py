"""The sheets and docs: spreadsheet columns as the book lists them, and links that resolve."""
import csv
import re
import unittest

from support import CH, ROOT


class Spreadsheets(unittest.TestCase):
    def header(self, rel):
        with open(CH / rel, newline="") as f:
            return next(csv.reader(f))

    def test_kelly_sheet_has_columns_a_to_j(self):
        self.assertEqual(self.header("08-kelly/kelly-sheet.csv"), [
            "Market Question", "Your Probability", "Market Price", "Side", "Edge",
            "Payout Ratio", "Full Kelly %", "Half Kelly %", "Position Size $", "Current Bankroll"])

    def test_tracker_has_columns_a_to_m(self):
        self.assertEqual(len(self.header("10-arbitrage/portfolio-tracker.csv")), 13)

    def test_sheets_ship_blank(self):
        # inputs are the reader's: no probabilities, prices or positions pre-filled
        for rel, inputs in (("08-kelly/kelly-sheet.csv", (0, 1, 2, 3, 9)),
                            ("10-arbitrage/portfolio-tracker.csv", range(0, 6))):
            with open(CH / rel, newline="") as f:
                rows = list(csv.reader(f))[1:16]
            for row in rows:
                self.assertTrue(all(row[i] == "" for i in inputs), (rel, row))


class Docs(unittest.TestCase):
    def test_relative_links_resolve(self):
        link = re.compile(r"\]\((?!https?://|#|mailto:)([^)\s]+)\)")
        for md in ROOT.rglob("*.md"):
            if ".venv" in md.parts:
                continue
            for target in link.findall(md.read_text()):
                path = (md.parent / target.split("#")[0]).resolve()
                self.assertTrue(path.exists(), f"{md.relative_to(ROOT)} -> {target}")

    def test_every_script_names_its_chapter(self):
        for py in CH.rglob("*.py"):
            first = py.read_text().split("\n", 1)[0]
            self.assertRegex(first, r"Chapter \d+", str(py.relative_to(ROOT)))


if __name__ == "__main__":
    unittest.main()
