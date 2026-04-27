"""SILVER Deep Analysis — Structure, FVG, OB, Entry"""
import sys
import yfinance as yf
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

t = yf.Ticker("SI=F")
d = t.history(period="1mo")
h = t.history(period="5d", interval="1h")

print("=" * 55)
print(f"  SILVER (XAG/USD) Deep Analysis")
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=" * 55)

# ── DAILY STRUCTURE ──
print("\n[ DAILY STRUCTURE — Last 10 Days ]")
print(f"{'Date':>12s}  {'O':>8s}  {'H':>8s}  {'L':>8s}  {'C':>8s}  {'V':>10s}")
r = d.tail(10)

swing_highs = []
swing_lows = []

for i, (idx, row) in enumerate(r.iterrows()):
    print(f"  {idx.strftime('%d/%m')}  {row['Open']:8.2f}  {row['High']:8.2f}  {row['Low']:8.2f}  {row['Close']:8.2f}  {int(row.get('Volume',0)):>10,d}")

# Structure: HH/HL/LL/LH
last_close = r["Close"].iloc[-1]
last_high = r["High"].iloc[-1]
last_low = r["Low"].iloc[-1]
prev_high = r["High"].iloc[-2]
prev_low = r["Low"].iloc[-2]
prev2_high = r["High"].iloc[-3] if len(r) >= 3 else prev_high
prev2_low = r["Low"].iloc[-3] if len(r) >= 3 else prev_low

print(f"\n  Last C: {last_close:.2f}")

if last_high > prev_high:
    print(f"  [HH] Higher High: {last_high:.2f} > {prev_high:.2f}")
else:
    print(f"  [LH] Lower High: {last_high:.2f} < {prev_high:.2f}")

if last_low > prev_low:
    print(f"  [HL] Higher Low: {last_low:.2f} > {prev_low:.2f}")
else:
    print(f"  [LL] Lower Low: {last_low:.2f} < {prev_low:.2f}")

# Bias from structure
if last_high > prev_high and last_low > prev_low:
    print(f"  STRUCTURE: BULLISH (HH+HL)")
elif last_high < prev_high and last_low < prev_low:
    print(f"  STRUCTURE: BEARISH (LH+LL)")
else:
    print(f"  STRUCTURE: INDECISION (mixed)")

# Month levels
m_high = d["High"].max()
m_low = d["Low"].min()
m_range = m_high - m_low
pos = (last_close - m_low) / m_range * 100
print(f"\n  Month Range: {m_low:.2f} — [{pos:.0f}%] — {m_high:.2f}")
print(f"  Position: {'DISCOUNT' if pos < 40 else 'PREMIUM' if pos > 60 else 'EQUILIBRIUM'}")

# ── HOURLY FVG ──
print("\n[ HOURLY FVG SCAN ]")
r_h = h.tail(20)
candles = []
for idx, row in r_h.iterrows():
    candles.append({
        "time": idx.strftime("%d %H:%M"),
        "O": round(row["Open"], 2),
        "H": round(row["High"], 2),
        "L": round(row["Low"], 2),
        "C": round(row["Close"], 2),
        "bull": row["Close"] >= row["Open"]
    })

fvg_found = False
for i in range(len(candles) - 2):
    c1, c2, c3 = candles[i], candles[i+1], candles[i+2]
    # Bullish FVG
    if c1["bull"] and c1["H"] < c3["L"]:
        gap = round(c3["L"] - c1["H"], 2)
        print(f"  BULLISH FVG: {c1['time']} -> {c3['time']}")
        print(f"    Gap: {c1['H']:.2f} — {c3['L']:.2f} ({gap})")
        print(f"    ENTRY ZONE: {c1['H']:.2f} to {c3['L']:.2f}")
        fvg_found = True
    # Bearish FVG
    if not c1["bull"] and c1["L"] > c3["H"]:
        gap = round(c1["L"] - c3["H"], 2)
        print(f"  BEARISH FVG: {c1['time']} -> {c3['time']}")
        print(f"    Gap: {c3['H']:.2f} — {c1['L']:.2f} ({gap})")
        print(f"    ENTRY ZONE: {c3['H']:.2f} to {c1['L']:.2f}")
        fvg_found = True

if not fvg_found:
    print("  No FVG detected in last 20 candles")

# ── LIQUIDITY ──
print("\n[ LIQUIDITY ]")
print(f"  BSL (Buy-Side): {m_high:.2f} (month high)")
print(f"  SSL (Sell-Side): {m_low:.2f} (month low)")
print(f"  Near BSL: {'YES' if pos > 85 else 'no'}")
print(f"  Near SSL: {'YES' if pos < 15 else 'no'}")

# ── SUMMARY ──
print("\n" + "=" * 55)
print(f"  SUMMARY")
print(f"  Price: {last_close:.2f}")
print(f"  Position: {pos:.0f}% of monthly range")
print(f"  Structure: {'HH+HL (BULLISH)' if last_high > prev_high and last_low > prev_low else 'LH+LL (BEARISH)' if last_high < prev_high and last_low < prev_low else 'MIXED'}")

if pos < 40:
    print(f"  BIAS for OPEN: LONG from discount")
    print(f"  Target: BSL at {m_high:.2f}")
    print(f"  Stop: below {m_low:.2f}")
elif pos > 60:
    print(f"  BIAS for OPEN: SHORT from premium")
    print(f"  Target: SSL at {m_low:.2f}")
    print(f"  Stop: above {m_high:.2f}")
else:
    print(f"  BIAS for OPEN: WAIT — equilibrium, no edge")
print("=" * 55)