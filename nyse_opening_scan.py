"""
NYSE OPENING SCAN
Scans forex, indices, commodities for pre-market setups
ICT/SMC lens: structure, FVG, liquidity
Usage: python nyse_opening_scan.py
"""

import sys
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ============================================================
# ASSET UNIVERSE
# ============================================================
ASSETS = {
    # Forex
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CAD": "USDCAD=X",
    "NZD/USD": "NZDUSD=X",
    # Indices
    "US30 (DJI)": "^DJI",
    "ES (S&P)": "ES=F",
    "NQ (NASDAQ)": "NQ=F",
    "GER40 (DAX)": "^GDAXI",
    "UK100 (FTSE)": "^FTSE",
    # Commodities
    "GOLD (XAU)": "GC=F",
    "SILVER": "SI=F",
    "OIL (WTI)": "CL=F",
    "OIL (BRENT)": "BZ=F",
    "NAT GAS": "NG=F",
    # Crypto
    "BTC/USD": "BTC-USD",
    "ETH/USD": "ETH-USD",
}


def fetch_asset(symbol, name):
    """Pull 5d + 1d intraday for one asset"""
    try:
        t = yf.Ticker(symbol)

        # Daily data (5 days)
        d = t.history(period="5d")
        # 1h intraday (1 day)
        h = t.history(period="1d", interval="1h")

        if d.empty:
            return None

        close_now = round(d["Close"].iloc[-1], 2)
        prev_close = round(d["Close"].iloc[-2], 2) if len(d) > 1 else close_now
        change_pct = round(((close_now - prev_close) / prev_close) * 100, 2)

        high_5d = round(d["High"].max(), 2)
        low_5d = round(d["Low"].min(), 2)
        range_5d = round(high_5d - low_5d, 2)

        # Volume spike check
        vol_now = int(d["Volume"].iloc[-1]) if "Volume" in d else 0
        vol_avg = int(d["Volume"].mean()) if "Volume" in d else 0
        vol_spike = round(vol_now / vol_avg, 2) if vol_avg > 0 else 1.0

        # Position in 5D range (0=low, 100=high)
        range_pos = round(((close_now - low_5d) / range_5d) * 100, 2) if range_5d > 0 else 50

        # Intraday range (from 1h data)
        intra_range = 0
        intra_change = 0
        if not h.empty and len(h) > 1:
            h_high = round(h["High"].max(), 2)
            h_low = round(h["Low"].min(), 2)
            h_open = round(h["Open"].iloc[0], 2)
            intra_range = round(h_high - h_low, 2)
            intra_change = round(((close_now - h_open) / h_open) * 100, 2)

        return {
            "name": name,
            "symbol": symbol,
            "price": close_now,
            "change_pct": change_pct,
            "high_5d": high_5d,
            "low_5d": low_5d,
            "range_5d": range_5d,
            "range_pos": range_pos,
            "vol_spike": vol_spike,
            "intra_range": intra_range,
            "intra_change": intra_change,
        }

    except Exception as e:
        return {"name": name, "error": str(e)}


# ============================================================
# SCORING - ICT/SMC Setup Potential
# ============================================================
def score_asset(data):
    """Score asset based on ICT/SMC setup potential for opening"""
    if "error" in data:
        return 0, "Error"

    score = 0
    tags = []

    # 1. Range position - discount/premium
    if data["range_pos"] < 30:
        score += 15
        tags.append("DISCOUNT (<30%)")
    elif data["range_pos"] > 70:
        score += 15
        tags.append("PREMIUM (>70%)")
    else:
        score += 5
        tags.append("EQ (~50%)")

    # 2. Volume spike = institutional activity
    if data["vol_spike"] > 1.5:
        score += 20
        tags.append("VOL SPIKE")
    elif data["vol_spike"] > 1.2:
        score += 10
        tags.append("Vol Above Avg")

    # 3. Clear directional momentum
    if abs(data["change_pct"]) > 0.5:
        score += 15
        direction = "UP" if data["change_pct"] > 0 else "DOWN"
        tags.append(f"CLEAR {direction}")
    elif abs(data["change_pct"]) > 0.25:
        score += 8
        tags.append("Weak momentum")

    # 4. Intraday range expansion (potential displacement)
    if data["intra_range"] > data["range_5d"] * 0.3:
        score += 20
        tags.append("RANGE EXPAND")
    elif data["intra_range"] > 0:
        score += 10
        tags.append("Normal intra")

    # 5. Price near session high/low (liquidity grab potential)
    if data["range_pos"] > 85:
        score += 10
        tags.append("Near RESISTANCE")
    elif data["range_pos"] < 15:
        score += 10
        tags.append("Near SUPPORT")

    return score, " | ".join(tags)


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 70)
    print(f"  NYSE OPENING SCAN  |  {datetime.now().strftime('%Y-%m-%d %H:%M')} IST")
    print(f"  Market opens: ~{datetime.now().strftime('%H:%M')} (pre-market active)")
    print("=" * 70)
    print()

    # Fetch all
    results = []
    for name, symbol in ASSETS.items():
        print(f"  Loading {name}...", end=" ")
        data = fetch_asset(symbol, name)
        if data:
            score, tags = score_asset(data)
            data["score"] = score
            data["tags"] = tags
            results.append(data)
            print(f"ok (score: {score})")
        else:
            print("no data")

    # Sort by score
    results.sort(key=lambda x: x.get("score", 0), reverse=True)

    # Display Top 10
    print()
    print("=" * 70)
    print("  TOP SETUPS FOR NYSE OPENING")
    print("=" * 70)
    print()

    for i, r in enumerate(results[:12]):
        if i < 10:
            direction = "+" if r.get("change_pct", 0) > 0 else ""
            stars = "⭐" * min(3, r.get("score", 0) // 15)
            print(f"  #{i+1:2d}  {stars}  {r['name']:<16s}  "
                  f"{r['price']:<12,.2f}  "
                  f"{direction}{r['change_pct']:+.2f}%  "
                  f"[{r.get('score', 0)} pts]")
            print(f"        {r.get('tags', '')}")
            print(f"        Range: {r['low_5d']} -- [{r['range_pos']:.0f}%] -- {r['high_5d']}")
            print()

    # Pick the best one
    if results:
        best = results[0]
        print("=" * 70)
        print(f"  RECOMMENDED: {best['name']} ({best['score']} pts)")
        print(f"  Price: {best['price']}")
        print(f"  Setup: {best['tags']}")
        print(f"  Bias: {'LONG (discount)' if best['range_pos'] < 40 else 'SHORT (premium)' if best['range_pos'] > 60 else 'WAIT (equilibrium)'}")
        print("=" * 70)