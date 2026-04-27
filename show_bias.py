"""Print the current NASDAQ BIAS as it would appear in Telegram."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from nasdaq_scanner import fetch_indicators, calculate_bias
from datetime import datetime

indicators = fetch_indicators()
bias, score, details = calculate_bias(indicators)
now = datetime.now().strftime("%d/%m/%Y %H:%M")

sep = "=" * 45
print(sep)
print(f"  NASDAQ DAILY BIAS  |  {now}")
print(sep)
print()

print("[ LIVE INDICATORS ]")
print(f"  DXY  : {indicators['DXY']['value']:>8}  ({indicators['DXY']['change_pct']:+.2f}%)")
print(f"  VIX  : {indicators['VIX']['value']:>8}  ({indicators['VIX']['change_pct']:+.2f}%)")
print(f"  NDX  : {indicators['NDX']['value']:>8}  ({indicators['NDX']['change_pct']:+.2f}%)")
print(f"  SPX  : {indicators['SPX']['value']:>8}  ({indicators['SPX']['change_pct']:+.2f}%)")
print(f"  10Y  : {indicators['10Y']['value']:>8}% ({indicators['10Y']['change_pct']:+.2f}%)")
print()

print(f"[ BIAS: {bias} ]")
print(f"  Score : {score}/3")
for d in details:
    print(f"  - {d}")
print()

if "BULLISH" in bias.upper():
    symbol = "^^^"
elif "BEARISH" in bias.upper():
    symbol = "vvv"
else:
    symbol = "---"

print(f"    {symbol} {bias} {symbol}")
print()
print(sep)
print("  This is what Telegram receives")
print("  once BOT_TOKEN + CHAT_ID are set.")
print(sep)