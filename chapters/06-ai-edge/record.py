"""Record one resolved market for the calibrated baselines, Chapter 6.

Writes calibration.json next to this file. The category is the one
categorize_market() gives the market's question.
"""
import sys
from polybot import update_calibration

# usage: python3 record.py crypto no
update_calibration(sys.argv[1], sys.argv[2] == "yes")
print(f"recorded {sys.argv[1]}: {sys.argv[2]}")
